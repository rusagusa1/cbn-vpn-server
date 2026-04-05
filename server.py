import sqlite3
import urllib.request
import base64
import threading
import time
from flask import Flask, Response, request, redirect

app = Flask(__name__)

DB_PATH = 'vpn_database.db'
VPN_CONFIG_URL = (
    "https://cdn.jsdelivr.net/gh/igareck/vpn-configs-for-russia@main/BLACK_VLESS_RUS_mobile.txt"
)
OBHOD_CONFIG_URL = (
    "https://cdn.jsdelivr.net/gh/igareck/vpn-configs-for-russia@main/Vless-Reality-White-Lists-Rus-Mobile.txt"
)
_cache = {}
_cache_ready = False  # True когда оба конфига уже загружены при старте

RENDER_URL = "https://cbn-vpn-server.onrender.com/"  # ⚠️ замени на свой URL после деплоя
SECRET_KEY = "cbn_secret_2026"                        # ⚠️ одинаковый в боте и сервере
ADMIN_ID = 1448623020


def fetch_config(url: str) -> str:
    """Возвращает конфиг из кэша или скачивает его."""
    if url in _cache:
        return _cache[url]
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            raw = r.read()
        content = base64.b64encode(raw).decode("utf-8")
        _cache[url] = content
        return content
    except Exception as e:
        error_text = f"# Ошибка загрузки конфига: {e}"
        return base64.b64encode(error_text.encode()).decode()


def warm_cache():
    """Загружает оба конфига сразу при старте в фоновом потоке."""
    global _cache_ready
    for url in (VPN_CONFIG_URL, OBHOD_CONFIG_URL):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                raw = r.read()
            _cache[url] = base64.b64encode(raw).decode("utf-8")
        except Exception:
            pass  # при следующем запросе попробуем ещё раз
    _cache_ready = True


def keep_alive():
    """Пингует сам себя каждые 10 минут чтобы Render не засыпал."""
    time.sleep(60)
    while True:
        try:
            urllib.request.urlopen(RENDER_URL + "/", timeout=10)
        except Exception:
            pass
        time.sleep(600)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        premium_expiry TEXT,
        is_premium INTEGER DEFAULT 0,
        reg_date TEXT
    )""")
    conn.commit()
    conn.close()


init_db()
# Запускаем прогрев кэша при любом способе запуска (gunicorn или python напрямую)
threading.Thread(target=warm_cache, daemon=True).start()
threading.Thread(target=keep_alive, daemon=True).start()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_premium_user(user_id: int) -> bool:
    """Проверяет, является ли пользователь премиум."""
    if user_id == ADMIN_ID:
        return True
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT is_premium FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        conn.close()
        return bool(row and row["is_premium"] == 1)
    except Exception:
        return False


def make_response(content: str, title: str) -> Response:
    return Response(
        content,
        mimetype="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "no-cache",
            "profile-update-interval": "12",
            "ngrok-skip-browser-warning": "true",
            "profile-title": title,
            "subscription-userinfo": "upload=0; download=0; total=0; expire=0",
            "support-url": "https://t.me/cherniy_bez_nomerov",
            "profile-web-page-url": "https://t.me/CBN_VPN",
            "channel-url": "https://t.me/CBN_VPN",
            "bot-url": "https://t.me/CBN_VPN",
        }
    )


# ─── МАРШРУТЫ ─────────────────────────────────────────────

@app.route('/<int:user_id>')
def serve_vpn(user_id):
    """Обычный VPN — для всех пользователей."""
    # Если кэш ещё не прогрелся — редиректим напрямую на CDN (мгновенно)
    if VPN_CONFIG_URL not in _cache:
        return redirect(VPN_CONFIG_URL, code=302)
    return make_response(_cache[VPN_CONFIG_URL], "CBN VPN")


@app.route('/<int:user_id>/obs')
def serve_obs(user_id):
    """ОБС — только для премиум-пользователей."""
    if not is_premium_user(user_id):
        url = VPN_CONFIG_URL
        title = "CBN VPN (нет Премиума)"
    else:
        url = OBHOD_CONFIG_URL
        title = "CBN VPN — ОБС (Премиум)"

    # Если кэш ещё не прогрелся — редиректим напрямую на CDN
    if url not in _cache:
        return redirect(url, code=302)
    return make_response(_cache[url], title)


@app.route('/update/<int:user_id>')
def force_update(user_id):
    _cache.clear()
    return serve_vpn(user_id)


@app.route('/update/<int:user_id>/obs')
def force_update_obs(user_id):
    _cache.clear()
    return serve_obs(user_id)


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
        conn.execute(
            "UPDATE users SET is_premium=? WHERE user_id=?",
            (status, user_id)
        )
        conn.commit()
        conn.close()
        return 'OK', 200
    except Exception as e:
        return str(e), 500


@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """Бот вызывает при бане пользователя."""
    secret = request.headers.get('X-Secret', '')
    if secret != SECRET_KEY:
        return 'Forbidden', 403
    try:
        conn = get_db()
        conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
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
