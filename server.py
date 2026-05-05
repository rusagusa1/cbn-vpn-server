"""
CBN VPN Server - v5.17 FINAL
- Новый премиум-источник
- Персонализированный кэш для премиум-подписок (user_id)
- Оригинальная обработка имён (как в первой версии)
- Заголовки Standard / Premium
- Игнорирование 0.0.0.0
- Без семейного доступа, без фильтрации
- Gzip‑сжатие
"""

import urllib.request
import threading
import time
import re
import os
import gzip
from datetime import datetime
from urllib.parse import unquote
from flask import Flask, request, Response, redirect

app = Flask(__name__)

# =========================================================
# GZIP-СЖАТИЕ
# =========================================================
@app.after_request
def compress_response(response):
    if 'gzip' in request.headers.get('Accept-Encoding', '').lower():
        if response.direct_passthrough:
            return response
        content = response.get_data()
        if len(content) < 500:
            return response
        compressed = gzip.compress(content)
        response.set_data(compressed)
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = str(len(compressed))
    return response

# =========================================================
# URL И КЛЮЧИ
# =========================================================
VPN_CONFIG_URL = "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt"
OBHOD_CONFIG_URL = "https://raw.githubusercontent.com/ShadowException/VPN/refs/heads/main/configs/VPN-cat-top-100"  # новый
RENDER_URL = "https://cbn-vpn-server.onrender.com/"
SECRET_KEY = "cbn_secret_2026"
CACHE_TTL = 900

# =========================================================
# СЛОВАРЬ СТРАН И ГОРОДОВ (полный, как в первой версии)
# =========================================================
CITY_DATA = {
    # Страны
    "afghanistan": ("Афганистан", "🇦🇫"),
    "albania": ("Албания", "🇦🇱"),
    "algeria": ("Алжир", "🇩🇿"),
    "andorra": ("Андорра", "🇦🇩"),
    "angola": ("Ангола", "🇦🇴"),
    "argentina": ("Аргентина", "🇦🇷"),
    "armenia": ("Армения", "🇦🇲"),
    "australia": ("Австралия", "🇦🇺"),
    "austria": ("Австрия", "🇦🇹"),
    "azerbaijan": ("Азербайджан", "🇦🇿"),
    "bahamas": ("Багамы", "🇧🇸"),
    "bahrain": ("Бахрейн", "🇧🇭"),
    "bangladesh": ("Бангладеш", "🇧🇩"),
    "barbados": ("Барбадос", "🇧🇧"),
    "belarus": ("Беларусь", "🇧🇾"),
    "belgium": ("Бельгия", "🇧🇪"),
    "belize": ("Белиз", "🇧🇿"),
    "benin": ("Бенин", "🇧🇯"),
    "bhutan": ("Бутан", "🇧🇹"),
    "bolivia": ("Боливия", "🇧🇴"),
    "bosnia": ("Босния и Герцеговина", "🇧🇦"),
    "botswana": ("Ботсвана", "🇧🇼"),
    "brazil": ("Бразилия", "🇧🇷"),
    "brunei": ("Бруней", "🇧🇳"),
    "bulgaria": ("Болгария", "🇧🇬"),
    "burkina faso": ("Буркина-Фасо", "🇧🇫"),
    "burundi": ("Бурунди", "🇧🇮"),
    "cambodia": ("Камбоджа", "🇰🇭"),
    "cameroon": ("Камерун", "🇨🇲"),
    "canada": ("Канада", "🇨🇦"),
    "cape verde": ("Кабо-Верде", "🇨🇻"),
    "chad": ("Чад", "🇹🇩"),
    "chile": ("Чили", "🇨🇱"),
    "china": ("Китай", "🇨🇳"),
    "colombia": ("Колумбия", "🇨🇴"),
    "comoros": ("Коморы", "🇰🇲"),
    "congo": ("Конго", "🇨🇬"),
    "costa rica": ("Коста-Рика", "🇨🇷"),
    "croatia": ("Хорватия", "🇭🇷"),
    "cuba": ("Куба", "🇨🇺"),
    "cyprus": ("Кипр", "🇨🇾"),
    "czech": ("Чехия", "🇨🇿"),
    "denmark": ("Дания", "🇩🇰"),
    "djibouti": ("Джибути", "🇩🇯"),
    "dominican republic": ("Доминикана", "🇩🇴"),
    "ecuador": ("Эквадор", "🇪🇨"),
    "egypt": ("Египет", "🇪🇬"),
    "el salvador": ("Сальвадор", "🇸🇻"),
    "equatorial guinea": ("Экваториальная Гвинея", "🇬🇶"),
    "eritrea": ("Эритрея", "🇪🇷"),
    "estonia": ("Эстония", "🇪🇪"),
    "ethiopia": ("Эфиопия", "🇪🇹"),
    "fiji": ("Фиджи", "🇫🇯"),
    "finland": ("Финляндия", "🇫🇮"),
    "france": ("Франция", "🇫🇷"),
    "gabon": ("Габон", "🇬🇦"),
    "gambia": ("Гамбия", "🇬🇲"),
    "georgia": ("Грузия", "🇬🇪"),
    "germany": ("Германия", "🇩🇪"),
    "ghana": ("Гана", "🇬🇭"),
    "greece": ("Греция", "🇬🇷"),
    "grenada": ("Гренада", "🇬🇩"),
    "guatemala": ("Гватемала", "🇬🇹"),
    "guinea": ("Гвинея", "🇬🇳"),
    "guyana": ("Гайана", "🇬🇾"),
    "haiti": ("Гаити", "🇭🇹"),
    "honduras": ("Гондурас", "🇭🇳"),
    "hungary": ("Венгрия", "🇭🇺"),
    "iceland": ("Исландия", "🇮🇸"),
    "india": ("Индия", "🇮🇳"),
    "indonesia": ("Индонезия", "🇮🇩"),
    "iran": ("Иран", "🇮🇷"),
    "iraq": ("Ирак", "🇮🇶"),
    "ireland": ("Ирландия", "🇮🇪"),
    "israel": ("Израиль", "🇮🇱"),
    "italy": ("Италия", "🇮🇹"),
    "jamaica": ("Ямайка", "🇯🇲"),
    "japan": ("Япония", "🇯🇵"),
    "jordan": ("Иордания", "🇯🇴"),
    "kazakhstan": ("Казахстан", "🇰🇿"),
    "kenya": ("Кения", "🇰🇪"),
    "kuwait": ("Кувейт", "🇰🇼"),
    "kyrgyzstan": ("Киргизия", "🇰🇬"),
    "laos": ("Лаос", "🇱🇦"),
    "latvia": ("Латвия", "🇱🇻"),
    "lebanon": ("Ливан", "🇱🇧"),
    "lesotho": ("Лесото", "🇱🇸"),
    "liberia": ("Либерия", "🇱🇷"),
    "libya": ("Ливия", "🇱🇾"),
    "lithuania": ("Литва", "🇱🇹"),
    "luxembourg": ("Люксембург", "🇱🇺"),
    "madagascar": ("Мадагаскар", "🇲🇬"),
    "malawi": ("Малави", "🇲🇼"),
    "malaysia": ("Малайзия", "🇲🇾"),
    "maldives": ("Мальдивы", "🇲🇻"),
    "mali": ("Мали", "🇲🇱"),
    "malta": ("Мальта", "🇲🇹"),
    "mauritania": ("Мавритания", "🇲🇷"),
    "mauritius": ("Маврикий", "🇲🇺"),
    "mexico": ("Мексика", "🇲🇽"),
    "moldova": ("Молдова", "🇲🇩"),
    "monaco": ("Монако", "🇲🇨"),
    "mongolia": ("Монголия", "🇲🇳"),
    "montenegro": ("Черногория", "🇲🇪"),
    "morocco": ("Марокко", "🇲🇦"),
    "mozambique": ("Мозамбик", "🇲🇿"),
    "myanmar": ("Мьянма", "🇲🇲"),
    "namibia": ("Намибия", "🇳🇦"),
    "nepal": ("Непал", "🇳🇵"),
    "netherlands": ("Нидерланды", "🇳🇱"),
    "new zealand": ("Новая Зеландия", "🇳🇿"),
    "nicaragua": ("Никарагуа", "🇳🇮"),
    "niger": ("Нигер", "🇳🇪"),
    "nigeria": ("Нигерия", "🇳🇬"),
    "north korea": ("Северная Корея", "🇰🇵"),
    "north macedonia": ("Северная Македония", "🇲🇰"),
    "norway": ("Норвегия", "🇳🇴"),
    "oman": ("Оман", "🇴🇲"),
    "pakistan": ("Пакистан", "🇵🇰"),
    "palau": ("Палау", "🇵🇼"),
    "palestine": ("Палестина", "🇵🇸"),
    "panama": ("Панама", "🇵🇦"),
    "papua new guinea": ("Папуа — Новая Гвинея", "🇵🇬"),
    "paraguay": ("Парагвай", "🇵🇾"),
    "peru": ("Перу", "🇵🇪"),
    "philippines": ("Филиппины", "🇵🇭"),
    "poland": ("Польша", "🇵🇱"),
    "portugal": ("Португалия", "🇵🇹"),
    "qatar": ("Катар", "🇶🇦"),
    "romania": ("Румыния", "🇷🇴"),
    "russia": ("Россия", "🇷🇺"),
    "rwanda": ("Руанда", "🇷🇼"),
    "saudi arabia": ("Саудовская Аравия", "🇸🇦"),
    "senegal": ("Сенегал", "🇸🇳"),
    "serbia": ("Сербия", "🇷🇸"),
    "seychelles": ("Сейшелы", "🇸🇨"),
    "sierra leone": ("Сьерра-Леоне", "🇸🇱"),
    "singapore": ("Сингапур", "🇸🇬"),
    "slovakia": ("Словакия", "🇸🇰"),
    "slovenia": ("Словения", "🇸🇮"),
    "somalia": ("Сомали", "🇸🇴"),
    "south africa": ("ЮАР", "🇿🇦"),
    "south korea": ("Корея", "🇰🇷"),
    "south sudan": ("Южный Судан", "🇸🇸"),
    "spain": ("Испания", "🇪🇸"),
    "sri lanka": ("Шри-Ланка", "🇱🇰"),
    "sudan": ("Судан", "🇸🇩"),
    "suriname": ("Суринам", "🇸🇷"),
    "sweden": ("Швеция", "🇸🇪"),
    "switzerland": ("Швейцария", "🇨🇭"),
    "syria": ("Сирия", "🇸🇾"),
    "taiwan": ("Тайвань", "🇹🇼"),
    "tajikistan": ("Таджикистан", "🇹🇯"),
    "tanzania": ("Танзания", "🇹🇿"),
    "thailand": ("Таиланд", "🇹🇭"),
    "togo": ("Того", "🇹🇬"),
    "trinidad and tobago": ("Тринидад и Тобаго", "🇹🇹"),
    "tunisia": ("Тунис", "🇹🇳"),
    "turkey": ("Турция", "🇹🇷"),
    "turkmenistan": ("Туркменистан", "🇹🇲"),
    "uganda": ("Уганда", "🇺🇬"),
    "ukraine": ("Украина", "🇺🇦"),
    "united arab emirates": ("ОАЭ", "🇦🇪"),
    "united kingdom": ("Великобритания", "🇬🇧"),
    "united states": ("США", "🇺🇸"),
    "uruguay": ("Уругвай", "🇺🇾"),
    "uzbekistan": ("Узбекистан", "🇺🇿"),
    "venezuela": ("Венесуэла", "🇻🇪"),
    "vietnam": ("Вьетнам", "🇻🇳"),
    "yemen": ("Йемен", "🇾🇪"),
    "zambia": ("Замбия", "🇿🇲"),
    "zimbabwe": ("Зимбабве", "🇿🇼"),

    # Аббревиатуры и синонимы
    "usa": ("США", "🇺🇸"),
    "uk": ("Великобритания", "🇬🇧"),
    "uae": ("ОАЭ", "🇦🇪"),
    "korea": ("Корея", "🇰🇷"),

    # Крупные города
    "amsterdam": ("Амстердам", "🇳🇱"),
    "athens": ("Афины", "🇬🇷"),
    "bangkok": ("Бангкок", "🇹🇭"),
    "barcelona": ("Барселона", "🇪🇸"),
    "beijing": ("Пекин", "🇨🇳"),
    "belgrade": ("Белград", "🇷🇸"),
    "berlin": ("Берлин", "🇩🇪"),
    "boston": ("Бостон", "🇺🇸"),
    "brussels": ("Брюссель", "🇧🇪"),
    "bucharest": ("Бухарест", "🇷🇴"),
    "budapest": ("Будапешт", "🇭🇺"),
    "buenos aires": ("Буэнос-Айрес", "🇦🇷"),
    "cairo": ("Каир", "🇪🇬"),
    "chicago": ("Чикаго", "🇺🇸"),
    "copenhagen": ("Копенгаген", "🇩🇰"),
    "dallas": ("Даллас", "🇺🇸"),
    "delhi": ("Дели", "🇮🇳"),
    "dubai": ("Дубай", "🇦🇪"),
    "dublin": ("Дублин", "🇮🇪"),
    "frankfurt": ("Франкфурт", "🇩🇪"),
    "geneva": ("Женева", "🇨🇭"),
    "helsinki": ("Хельсинки", "🇫🇮"),
    "hong kong": ("Гонконг", "🇭🇰"),
    "istanbul": ("Стамбул", "🇹🇷"),
    "jakarta": ("Джакарта", "🇮🇩"),
    "johannesburg": ("Йоханнесбург", "🇿🇦"),
    "kiev": ("Киев", "🇺🇦"),
    "kuala lumpur": ("Куала-Лумпур", "🇲🇾"),
    "lisbon": ("Лиссабон", "🇵🇹"),
    "ljubljana": ("Любляна", "🇸🇮"),
    "london": ("Лондон", "🇬🇧"),
    "los angeles": ("Лос-Анджелес", "🇺🇸"),
    "madrid": ("Мадрид", "🇪🇸"),
    "manila": ("Манила", "🇵🇭"),
    "melbourne": ("Мельбурн", "🇦🇺"),
    "mexico city": ("Мехико", "🇲🇽"),
    "miami": ("Майами", "🇺🇸"),
    "milan": ("Милан", "🇮🇹"),
    "minsk": ("Минск", "🇧🇾"),
    "montreal": ("Монреаль", "🇨🇦"),
    "moscow": ("Москва", "🇷🇺"),
    "mumbai": ("Мумбаи", "🇮🇳"),
    "munich": ("Мюнхен", "🇩🇪"),
    "nairobi": ("Найроби", "🇰🇪"),
    "new york": ("Нью-Йорк", "🇺🇸"),
    "oslo": ("Осло", "🇳🇴"),
    "paris": ("Париж", "🇫🇷"),
    "prague": ("Прага", "🇨🇿"),
    "reykjavik": ("Рейкьявик", "🇮🇸"),
    "riga": ("Рига", "🇱🇻"),
    "rio de janeiro": ("Рио-де-Жанейро", "🇧🇷"),
    "rome": ("Рим", "🇮🇹"),
    "santiago": ("Сантьяго", "🇨🇱"),
    "sao paulo": ("Сан-Паулу", "🇧🇷"),
    "seattle": ("Сиэтл", "🇺🇸"),
    "seoul": ("Сеул", "🇰🇷"),
    "shanghai": ("Шанхай", "🇨🇳"),
    "sofia": ("София", "🇧🇬"),
    "stockholm": ("Стокгольм", "🇸🇪"),
    "sydney": ("Сидней", "🇦🇺"),
    "tallinn": ("Таллин", "🇪🇪"),
    "tbilisi": ("Тбилиси", "🇬🇪"),
    "tehran": ("Тегеран", "🇮🇷"),
    "tokyo": ("Токио", "🇯🇵"),
    "toronto": ("Торонто", "🇨🇦"),
    "vienna": ("Вена", "🇦🇹"),
    "vilnius": ("Вильнюс", "🇱🇹"),
    "warsaw": ("Варшава", "🇵🇱"),
    "zagreb": ("Загреб", "🇭🇷"),
    "zurich": ("Цюрих", "🇨🇭"),
}

# =========================================================
# ЗАГОЛОВКИ ПОДПИСОК
# =========================================================
STANDARD_HEADERS = """#profile-title: CBN VPN Standard
#profile-update-interval: 2
#support-url: https://t.me/CBN_VPN
#announce: Стандартная подписка. Используется при отсутствии белых списков на любом типе соединения. Для обхода белых списков приобретите премиум-подписку в боте.
"""

PREMIUM_HEADERS = """#profile-title: CBN VPN Premium
#profile-update-interval: 2
#support-url: https://t.me/CBN_VPN
#announce: Премиум-подписка, предназначенная для обхода белых списков ("глушилок"). Использовать исключительно на мобильном интернете и только при белых списках.
"""

# =========================================================
# ОРИГИНАЛЬНЫЕ ФУНКЦИИ ОБРАБОТКИ ИМЁН (из первого server.py)
# =========================================================
def clean_name(name):
    name = unquote(name)
    name = re.sub(r'[^\x00-\x7F\u0400-\u04FFa-zA-Z\s]', '', name)
    name = re.sub(r'\[.*?\]', '', name)
    name = re.sub(r'\*[^*]+\*', '', name)
    name = re.sub(r'\*', '', name)
    name = re.sub(r'\bf\d+\b', '', name)
    name = re.sub(r'\b[a-z]{1,2}\b', '', name, flags=re.IGNORECASE)
    name = name.replace('|', ' ').replace('-', ' ')
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def extract_name(line):
    m = re.search(r'#(.+)$', line)
    if m: return clean_name(m.group(1))
    return ""

def get_transport(line):
    low = line.lower()
    if 'grpc' in low: return 'GRPC'
    if 'xhttp' in low: return 'XHTTP'
    if 'ws' in low: return 'WS'
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
    if 'united' in name_lower:
        return ("США", "🇺🇸")
    words = [w for w in name_lower.split() if len(w) > 2]
    return (words[0].capitalize(), "") if words else (name[:15], "")

def create_name(line, ping_map=None):
    name = extract_name(line)
    transport = get_transport(line)
    if is_anycast(line):
        base = "🌍 Global"
    else:
        location, flag = find_location(name)
        base = f"{location} {flag}".strip() if flag else location
    if ping_map:
        match = re.search(r'@([^:]+):', line)
        if match:
            host = match.group(1)
            latency = ping_map.get(host)
            if latency is not None:
                base += f" · {latency:.0f}ms"
    return f"{base} · {transport}" if transport else base

# =========================================================
# ОБРАБОТКА КОНФИГОВ (с фильтром 0.0.0.0)
# =========================================================
def process_configs(raw, headers=""):
    try:
        content = raw.decode('utf-8', errors='ignore')
        lines = content.split('\n')
        configs = []
        for line in lines:
            line = line.strip()
            if not line or not line.startswith(('vless://', 'vmess://', 'trojan://', 'ss://', 'hysteria://', 'hysteria2://', 'tuic://')):
                continue
            # Игнорируем невалидные хосты
            match = re.search(r'@([^:]+):', line)
            if not match:
                match = re.search(r'://([^:]+):', line)
            if match and match.group(1) in ('0.0.0.0', '127.0.0.1', ''):
                continue
            configs.append(line)

        name_counts = {}
        config_list = []
        for line in configs:
            base = line[:line.rfind('#')] if '#' in line else line
            if base not in [c[0] for c in config_list]:
                name = create_name(line)
                config_list.append((base, name))
                name_counts[name] = name_counts.get(name, 0) + 1

        result = []
        name_index = {}
        for base, name in config_list:
            if name_counts[name] > 1:
                name_index[name] = name_index.get(name, 0) + 1
                display = f"{name} #{name_index[name]}"
            else:
                display = name
            result.append(f"{base}#{display}")

        full_config = headers + '\n'.join(result)
        return full_config.encode('utf-8')
    except:
        return raw

# =========================================================
# СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЕЙ
# =========================================================
_premium = {}; _banned = {}; _lock = threading.Lock()

def set_premium(uid, s):
    with _lock: _premium[uid] = s
def set_banned(uid, s):
    with _lock:
        _banned[uid] = s
        if s: _premium[uid] = False

def is_premium_user(uid):
    with _lock:
        if _banned.get(uid): return False
        return _premium.get(uid, False)

def is_banned_user(uid):
    with _lock:
        return _banned.get(uid, False)

# =========================================================
# КЭШ И ЗАГРУЗКА (с персональным ключом для премиум)
# =========================================================
_raw = {}; _raw_lock = threading.Lock()
_processed = {}; _processed_lock = threading.Lock()

def get_raw(url):
    with _raw_lock:
        if url in _raw:
            data, ts = _raw[url]
            if time.time() - ts < CACHE_TTL: return data
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=20).read()
    with _raw_lock: _raw[url] = (data, time.time())
    return data

def get_processed(url, headers="", user_id=None):
    with _processed_lock:
        cache_key = url + headers + (str(user_id) if user_id else "")
        if cache_key in _processed:
            data, ts = _processed[cache_key]
            if time.time() - ts < CACHE_TTL: return data
    raw = get_raw(url)
    processed = process_configs(raw, headers)
    with _processed_lock:
        _processed[cache_key] = (processed, time.time())
    return processed

# =========================================================
# KEEP ALIVE
# =========================================================
def keep_alive():
    while True:
        time.sleep(600)
        try: urllib.request.urlopen(RENDER_URL + "/health", timeout=10)
        except: pass

threading.Thread(target=keep_alive, daemon=True).start()

# =========================================================
# МАРШРУТЫ
# =========================================================
@app.route('/<int:user_id>')
def serve_vpn(user_id):
    if is_banned_user(user_id): return '', 200
    try:
        content = get_processed(VPN_CONFIG_URL, STANDARD_HEADERS)
        return Response(content, status=200, headers={"Content-Type": "text/plain; charset=utf-8", "profile-title": "CBN VPN Standard"})
    except:
        return Response(get_raw(VPN_CONFIG_URL), status=200, headers={"Content-Type": "text/plain; charset=utf-8", "profile-title": "CBN VPN Standard"})

@app.route('/<int:user_id>/obs')
def serve_obs(user_id):
    if is_banned_user(user_id): return '', 200
    if not is_premium_user(user_id):
        return redirect(VPN_CONFIG_URL, code=302)
    try:
        # персональный кэш по user_id
        content = get_processed(OBHOD_CONFIG_URL, PREMIUM_HEADERS, user_id)
        return Response(content, status=200, headers={"Content-Type": "text/plain; charset=utf-8", "profile-title": "CBN VPN Premium"})
    except:
        return redirect(OBHOD_CONFIG_URL, code=302)

@app.route('/health')
def health():
    return {"status": "ok"}, 200

@app.route('/')
def root():
    return "CBN VPN v5.17", 200

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
        _premium.clear(); _banned.clear()
        for uid in data.get('premium', []): _premium[int(uid)] = True
        for uid in data.get('banned', []): _banned[int(uid)] = True
    return 'OK', 200

@app.route('/flush_cache', methods=['POST'])
def api_fc():
    if request.headers.get('X-Secret') != SECRET_KEY: return 'Forbidden', 403
    with _raw_lock: _raw.clear()
    with _processed_lock: _processed.clear()
    return 'OK', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"CBN VPN v5.17 | Personal cache | Port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
