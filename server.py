import sqlite3
import urllib.request
import threading
import time
from flask import Flask, request, Response, redirect

app = Flask(__name__)

DB_PATH = 'vpn_database.db'
VPN_CONFIG_URL = (
    "https://cdn.jsdelivr.net/gh/igareck/vpn-configs-for-russia@main/BLACK_VLESS_RUS.txt"
)
OBHOD_CONFIG_URL = (
    "https://cdn.jsdelivr.net/gh/igareck/vpn-configs-for-russia@main/WHITE-CIDR-RU-all.txt"
)
RENDER_URL = "https://cbn-vpn-server.onrender.com/"  # ⚠️ замени на свой URL после деплоя
SECRET_KEY = "cbn_secret_2026"                        # ⚠️ одинаковый в боте и сервере
ADMIN_ID = 1448623020
CACHE_TTL = 900  # 15 минут

# ─── КЕШ КОНФИГОВ ─────────────────────────────────────────
_cache = {
    "vpn":  {"data": None, "updated_at": 0, "updating": False},
    "obs":  {"data": None, "updated_at": 0, "updating": False},
}
_cache_lock = threading.Lock()


def _download(url: str, timeout: int = 30, retries: int = 3) -> bytes:
    """Скачивает URL с retry. Таймаут увеличен до 30с."""
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # 1с, 2с между попытками
    raise last_err


def _warm_one(key: str, url: str):
    """Скачивает один конфиг и кладёт в кеш. Для параллельного прогрева."""
    try:
        data = _download(url)
        with _cache_lock:
            _cache[key]["data"] = data
            _cache[key]["updated_at"] = time.time()
            _cache[key]["updating"] = False
        print(f"[cache] Обновлён {key}: {len(data)} байт")
    except Exception as e:
        with _cache_lock:
            _cache[key]["updating"] = False
        print(f"[cache] Не удалось скачать {key}: {e}")


def get_config(key: str, url: str) -> bytes:
    """Возвращает конфиг из кеша НЕМЕДЛЕННО.
    Если кеш пустой — качаем синхронно (только при первом старте).
    Если кеш устарел — запускаем фоновое обновление и отдаём старый."""
    with _cache_lock:
        entry = _cache[key]
        cache_has_data = entry["data"] is not None
        cache_fresh = cache_has_data and (time.time() - entry["updated_at"]) < CACHE_TTL
        already_updating = entry.get("updating", False)

    # Кеш свежий — отдаём сразу
    if cache_fresh:
        return entry["data"]

    # Кеш устарел но данные есть — запускаем фоновое обновление и отдаём старое
    if cache_has_data and not already_updating:
        with _cache_lock:
            _cache[key]["updating"] = True
        threading.Thread(target=_warm_one, args=(key, url), daemon=True).start()
        return entry["data"]

    # Кеш пустой (первый старт) — качаем синхронно, деваться некуда
    try:
        data = _download(url)
        with _cache_lock:
            _cache[key]["data"] = data
            _cache[key]["updated_at"] = time.time()
            _cache[key]["updating"] = False
        return data
    except Exception as e:
        print(f"[cache] Не удалось скачать {key}: {e}")
        raise


def _refresh_cache():
    """Фоновый поток: запускает прогрев кеша в фоне (не блокирует старт),
    затем обновляет каждые 15 минут."""
    # Прогрев при старте — НЕ ждём, сервер поднимается сразу
    threading.Thread(target=_warm_one, args=("vpn", VPN_CONFIG_URL), daemon=True).start()
    threading.Thread(target=_warm_one, args=("obs", OBHOD_CONFIG_URL), daemon=True).start()

    # Дальше — цикл обновления каждые 15 минут
    while True:
        time.sleep(CACHE_TTL)
        threading.Thread(target=_warm_one, args=("vpn", VPN_CONFIG_URL), daemon=True).start()
        threading.Thread(target=_warm_one, args=("obs", OBHOD_CONFIG_URL), daemon=True).start()


def keep_alive():
    """Пингует сам себя каждые 10 минут чтобы Render не засыпал."""
    while True:
        time.sleep(600)
        try:
            urllib.request.urlopen(RENDER_URL + "/", timeout=10)
        except Exception:
            pass


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        premium_expiry TEXT,
        is_premium INTEGER DEFAULT 0,
        reg_date TEXT,
        is_banned INTEGER DEFAULT 0
    )""")
    # Добавляем колонку is_banned если её нет (для старых БД)
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    conn.commit()
    conn.close()


init_db()
threading.Thread(target=keep_alive, daemon=True).start()
threading.Thread(target=_refresh_cache, daemon=True).start()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_banned_user(user_id: int) -> bool:
    """Проверяет, забанен ли пользователь."""
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT is_banned FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        conn.close()
        return bool(row and row["is_banned"] == 1)
    except Exception:
        return False


def is_premium_user(user_id: int) -> bool:
    """Проверяет, является ли пользователь премиум."""
    if user_id == ADMIN_ID:
        return True
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT is_premium, is_banned FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        conn.close()
        if not row:
            return False
        if row["is_banned"] == 1:
            return False
        return bool(row["is_premium"] == 1)
    except Exception:
        return False


# ─── МАРШРУТЫ ─────────────────────────────────────────────

@app.route('/<int:user_id>')
def serve_vpn(user_id):
    """Обычный VPN. Забаненным — пустой конфиг чтобы INCY сбросил кеш."""
    if is_banned_user(user_id):
        return '', 200
    try:
        content = get_config("vpn", VPN_CONFIG_URL)
    except Exception as e:
        return f"upstream error: {e}", 502
    return Response(
        content,
        status=200,
        headers={
            "Content-Type": "text/plain; charset=utf-8",
            "profile-title": "CBN VPN",
            "Cache-Control": "no-cache",
        }
    )


@app.route('/<int:user_id>/obs')
def serve_obs(user_id):
    """ОБС — только для премиум. Забаненным — пустой конфиг."""
    if is_banned_user(user_id):
        return '', 200
    if not is_premium_user(user_id):
        return redirect(VPN_CONFIG_URL, code=302)
    # Качаем напрямую с GitHub с коротким таймаутом и отдаём с заголовком
    try:
        data = _download(OBHOD_CONFIG_URL, timeout=10, retries=1)
        return Response(
            data,
            status=200,
            headers={
                "Content-Type": "text/plain; charset=utf-8",
                "profile-title": "CBN VPN Premium",
                "Cache-Control": "no-cache",
            }
        )
    except Exception:
        # Не успели скачать — редирект как fallback (без названия, но работает)
        return redirect(OBHOD_CONFIG_URL, code=302)


# ─── ADMIN API ────────────────────────────────────────────

@app.route('/set_premium/<int:user_id>/<int:status>', methods=['POST'])
def set_premium(user_id, status):
    """Бот вызывает этот endpoint при выдаче/снятии премиума."""
    secret = request.headers.get('X-Secret', '')
    if secret != SECRET_KEY:
        return 'Forbidden', 403
    try:
        conn = get_db()
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, is_premium) VALUES (?, ?)",
            (user_id, status)
        )
        # При выдаче премиума также снимаем бан на случай если он был
        conn.execute(
            "UPDATE users SET is_premium=?, is_banned=0 WHERE user_id=?",
            (status, user_id)
        )
        conn.commit()
        conn.close()
        return 'OK', 200
    except Exception as e:
        return str(e), 500


@app.route('/unban_user/<int:user_id>', methods=['POST'])
def unban_user(user_id):
    """Бот вызывает при разбане пользователя — снимает флаг is_banned."""
    secret = request.headers.get('X-Secret', '')
    if secret != SECRET_KEY:
        return 'Forbidden', 403
    try:
        conn = get_db()
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, is_banned, is_premium) VALUES (?, 0, 0)",
            (user_id,)
        )
        conn.execute(
            "UPDATE users SET is_banned=0 WHERE user_id=?",
            (user_id,)
        )
        conn.commit()
        conn.close()
        return 'OK', 200
    except Exception as e:
        return str(e), 500


@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """Бот вызывает при бане пользователя — ставит флаг is_banned."""
    secret = request.headers.get('X-Secret', '')
    if secret != SECRET_KEY:
        return 'Forbidden', 403
    try:
        conn = get_db()
        # Вставляем если нет, затем обновляем флаги
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, is_banned, is_premium) VALUES (?, 1, 0)",
            (user_id,)
        )
        conn.execute(
            "UPDATE users SET is_banned=1, is_premium=0 WHERE user_id=?",
            (user_id,)
        )
        conn.commit()
        conn.close()
        return 'OK', 200
    except Exception as e:
        return str(e), 500


@app.route('/')
def health():
    return "CBN VPN Web Server is Online", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
