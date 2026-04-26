"""
CBN VPN Server - STATELESS VERSION
Состояние в памяти, синхронизация с ботом.
Переименование конфигов: флаги стран, перевод, 🌍 сохраняется.
"""

import urllib.request
import threading
import time
import json
import re
import base64
from urllib.parse import unquote, quote
from flask import Flask, request, Response, redirect

app = Flask(__name__)

VPN_CONFIG_URL = "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt"
OBHOD_CONFIG_URL = "https://raw.githack.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt"
RENDER_URL = "https://cbn-vpn-server.onrender.com/"
SECRET_KEY = "cbn_secret_2026"
CACHE_TTL = 900

# ─── СЛОВАРЬ СТРАН С ФЛАГАМИ ────────────────────────────────
COUNTRY_DATA = {
    "Netherlands": {"name": "Нидерланды", "flag": "🇳🇱"},
    "Germany": {"name": "Германия", "flag": "🇩🇪"},
    "France": {"name": "Франция", "flag": "🇫🇷"},
    "UK": {"name": "Англия", "flag": "🇬🇧"},
    "United Kingdom": {"name": "Англия", "flag": "🇬🇧"},
    "Sweden": {"name": "Швеция", "flag": "🇸🇪"},
    "Switzerland": {"name": "Швейцария", "flag": "🇨🇭"},
    "Finland": {"name": "Финляндия", "flag": "🇫🇮"},
    "Norway": {"name": "Норвегия", "flag": "🇳🇴"},
    "Poland": {"name": "Польша", "flag": "🇵🇱"},
    "Italy": {"name": "Италия", "flag": "🇮🇹"},
    "Spain": {"name": "Испания", "flag": "🇪🇸"},
    "Austria": {"name": "Австрия", "flag": "🇦🇹"},
    "Belgium": {"name": "Бельгия", "flag": "🇧🇪"},
    "Czech": {"name": "Чехия", "flag": "🇨🇿"},
    "Denmark": {"name": "Дания", "flag": "🇩🇰"},
    "Ireland": {"name": "Ирландия", "flag": "🇮🇪"},
    "Latvia": {"name": "Латвия", "flag": "🇱🇻"},
    "Lithuania": {"name": "Литва", "flag": "🇱🇹"},
    "Luxembourg": {"name": "Люксембург", "flag": "🇱🇺"},
    "Romania": {"name": "Румыния", "flag": "🇷🇴"},
    "Serbia": {"name": "Сербия", "flag": "🇷🇸"},
    "Slovakia": {"name": "Словакия", "flag": "🇸🇰"},
    "Slovenia": {"name": "Словения", "flag": "🇸🇮"},
    "Bulgaria": {"name": "Болгария", "flag": "🇧🇬"},
    "Hungary": {"name": "Венгрия", "flag": "🇭🇺"},
    "Greece": {"name": "Греция", "flag": "🇬🇷"},
    "Portugal": {"name": "Португалия", "flag": "🇵🇹"},
    "Moldova": {"name": "Молдова", "flag": "🇲🇩"},
    "Estonia": {"name": "Эстония", "flag": "🇪🇪"},
    "Iceland": {"name": "Исландия", "flag": "🇮🇸"},
    "Singapore": {"name": "Сингапур", "flag": "🇸🇬"},
    "Japan": {"name": "Япония", "flag": "🇯🇵"},
    "Hong Kong": {"name": "Гонконг", "flag": "🇭🇰"},
    "South Korea": {"name": "Корея", "flag": "🇰🇷"},
    "Taiwan": {"name": "Тайвань", "flag": "🇹🇼"},
    "Vietnam": {"name": "Вьетнам", "flag": "🇻🇳"},
    "Thailand": {"name": "Таиланд", "flag": "🇹🇭"},
    "India": {"name": "Индия", "flag": "🇮🇳"},
    "Indonesia": {"name": "Индонезия", "flag": "🇮🇩"},
    "Malaysia": {"name": "Малайзия", "flag": "🇲🇾"},
    "Philippines": {"name": "Филиппины", "flag": "🇵🇭"},
    "China": {"name": "Китай", "flag": "🇨🇳"},
    "Turkey": {"name": "Турция", "flag": "🇹🇷"},
    "Israel": {"name": "Израиль", "flag": "🇮🇱"},
    "Kazakhstan": {"name": "Казахстан", "flag": "🇰🇿"},
    "USA": {"name": "США", "flag": "🇺🇸"},
    "United States": {"name": "США", "flag": "🇺🇸"},
    "Canada": {"name": "Канада", "flag": "🇨🇦"},
    "Brazil": {"name": "Бразилия", "flag": "🇧🇷"},
    "Mexico": {"name": "Мексика", "flag": "🇲🇽"},
    "Argentina": {"name": "Аргентина", "flag": "🇦🇷"},
    "UAE": {"name": "ОАЭ", "flag": "🇦🇪"},
    "United Arab Emirates": {"name": "ОАЭ", "flag": "🇦🇪"},
    "Russia": {"name": "Россия", "flag": "🇷🇺"},
    "Anycast": {"name": "Универсальный", "flag": ""},
}

# ─── СОСТОЯНИЕ В ПАМЯТИ ────────────────────────────────────
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
            _premium_users[user_id] = False
        else:
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

# ─── ПЕРЕВОД НАЗВАНИЙ ──────────────────────────────────────

def clean_config_name(name: str) -> str:
    """
    Очищает название конфигурации:
    - 🌍 сохраняется если была в оригинале
    - Добавляет флаг страны
    - Убирает города, номера, IPv6, CIDR, технические суффиксы
    - Переводит страну на русский
    - Anycast → Универсальный
    """
    
    try:
        decoded = unquote(name)
    except:
        decoded = name
    
    # Проверяем наличие 🌍 и временно убираем
    has_planet = '🌍' in decoded
    
    if has_planet:
        cleaned_text = decoded.replace('🌍', '').strip()
    else:
        cleaned_text = decoded
    
    # Удаляем IPv6 адреса
    cleaned_text = re.sub(r'\[?[0-9a-fA-F:]{10,}\]?', '', cleaned_text)
    
    # Удаляем CIDR маски
    cleaned_text = re.sub(r'/\d{1,3}', '', cleaned_text)
    
    # Удаляем номера серверов
    cleaned_text = re.sub(r'[-_#]\d{1,3}$', '', cleaned_text)
    cleaned_text = re.sub(r'\s*\(\d+\)', '', cleaned_text)
    cleaned_text = re.sub(r'\s*\[\d+\]', '', cleaned_text)
    
    # Убираем города (всё после дефиса)
    parts = cleaned_text.split('-')
    if len(parts) > 1:
        cleaned_text = parts[0].strip()
    
    # Удаляем технические суффиксы
    tech_suffixes = [
        'IPv6', 'IPV6', 'ipv6', 'v6', 'V6',
        'CIDR', 'cidr', 'CDN', 'cdn',
        'NAT', 'nat', 'TUN', 'tun',
        'Proxy', 'proxy', 'PROXY',
        'Elite', 'elite', 'ELITE',
        'Premium', 'premium', 'PREMIUM',
        'VIP', 'vip',
        'Pro', 'pro', 'PRO',
        'Max', 'max', 'MAX',
        'Plus', 'plus', 'PLUS',
        'Lite', 'lite', 'LITE',
        'Basic', 'basic', 'BASIC',
        'Standard', 'standard', 'STANDARD',
        'Ultra', 'ultra', 'ULTRA',
        'Super', 'super', 'SUPER',
        'Fast', 'fast', 'FAST',
        'Turbo', 'turbo', 'TURBO',
        'Extra', 'extra', 'EXTRA',
        'Special', 'special', 'SPECIAL',
    ]
    
    for suffix in tech_suffixes:
        cleaned_text = re.sub(rf'\b{suffix}\b', '', cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(rf'-{suffix}$', '', cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(rf'_{suffix}$', '', cleaned_text, flags=re.IGNORECASE)
    
    # Чистим пробелы и дефисы
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    cleaned_text = re.sub(r'-+', '-', cleaned_text)
    cleaned_text = cleaned_text.strip().strip('-').strip()
    
    # Anycast → Универсальный
    if 'anycast' in cleaned_text.lower():
        return f"🌍 Универсальный" if has_planet else "Универсальный"
    
    # Ищем страну и добавляем флаг + перевод
    for eng, data in COUNTRY_DATA.items():
        if eng.lower() == cleaned_text.lower() or eng.lower() in cleaned_text.lower():
            flag = data["flag"]
            ru_name = data["name"]
            if has_planet:
                return f"🌍 {flag} {ru_name}"
            else:
                return f"{flag} {ru_name}"
    
    # Если не нашли страну — возвращаем очищенное
    if has_planet:
        return f"🌍 {cleaned_text}" if cleaned_text else f"🌍 {decoded}"
    
    return cleaned_text if cleaned_text else decoded


def process_config_line(line: str) -> str:
    """Обрабатывает строку конфигурации любого протокола"""
    
    # VLESS, Trojan, Hysteria, TUIC с #name в конце
    if '#' in line and not line.startswith('vmess://'):
        base_url, sep, name = line.rpartition('#')
        new_name = clean_config_name(name)
        encoded_name = quote(new_name, safe='')
        return f"{base_url}#{encoded_name}"
    
    # Shadowsocks
    if line.startswith('ss://') or line.startswith('ssr://'):
        if '#' in line:
            base_url, sep, name = line.rpartition('#')
            new_name = clean_config_name(name)
            encoded_name = quote(new_name, safe='')
            return f"{base_url}#{encoded_name}"
        return line
    
    # VMess
    if line.startswith('vmess://'):
        try:
            base64_part = line[8:]
            padding = 4 - len(base64_part) % 4
            if padding != 4:
                base64_part += '=' * padding
            
            decoded = base64.b64decode(base64_part).decode('utf-8')
            config = json.loads(decoded)
            
            if 'ps' in config:
                config['ps'] = clean_config_name(config['ps'])
            
            new_json = json.dumps(config, ensure_ascii=False)
            new_base64 = base64.b64encode(new_json.encode('utf-8')).decode('utf-8')
            return f"vmess://{new_base64}"
        except Exception as e:
            print(f"[translate] Ошибка обработки VMess: {e}")
            return line
    
    # Hysteria2, TUIC и другие
    if any(line.startswith(proto) for proto in ['hysteria2://', 'tuic://', 'vless://', 'trojan://']):
        if '#' in line:
            base_url, sep, name = line.rpartition('#')
            new_name = clean_config_name(name)
            encoded_name = quote(new_name, safe='')
            return f"{base_url}#{encoded_name}"
        return line
    
    return line


def translate_config_text(config_text: str) -> str:
    """Обрабатывает весь конфиг"""
    if not config_text:
        return config_text
    
    lines = config_text.strip().split('\n')
    result_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            result_lines.append('')
            continue
        
        try:
            processed_line = process_config_line(line)
            result_lines.append(processed_line)
        except Exception as e:
            print(f"[translate] Ошибка обработки строки: {e}")
            result_lines.append(line)
    
    return '\n'.join(result_lines)

# ─── КЭШ КОНФИГОВ ─────────────────────────────────────────
_cache = {
    "vpn":  {"data": None, "translated": None, "updated_at": 0, "updating": False},
    "obs":  {"data": None, "translated": None, "updated_at": 0, "updating": False},
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
        translated = translate_config_text(data.decode('utf-8')).encode('utf-8')
        
        with _cache_lock:
            _cache[key]["data"] = data
            _cache[key]["translated"] = translated
            _cache[key]["updated_at"] = time.time()
            _cache[key]["updating"] = False
        print(f"[cache] Обновлён {key}: {len(data)} байт → переведён")
    except Exception as e:
        with _cache_lock:
            _cache[key]["updating"] = False
        print(f"[cache] Не удалось скачать {key}: {e}")

def get_config(key: str, url: str) -> bytes:
    with _cache_lock:
        entry = _cache[key]
        cache_has_data = entry["translated"] is not None
        cache_fresh = cache_has_data and (time.time() - entry["updated_at"]) < CACHE_TTL
        already_updating = entry.get("updating", False)

    if cache_fresh:
        return entry["translated"]

    if cache_has_data and not already_updating:
        with _cache_lock:
            _cache[key]["updating"] = True
        threading.Thread(target=_warm_one, args=(key, url), daemon=True).start()
        return entry["translated"]

    try:
        data = _download(url)
        translated = translate_config_text(data.decode('utf-8')).encode('utf-8')
        with _cache_lock:
            _cache[key]["data"] = data
            _cache[key]["translated"] = translated
            _cache[key]["updated_at"] = time.time()
            _cache[key]["updating"] = False
        return translated
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
        return Response(
            content, 
            status=200, 
            headers={
                "Content-Type": "text/plain; charset=utf-8", 
                "profile-title": "CBN VPN", 
                "Cache-Control": "no-store, no-cache, must-revalidate"
            }
        )
    except Exception as e:
        return f"upstream error: {e}", 502

@app.route('/<int:user_id>/obs')
def serve_obs(user_id):
    if is_banned_user(user_id):
        return '', 200
    if not is_premium_user(user_id):
        return redirect(VPN_CONFIG_URL, code=302)
    try:
        content = get_config("obs", OBHOD_CONFIG_URL)
        return Response(
            content, 
            status=200, 
            headers={
                "Content-Type": "text/plain; charset=utf-8", 
                "profile-title": "CBN VPN Premium", 
                "Cache-Control": "no-store, no-cache, must-revalidate"
            }
        )
    except Exception:
        return redirect(OBHOD_CONFIG_URL, code=302)

# ─── HEALTH CHECK ─────────────────────────────────────────
@app.route('/health')
def health():
    with _state_lock:
        return {
            "status": "ok", 
            "timestamp": time.time(), 
            "premium": len(_premium_users), 
            "banned": len(_banned_users)
        }, 200

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
            _cache[key]["translated"] = None
            _cache[key]["updated_at"] = 0
            _cache[key]["updating"] = False
    
    threading.Thread(target=_warm_one, args=("vpn", VPN_CONFIG_URL), daemon=True).start()
    threading.Thread(target=_warm_one, args=("obs", OBHOD_CONFIG_URL), daemon=True).start()
    print("[cache] Принудительный сброс кэша выполнен")
    return 'OK — cache flushed, reloading in background', 200

@app.route('/check_batch', methods=['POST'])
def api_check_batch():
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
