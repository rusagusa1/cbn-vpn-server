import sqlite3
import urllib.request
import base64
import threading
import time
from flask import Flask, Response

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

    return Response(
        content,
        mimetype="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "no-cache",
            "profile-update-interval": "12",
            "ngrok-skip-browser-warning": "true",
        }
    )


@app.route('/update/<int:user_id>')
def force_update(user_id):
    _cache.clear()
    return serve_config(user_id)


@app.route('/')
def health():
    return "CBN VPN Web Server is Online", 200


if __name__ == '__main__':
    threading.Thread(target=keep_alive, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)
