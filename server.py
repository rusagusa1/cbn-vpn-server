"""
CBN VPN Server - STATELESS VERSION
Теперь состояние хранится только в памяти и синхронизируется с ботом.
При перезапуске сервер получает состояние от бота через /sync.
"""

import urllib.request
import threading
import time
import json
from flask import Flask, request, Response, redirect

app = Flask(__name__)

VPN_CONFIG_URL = "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt"
OBHOD_CONFIG_URL = "https://raw.githack.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt"
RENDER_URL = "https://cbn-vpn-server.onrender.com/"
SECRET_KEY = "cbn_secret_2026"
CACHE_TTL = 900

# ─── СОСТОЯНИЕ ТОЛЬКО В ПАМЯТИ ────────────────────────────
_premium_users: dict[int, bool] = {}
_banned_users: dict[int, bool] = {}
_state_lock = threading.Lock()

def set_premium(user_id: int, status: bool):
    with _state_lock:
        _premium_users[user_id] = status
    print(f"[state] premium user={user_id} status={status}")

def set_banned(user_id: int, status: bool):
    with _state_lock:
        _banned_users[user_id] = status
        if status:
            # При бане сбрасываем премиум
            _premium_users[user_id] = False
        else:
            # При разбане очищаем запись о бане
            if user_id in _banned_users:
                del _banned_users[user_id]
    print(f"[state] ban user={user_id} status={status}")

def is_premium_user(user_id: int) -> bool:
    with _state_lock:
        if _banned_users.get(user_id):
            return False
        return _premium_users.get(user_id, False)

def is_banned_user(user_id: int) -> bool:
    with _state_lock:
        return _banned_users.get(user_id, False)

# ─── КЕШ КОНФИГОВ ─────────────────────────────────────────
_cache = {
    "vpn":  {"data": None, "updated_at": 0, "updating": False},
    "obs":  {"data": None, "updated_at": 0, "updating": False},
}
_cache_lock = threading.Lock()

def _download(url: str, timeout: int = 30, retries: int = 3) -> bytes:
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise last_err

def _warm_one(key: str, url: str):
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
    with _cache_lock:
        entry = _cache[key]
        cache_has_data = entry["data"] is not None
        cache_fresh = cache_has_data and (time.time() - entry["updated_at"]) < CACHE_TTL
        already_updating = entry.get("updating", False)

    if cache_fresh:
        return entry["data"]

    if cache_has_data and not already_updating:
        with _cache_lock:
            _cache[key]["updating"] = True
        threading.Thread(target=_warm_one, args=(key, url), daemon=True).start()
        return entry["data"]

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
    threading.Thread(target=_warm_one, args=("vpn", VPN_CONFIG_URL), daemon=True).start()
    threading.Thread(target=_warm_one, args=("obs", OBHOD_CONFIG_URL), daemon=True).start()
    while True:
        time.sleep(CACHE_TTL)
        threading.Thread(target=_warm_one, args=("vpn", VPN_CONFIG_URL), daemon=True).start()
        threading.Thread(target=_warm_one, args=("obs", OBHOD_CONFIG_URL), daemon=True).start()

def keep_alive():
    while True:
        time.sleep(600)
        try:
            urllib.request.urlopen(RENDER_URL + "/health", timeout=10)
        except Exception:
            pass

threading.Thread(target=keep_alive, daemon=True).start()
threading.Thread(target=_refresh_cache, daemon=True).start()

# ─── МАРШРУТЫ ─────────────────────────────────────────────
@app.route('/<int:user_id>')
def serve_vpn(user_id):
    if is_banned_user(user_id):
        return '', 200
    try:
        content = get_config("vpn", VPN_CONFIG_URL)
    except Exception as e:
        return f"upstream error: {e}", 502
    return Response(content, status=200, headers={"Content-Type": "text/plain; charset=utf-8", "profile-title": "CBN VPN", "Cache-Control": "no-store, no-cache, must-revalidate"})

@app.route('/<int:user_id>/obs')
def serve_obs(user_id):
    if is_banned_user(user_id):
        return '', 200
    if not is_premium_user(user_id):
        return redirect(VPN_CONFIG_URL, code=302)
    try:
        data = _download(OBHOD_CONFIG_URL, timeout=10, retries=1)
        return Response(data, status=200, headers={"Content-Type": "text/plain; charset=utf-8", "profile-title": "CBN VPN Premium", "Cache-Control": "no-store, no-cache, must-revalidate"})
    except Exception:
        return redirect(OBHOD_CONFIG_URL, code=302)

# ─── HEALTH CHECK ─────────────────────────────────────────
@app.route('/health')
def health():
    with _state_lock:
        return {"status": "ok", "timestamp": time.time(), "premium": len(_premium_users), "banned": len(_banned_users)}, 200

@app.route('/')
def root():
    with _state_lock:
        return f"CBN VPN Server Online | premium={len(_premium_users)} banned={len(_banned_users)}", 200

# ─── ADMIN API ────────────────────────────────────────────
@app.route('/set_premium/<int:user_id>/<int:status>', methods=['POST'])
def api_set_premium(user_id, status):
    secret = request.headers.get('X-Secret', '')
    if secret != SECRET_KEY:
        return 'Forbidden', 403
    set_premium(user_id, bool(status))
    return 'OK', 200

@app.route('/unban_user/<int:user_id>', methods=['POST'])
def api_unban_user(user_id):
    secret = request.headers.get('X-Secret', '')
    if secret != SECRET_KEY:
        return 'Forbidden', 403
    set_banned(user_id, False)
    return 'OK', 200

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def api_delete_user(user_id):
    secret = request.headers.get('X-Secret', '')
    if secret != SECRET_KEY:
        return 'Forbidden', 403
    set_banned(user_id, True)
    return 'OK', 200

@app.route('/sync', methods=['POST'])
def api_sync():
    secret = request.headers.get('X-Secret', '')
    if secret != SECRET_KEY:
        return 'Forbidden', 403
    
    data = request.get_json(silent=True)
    if not data:
        return 'Bad JSON', 400
    
    premium_ids = set(int(i) for i in data.get('premium', []))
    banned_ids = set(int(i) for i in data.get('banned', []))
    
    with _state_lock:
        _premium_users.clear()
        _banned_users.clear()
        for uid in premium_ids:
            _premium_users[uid] = True
        for uid in banned_ids:
            _banned_users[uid] = True
    
    print(f"[state] sync: {len(premium_ids)} premium, {len(banned_ids)} banned")
    return 'OK', 200

@app.route('/flush_cache', methods=['POST'])
def flush_cache():
    secret = request.headers.get('X-Secret', '')
    if secret != SECRET_KEY:
        return 'Forbidden', 403
    
    with _cache_lock:
        for key in _cache:
            _cache[key]["data"] = None
            _cache[key]["updated_at"] = 0
            _cache[key]["updating"] = False
    
    threading.Thread(target=_warm_one, args=("vpn", VPN_CONFIG_URL), daemon=True).start()
    threading.Thread(target=_warm_one, args=("obs", OBHOD_CONFIG_URL), daemon=True).start()
    print("[cache] Принудительный сброс кэша выполнен")
    return 'OK — cache flushed, reloading in background', 200

@app.route('/check_batch', methods=['POST'])
def api_check_batch():
    """Проверка статуса для нескольких пользователей"""
    secret = request.headers.get('X-Secret', '')
    if secret != SECRET_KEY:
        return 'Forbidden', 403
    
    data = request.get_json(silent=True)
    if not data or 'user_ids' not in data:
        return 'Bad request', 400
    
    results = {}
    for user_id in data['user_ids']:
        uid = int(user_id)
        results[str(uid)] = {
            'banned': is_banned_user(uid),
            'premium': is_premium_user(uid)
        }
    
    return results, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
