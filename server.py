"""
CBN VPN Server - v5.5
Фикс: Обычная НЕ Premium, чистка f0, перевод стран
Формат: Город/Страна Флаг · Транспорт
"""

import urllib.request
import threading
import time
import re
import base64
import json
from datetime import datetime
from flask import Flask, request, Response, redirect

app = Flask(__name__)

VPN_CONFIG_URL = "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt"
OBHOD_CONFIG_URL = "https://raw.githack.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt"
RENDER_URL = "https://cbn-vpn-server.onrender.com/"
SECRET_KEY = "cbn_secret_2026"
CACHE_TTL = 900

CITY_DATA = {
    # Страны
    "united states": ("США", "🇺🇸"), "usa": ("США", "🇺🇸"),
    "germany": ("Германия", "🇩🇪"), "netherlands": ("Нидерланды", "🇳🇱"),
    "finland": ("Финляндия", "🇫🇮"), "sweden": ("Швеция", "🇸🇪"),
    "norway": ("Норвегия", "🇳🇴"), "switzerland": ("Швейцария", "🇨🇭"),
    "france": ("Франция", "🇫🇷"), "united kingdom": ("Великобритания", "🇬🇧"),
    "uk": ("Великобритания", "🇬🇧"), "canada": ("Канада", "🇨🇦"),
    "japan": ("Япония", "🇯🇵"), "singapore": ("Сингапур", "🇸🇬"),
    "hong kong": ("Гонконг", "🇭🇰"), "italy": ("Италия", "🇮🇹"),
    "spain": ("Испания", "🇪🇸"), "poland": ("Польша", "🇵🇱"),
    "latvia": ("Латвия", "🇱🇻"), "lithuania": ("Литва", "🇱🇹"),
    "estonia": ("Эстония", "🇪🇪"), "russia": ("Россия", "🇷🇺"),
    "ukraine": ("Украина", "🇺🇦"), "turkey": ("Турция", "🇹🇷"),
    "india": ("Индия", "🇮🇳"), "brazil": ("Бразилия", "🇧🇷"),
    "australia": ("Австралия", "🇦🇺"), "austria": ("Австрия", "🇦🇹"),
    "belgium": ("Бельгия", "🇧🇪"), "czech": ("Чехия", "🇨🇿"),
    "denmark": ("Дания", "🇩🇰"), "ireland": ("Ирландия", "🇮🇪"),
    "portugal": ("Португалия", "🇵🇹"), "romania": ("Румыния", "🇷🇴"),
    "slovakia": ("Словакия", "🇸🇰"), "bulgaria": ("Болгария", "🇧🇬"),
    "croatia": ("Хорватия", "🇭🇷"), "greece": ("Греция", "🇬🇷"),
    "hungary": ("Венгрия", "🇭🇺"), "serbia": ("Сербия", "🇷🇸"),
    "south korea": ("Корея", "🇰🇷"), "taiwan": ("Тайвань", "🇹🇼"),
    "vietnam": ("Вьетнам", "🇻🇳"), "thailand": ("Таиланд", "🇹🇭"),
    "malaysia": ("Малайзия", "🇲🇾"), "indonesia": ("Индонезия", "🇮🇩"),
    "philippines": ("Филиппины", "🇵🇭"), "mexico": ("Мексика", "🇲🇽"),
    "argentina": ("Аргентина", "🇦🇷"), "chile": ("Чили", "🇨🇱"),
    "south africa": ("ЮАР", "🇿🇦"), "israel": ("Израиль", "🇮🇱"),
    "uae": ("ОАЭ", "🇦🇪"), "kazakhstan": ("Казахстан", "🇰🇿"),
    "belarus": ("Беларусь", "🇧🇾"), "moldova": ("Молдова", "🇲🇩"),
    "georgia": ("Грузия", "🇬🇪"), "cyprus": ("Кипр", "🇨🇾"),
    # Города
    "amsterdam": ("Амстердам", "🇳🇱"), "frankfurt": ("Франкфурт", "🇩🇪"),
    "helsinki": ("Хельсинки", "🇫🇮"), "stockholm": ("Стокгольм", "🇸🇪"),
    "oslo": ("Осло", "🇳🇴"), "zurich": ("Цюрих", "🇨🇭"),
    "paris": ("Париж", "🇫🇷"), "london": ("Лондон", "🇬🇧"),
    "moscow": ("Москва", "🇷🇺"), "warsaw": ("Варшава", "🇵🇱"),
    "madrid": ("Мадрид", "🇪🇸"), "rome": ("Рим", "🇮🇹"),
    "vienna": ("Вена", "🇦🇹"), "prague": ("Прага", "🇨🇿"),
    "berlin": ("Берлин", "🇩🇪"), "munich": ("Мюнхен", "🇩🇪"),
    "lisbon": ("Лиссабон", "🇵🇹"), "dublin": ("Дублин", "🇮🇪"),
    "copenhagen": ("Копенгаген", "🇩🇰"), "brussels": ("Брюссель", "🇧🇪"),
    "budapest": ("Будапешт", "🇭🇺"), "bucharest": ("Бухарест", "🇷🇴"),
    "sofia": ("София", "🇧🇬"), "athens": ("Афины", "🇬🇷"),
    "riga": ("Рига", "🇱🇻"), "tallinn": ("Таллин", "🇪🇪"),
    "vilnius": ("Вильнюс", "🇱🇹"), "belgrade": ("Белград", "🇷🇸"),
    "istanbul": ("Стамбул", "🇹🇷"), "dubai": ("Дубай", "🇦🇪"),
    "tokyo": ("Токио", "🇯🇵"), "seoul": ("Сеул", "🇰🇷"),
    "sydney": ("Сидней", "🇦🇺"), "toronto": ("Торонто", "🇨🇦"),
    "new york": ("Нью-Йорк", "🇺🇸"), "los angeles": ("Лос-Анджелес", "🇺🇸"),
    "chicago": ("Чикаго", "🇺🇸"), "dallas": ("Даллас", "🇺🇸"),
    "miami": ("Майами", "🇺🇸"), "seattle": ("Сиэтл", "🇺🇸"),
    "sao paulo": ("Сан-Паулу", "🇧🇷"), "taipei": ("Тайбэй", "🇹🇼"),
    "mumbai": ("Мумбаи", "🇮🇳"), "delhi": ("Дели", "🇮🇳"),
    "tel aviv": ("Тель-Авив", "🇮🇱"),
}

def clean_name(name):
    """Очищает название от мусора"""
    name = re.sub(r'\[.*?\]', '', name)      # [ipv6]
    name = re.sub(r'\*[^*]+\*', '', name)    # *cidr*
    name = re.sub(r'\*', '', name)           # *
    name = re.sub(r'\bf\d+\b', '', name)     # f0, f1 и т.д.
    name = re.sub(r'\b[a-z]{1,2}\b', '', name, flags=re.IGNORECASE)  # одиночные буквы
    name = name.replace('|', ' ').replace('-', ' ')
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def extract_name(line):
    m = re.search(r'#(.+)$', line)
    if m:
        return clean_name(m.group(1))
    return ""

def get_transport(line):
    low = line.lower()
    if 'grpc' in low: return 'GRPC'
    if 'ws' in low or 'websocket' in low: return 'WS'
    if 'reality' in low: return 'Reality'
    if 'tcp' in low: return 'TCP'
    return ''

def is_anycast(line):
    return 'anycast' in line.lower()

def find_location(name):
    name_lower = name.lower().strip()
    for key in sorted(CITY_DATA.keys(), key=len, reverse=True):
        if key in name_lower:
            return CITY_DATA[key]
    words = [w for w in name_lower.split() if len(w) > 2]
    if words:
        return words[0].capitalize(), ""
    return name[:15], ""

def create_name(line):
    name = extract_name(line)
    transport = get_transport(line)

    if is_anycast(line):
        base = "🌍 Anycast"
    else:
        location, flag = find_location(name)
        base = f"{location} {flag}".strip() if flag else location

    return f"{base} · {transport}" if transport else base

def process_configs(raw, is_premium):
    try:
        content = raw.decode('utf-8', errors='ignore')
        lines = content.split('\n')

        configs = []
        for line in lines:
            line = line.strip()
            if line and line.startswith(('vless://', 'vmess://', 'trojan://', 'ss://', 'hysteria://', 'tuic://')):
                configs.append(line)

        result = []
        # ВАЖНО: is_premium=False -> CBN VPN, is_premium=True -> CBN VPN Premium
        result.append("#profile-title: CBN VPN Premium" if is_premium else "#profile-title: CBN VPN")
        result.append("#profile-update-interval: 6")
        result.append("")

        name_counts = {}
        config_list = []

        for line in configs:
            base = line[:line.rfind('#')] if '#' in line else line
            if base not in [c[0] for c in config_list]:
                name = create_name(line)
                config_list.append((base, name, line))
                name_counts[name] = name_counts.get(name, 0) + 1

        name_index = {}
        for base, name, line in config_list:
            if name_counts[name] > 1:
                name_index[name] = name_index.get(name, 0) + 1
                display = f"{name} #{name_index[name]}"
            else:
                display = name
            result.append(f"{base}#{display}")

        return '\n'.join(result).encode('utf-8')
    except Exception as e:
        print(f"Error: {e}")
        return raw

# ============================================================
_premium = {}
_banned = {}
_lock = threading.Lock()

def set_premium(uid, s):
    with _lock: _premium[uid] = s

def set_banned(uid, s):
    with _lock:
        _banned[uid] = s
        if s: _premium[uid] = False

def is_premium_user(uid):
    with _lock:
        return False if _banned.get(uid) else _premium.get(uid, False)

def is_banned_user(uid):
    with _lock:
        return _banned.get(uid, False)

_raw = {}
_raw_lock = threading.Lock()

def get_raw(url):
    with _raw_lock:
        if url in _raw:
            data, ts = _raw[url]
            if time.time() - ts < CACHE_TTL:
                return data
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=20).read()
    with _raw_lock:
        _raw[url] = (data, time.time())
    return data

def keep_alive():
    while True:
        time.sleep(600)
        try: urllib.request.urlopen(RENDER_URL + "/health", timeout=10)
        except: pass

def refresh_cache():
    while True:
        time.sleep(CACHE_TTL)
        try:
            urllib.request.urlopen(VPN_CONFIG_URL, timeout=20)
            urllib.request.urlopen(OBHOD_CONFIG_URL, timeout=20)
        except: pass

threading.Thread(target=keep_alive, daemon=True).start()
threading.Thread(target=refresh_cache, daemon=True).start()

@app.route('/<int:user_id>')
def serve_vpn(user_id):
    if is_banned_user(user_id):
        return '', 200
    try:
        is_prem = is_premium_user(user_id)
        content = process_configs(get_raw(VPN_CONFIG_URL), is_prem)
        title = "CBN VPN Premium" if is_prem else "CBN VPN"
        return Response(content, status=200, headers={
            "Content-Type": "text/plain; charset=utf-8",
            "profile-title": title,
        })
    except:
        return Response(get_raw(VPN_CONFIG_URL), status=200, headers={
            "Content-Type": "text/plain; charset=utf-8",
            "profile-title": "CBN VPN",
        })

@app.route('/<int:user_id>/obs')
def serve_obs(user_id):
    if is_banned_user(user_id):
        return '', 200
    if not is_premium_user(user_id):
        return redirect(VPN_CONFIG_URL, code=302)
    try:
        content = process_configs(get_raw(OBHOD_CONFIG_URL), True)
        return Response(content, status=200, headers={
            "Content-Type": "text/plain; charset=utf-8",
            "profile-title": "CBN VPN Premium",
        })
    except:
        return redirect(OBHOD_CONFIG_URL, code=302)

@app.route('/health')
def health():
    return {"status": "ok"}, 200

@app.route('/')
def root():
    return "CBN VPN v5.5", 200

@app.route('/set_premium/<int:uid>/<int:status>', methods=['POST'])
def api_sp(uid, status):
    if request.headers.get('X-Secret') != SECRET_KEY: return 'Forbidden', 403
    set_premium(uid, bool(status))
    return 'OK', 200

@app.route('/unban_user/<int:uid>', methods=['POST'])
def api_ub(uid):
    if request.headers.get('X-Secret') != SECRET_KEY: return 'Forbidden', 403
    set_banned(uid, False)
    return 'OK', 200

@app.route('/delete_user/<int:uid>', methods=['POST'])
def api_du(uid):
    if request.headers.get('X-Secret') != SECRET_KEY: return 'Forbidden', 403
    set_banned(uid, True)
    return 'OK', 200

@app.route('/sync', methods=['POST'])
def api_sync():
    if request.headers.get('X-Secret') != SECRET_KEY: return 'Forbidden', 403
    data = request.get_json(silent=True)
    if not data: return 'Bad JSON', 400
    with _lock:
        _premium.clear()
        _banned.clear()
        for uid in data.get('premium', []): _premium[int(uid)] = True
        for uid in data.get('banned', []): _banned[int(uid)] = True
    return 'OK', 200

@app.route('/flush_cache', methods=['POST'])
def api_fc():
    if request.headers.get('X-Secret') != SECRET_KEY: return 'Forbidden', 403
    with _raw_lock: _raw.clear()
    return 'OK', 200

if __name__ == '__main__':
    print("CBN VPN Server v5.5")
    print("Fixed: Premium label, clean f0, translate countries")
    app.run(host='0.0.0.0', port=5000, debug=False)
