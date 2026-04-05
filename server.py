import sqlite3
import urllib.request
import threading
import time
from flask import Flask, request, redirect

app = Flask(__name__)

DB_PATH = 'vpn_database.db'
VPN_CONFIG_URL = (
    "https://cdn.jsdelivr.net/gh/igareck/vpn-configs-for-russia@main/BLACK_VLESS_RUS_mobile.txt"
)
OBHOD_CONFIG_URL = (
    "https://cdn.jsdelivr.net/gh/igareck/vpn-configs-for-russia@main/Vless-Reality-White-Lists-Rus-Mobile.txt"
)
RENDER_URL = "https://cbn-vpn-server.onrender.com/"  # ⚠️ замени на свой URL после деплоя
SECRET_KEY = "cbn_secret_2026"                        # ⚠️ одинаковый в боте и сервере
ADMIN_ID = 1448623020


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
    """Обычный VPN — редирект напрямую на CDN. Забаненным — 403."""
    if is_banned_user(user_id):
        return 'Forbidden', 403
    return redirect(VPN_CONFIG_URL, code=302)


@app.route('/<int:user_id>/obs')
def serve_obs(user_id):
    """ОБС — только для премиум, иначе обычный VPN. Забаненным — 403."""
    if is_banned_user(user_id):
        return 'Forbidden', 403
    if not is_premium_user(user_id):
        return redirect(VPN_CONFIG_URL, code=302)
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
