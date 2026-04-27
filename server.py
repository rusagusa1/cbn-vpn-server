"""
CBN VPN Server - v5.3
Фикс: правильные названия подписок, конфиги не ломаются
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
    "germany": ("Германия", "🇩🇪"), "netherlands": ("Нидерланды", "🇳🇱"),
    "finland": ("Финляндия", "🇫🇮"), "sweden": ("Швеция", "🇸🇪"),
    "norway": ("Норвегия", "🇳🇴"), "switzerland": ("Швейцария", "🇨🇭"),
    "france": ("Франция", "🇫🇷"), "uk": ("Великобритания", "🇬🇧"),
    "united kingdom": ("Великобритания", "🇬🇧"), "usa": ("США", "🇺🇸"),
    "united states": ("США", "🇺🇸"), "canada": ("Канада", "🇨🇦"),
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
    "hungary": ("Венгрия", "🇭🇺"), "iceland": ("Исландия", "🇮🇸"),
    "luxembourg": ("Люксембург", "🇱🇺"), "serbia": ("Сербия", "🇷🇸"),
    "south korea": ("Корея", "🇰🇷"), "taiwan": ("Тайвань", "🇹🇼"),
    "vietnam": ("Вьетнам", "🇻🇳"), "thailand": ("Таиланд", "🇹🇭"),
    "malaysia": ("Малайзия", "🇲🇾"), "indonesia": ("Индонезия", "🇮🇩"),
    "mexico": ("Мексика", "🇲🇽"), "argentina": ("Аргентина", "🇦🇷"),
    "chile": ("Чили", "🇨🇱"), "south africa": ("ЮАР", "🇿🇦"),
    "israel": ("Израиль", "🇮🇱"), "uae": ("ОАЭ", "🇦🇪"),
    "kazakhstan": ("Казахстан", "🇰🇿"), "belarus": ("Беларусь", "🇧🇾"),
    "moldova": ("Молдова", "🇲🇩"), "georgia": ("Грузия", "🇬🇪"),
    "cyprus": ("Кипр", "🇨🇾"), "malta": ("Мальта", "🇲🇹"),
    "slovenia": ("Словения", "🇸🇮"),
    # Города
    "amsterdam": ("Амстердам", "🇳🇱"), "frankfurt": ("Франкфурт", "🇩🇪"),
    "helsinki": ("Хельсинки", "🇫🇮"), "stockholm": ("Стокгольм", "🇸🇪"),
    "oslo": ("Осло", "🇳🇴"), "zurich": ("Цюрих", "🇨🇭"),
    "paris": ("Париж", "🇫🇷"), "london": ("Лондон", "🇬🇧"),
    "moscow": ("Москва", "🇷🇺"), "st petersburg": ("СПб", "🇷🇺"),
    "warsaw": ("Варшава", "🇵🇱"), "madrid": ("Мадрид", "🇪🇸"),
    "barcelona": ("Барселона", "🇪🇸"), "rome": ("Рим", "🇮🇹"),
    "milan": ("Милан", "🇮🇹"), "vienna": ("Вена", "🇦🇹"),
    "prague": ("Прага", "🇨🇿"), "berlin": ("Берлин", "🇩🇪"),
    "munich": ("Мюнхен", "🇩🇪"), "hamburg": ("Гамбург", "🇩🇪"),
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
    "sao paulo": ("Сан-Паулу", "🇧🇷"), "mexico city": ("Мехико", "🇲🇽"),
    "buenos aires": ("Буэнос-Айрес", "🇦🇷"), "santiago": ("Сантьяго", "🇨🇱"),
    "taipei": ("Тайбэй", "🇹🇼"), "mumbai": ("Мумбаи", "🇮🇳"),
    "delhi": ("Дели", "🇮🇳"), "tel aviv": ("Тель-Авив", "🇮🇱"),
    "jakarta": ("Джакарта", "🇮🇩"), "bangkok": ("Бангкок", "🇹🇭"),
    "kuala lumpur": ("Куала-Лумпур", "🇲🇾"), "manila": ("Манила", "🇵🇭"),
}

def clean_name(name):
    """Очищает название от мусора"""
    name = re.sub(r'\[.*?\]', '', name)  # Убираем [ipv6], [*cidr] и т.д.
    name = re.sub(r'\b[a-z]{2}\b', '', name, flags=re.IGNORECASE)  # Убираем vk, ya
    name = re.sub(r'\s+', ' ', name).strip()  # Чистим пробелы
    name = name.strip('|').strip()  # Убираем палки
    return name

def extract_name(line):
    """Извлекает и очищает название конфига"""
    m = re.search(r'#([^#\n]+)$', line)
    if m:
        return clean_name(m.group(1))
    if line.startswith('vmess://'):
        try:
            b64 = line[8:]
            padding = 4 - len(b64) % 4
            if padding != 4:
                b64 += '=' * padding
            decoded = base64.b64decode(b64).decode('utf-8')
            data = json.loads(decoded)
            return clean_name(data.get('ps', ''))
        except:
            pass
    return ""

def get_transport(line):
    low = line.lower()
    if 'grpc' in low: return 'GRPC'
    if 'ws' in low: return 'WS'
    if 'reality' in low: return 'Reality'
    if 'tcp' in low: return 'TCP'
    return ''

def is_anycast(line):
    low = line.lower()
    name = extract_name(line).lower()
    return 'anycast' in low or 'anycast' in name

def is_cdn(line):
    low = line.lower()
    return 'cdn' in low

def is_reality(line):
    return 'reality' in line.lower()

def get_icon(line):
    if is_anycast(line): return "🌍"
    if is_cdn(line): return "📡"
    if is_reality(line): return "🔒"
    return "🌐"

def find_location(name):
    name_lower = name.lower()
    # Ищем самый длинный ключ (город приоритетнее страны)
    for key in sorted(CITY_DATA.keys(), key=len, reverse=True):
        if key in name_lower:
            return CITY_DATA[key]
    words = [w for w in name_lower.split() if len(w) > 2]
    if words:
        return words[0].capitalize(), ""
    return name[:12], ""

def create_name(line):
    name = extract_name(line)
    icon = get_icon(line)
    transport = get_transport(line)

    if is_anycast(line):
        return f"{icon} Anycast · {transport}" if transport else f"{icon} Anycast"

    location, flag = find_location(name)
    base = f"{icon} {location} {flag}" if flag else f"{icon} {location}"
    return f"{base} · {transport}" if transport else base

def process_configs(raw, is_premium=False):
    """Обработка конфигов БЕЗ изменения структуры URL"""
    try:
        content = raw.decode('utf-8', errors='ignore')
        lines = content.split('\n')

        configs = []
        for line in lines:
            line = line.strip()
            if line and (line.startswith(('vless://', 'vmess://', 'trojan://', 'ss://', 'hysteria://', 'tuic://'))):
                configs.append(line)

        result = []
        # Правильный заголовок
        if is_premium:
            result.append("#profile-title: CBN VPN Premium")
        else:
            result.append("#profile-title: CBN VPN")
        result.append("#profile-update-interval: 6")
        result.append("")

        # Собираем названия
        name_counts = {}
        config_data = []

        for line in configs:
            # Сохраняем всё ДО # для проверки дубликатов
            if '#' in line:
                base_for_dedup = line[:line.rfind('#')]
            else:
                base_for_dedup = line
            
            if base_for_dedup not in [x[0] for x in config_data]:
                name = create_name(line)
                config_data.append((base_for_dedup, name, line))
                name_counts[name] = name_counts.get(name, 0) + 1

        # Выводим с нумерацией
        name_index = {}
        for base, name, line in config_data:
            if name_counts[name] > 1:
                name_index[name] = name_index.get(name, 0) + 1
                display_name = f"{name} #{name_index[name]}"
            else:
                display_name = name

            # Безопасная замена названия
            if '#' in line:
                # Сохраняем всё до последнего #
                base_url = line[:line.rfind('#')]
                result.append(f"{base_url}#{display_name}")
            else:
                result.append(f"{line}#{display_name}")

        return '\n'.join(result).encode('utf-8')
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return raw

# ============================================================
# СОСТОЯНИЕ
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

# ============================================================
# КЭШ
# ============================================================
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

# ============================================================
# ФОН
# ============================================================
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

# ============================================================
# МАРШРУТЫ
# ============================================================
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
    return "CBN VPN Server v5.3", 200

# ADMIN API
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
    print("CBN VPN Server v5.3")
    print("Fixed: names, config structure preserved")
    app.run(host='0.0.0.0', port=5000, debug=False)
