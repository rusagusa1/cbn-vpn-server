import sqlite3
import urllib.request
import base64
import threading
import time
from flask import Flask, Response, request

app = Flask(__name__)
DB_PATH = 'vpn_database.db'

VPN_CONFIG_URL = (
    "https://cdn.jsdelivr.net/gh/igareck/vpn-configs-for-russia@main/BLACK_VLESS_RUS_mobile.txt"
)
OBHOD_CONFIG_URL = (
    "https://cdn.jsdelivr.net/gh/igareck/vpn-configs-for-russia@main/Vless-Reality-White-Lists-Rus-Mobile.txt"
)

_cache = {}
RENDER_URL = "https://cbn-vpn-server.onrender.com/"  # ⚠️ замени на свой URL после деплоя
SECRET_KEY = "cbn_secret_2026"  # ⚠️ поменяй на свой секрет, одинаковый в боте и сервере


def fetch_config(url: str) -> str:
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


def keep_alive():
    """Пингует сам себя каждые 10 минут чтобы Render не засыпал."""
    time.sleep(60)
    while True:
        try:
            urllib.request.urlopen(RENDER_URL + "/", timeout=10)
        except Exception:
            pass
        time.sleep(600)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/<int:user_id>')
def serve_config(user_id):
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT is_premium FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        conn.close()
        url = OBHOD_CONFIG_URL if (row and row["is_premium"] == 1) else VPN_CONFIG_URL
    except Exception:
        url = VPN_CONFIG_URL

    content = fetch_config(url)

    is_prem = row and row["is_premium"] == 1

    return Response(
        content,
        mimetype="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "no-cache",
            "profile-update-interval": "12",
            "ngrok-skip-browser-warning": "true",
            "profile-title": "CBN VPN — Премиум (ОБС)" if is_prem else "CBN VPN",
            "subscription-userinfo": "upload=0; download=0; total=0; expire=0",
            "profile-update-interval": "12",
            "support-url": "https://t.me/cherniy_bez_nomerov",
            "profile-web-page-url": "https://t.me/CBN_VPN",
            "channel-url": "https://t.me/CBN_VPN",
            "bot-url": "https://t.me/CBN_VPN",
        }
    )


@app.route('/update/<int:user_id>')
def force_update(user_id):
    _cache.clear()
    return serve_config(user_id)


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
    threading.Thread(target=keep_alive, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)
