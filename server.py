"""
CBN VPN Server - v3.2
- Обычная подписка: CBN VPN
- Премиум/OBS подписка: CBN VPN Premium
- Короткие названия серверов
- Фоновый пинг
"""

import urllib.request
import threading
import time
import re
import socket
from datetime import datetime
from collections import OrderedDict
from flask import Flask, request, Response, redirect

app = Flask(__name__)

VPN_CONFIG_URL = "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt"
OBHOD_CONFIG_URL = "https://raw.githack.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt"
RENDER_URL = "https://cbn-vpn-server.onrender.com/"
SECRET_KEY = "cbn_secret_2026"
CACHE_TTL = 900
PING_CACHE_TTL = 600

# ============================================================
# ПЕРЕВОДЫ
# ============================================================
LOCATION_TRANSLATIONS = OrderedDict([
    # Страны
    ("Netherlands", "Нидерланды"), ("Germany", "Германия"), ("Finland", "Финляндия"),
    ("Sweden", "Швеция"), ("Norway", "Норвегия"), ("Switzerland", "Швейцария"),
    ("France", "Франция"), ("United Kingdom", "Великобритания"), ("UK", "Великобритания"),
    ("United States", "США"), ("USA", "США"), ("Canada", "Канада"),
    ("Japan", "Япония"), ("Singapore", "Сингапур"), ("Hong Kong", "Гонконг"),
    ("Italy", "Италия"), ("Spain", "Испания"), ("Poland", "Польша"),
    ("Latvia", "Латвия"), ("Lithuania", "Литва"), ("Estonia", "Эстония"),
    ("Russia", "Россия"), ("Ukraine", "Украина"), ("Turkey", "Турция"),
    ("India", "Индия"), ("Brazil", "Бразилия"), ("Australia", "Австралия"),
    ("Austria", "Австрия"), ("Belgium", "Бельгия"), ("Czech", "Чехия"),
    ("Denmark", "Дания"), ("Ireland", "Ирландия"), ("Portugal", "Португалия"),
    ("Romania", "Румыния"), ("Slovakia", "Словакия"), ("Bulgaria", "Болгария"),
    ("Croatia", "Хорватия"), ("Greece", "Греция"), ("Hungary", "Венгрия"),
    ("Iceland", "Исландия"), ("Luxembourg", "Люксембург"), ("Serbia", "Сербия"),
    ("South Korea", "Корея"), ("Taiwan", "Тайвань"), ("Vietnam", "Вьетнам"),
    ("Thailand", "Таиланд"), ("Malaysia", "Малайзия"), ("Indonesia", "Индонезия"),
    ("Philippines", "Филиппины"), ("Mexico", "Мексика"), ("Argentina", "Аргентина"),
    ("Chile", "Чили"), ("South Africa", "ЮАР"), ("Israel", "Израиль"),
    ("UAE", "ОАЭ"), ("Kazakhstan", "Казахстан"), ("Belarus", "Беларусь"),
    ("Moldova", "Молдова"), ("Georgia", "Грузия"), ("Cyprus", "Кипр"),
    ("Malta", "Мальта"), ("Slovenia", "Словения"),
    # Сокращения
    ("NL", "Нидерланды"), ("DE", "Германия"), ("FI", "Финляндия"),
    ("SE", "Швеция"), ("NO", "Норвегия"), ("CH", "Швейцария"),
    ("FR", "Франция"), ("IT", "Италия"), ("ES", "Испания"),
    ("PL", "Польша"), ("LV", "Латвия"), ("LT", "Литва"),
    ("EE", "Эстония"), ("RU", "Россия"), ("UA", "Украина"),
    ("TR", "Турция"), ("AT", "Австрия"), ("BE", "Бельгия"),
    ("CZ", "Чехия"), ("DK", "Дания"), ("IE", "Ирландия"),
    ("PT", "Португалия"), ("RO", "Румыния"), ("SK", "Словакия"),
    ("BG", "Болгария"), ("HR", "Хорватия"), ("GR", "Греция"),
    ("HU", "Венгрия"), ("IS", "Исландия"), ("LU", "Люксембург"),
    ("RS", "Сербия"), ("AU", "Австралия"), ("CA", "Канада"),
    ("JP", "Япония"), ("SG", "Сингапур"), ("HK", "Гонконг"),
    ("KR", "Корея"), ("TW", "Тайвань"), ("VN", "Вьетнам"),
    ("TH", "Таиланд"), ("MY", "Малайзия"), ("ID", "Индонезия"),
    ("IN", "Индия"), ("BR", "Бразилия"), ("MX", "Мексика"),
    ("AR", "Аргентина"), ("CL", "Чили"), ("ZA", "ЮАР"),
    ("IL", "Израиль"), ("KZ", "Казахстан"), ("BY", "Беларусь"),
    ("MD", "Молдова"), ("GE", "Грузия"), ("CY", "Кипр"),
    # Города
    ("Amsterdam", "Амстердам"), ("Frankfurt", "Франкфурт"), ("Helsinki", "Хельсинки"),
    ("Stockholm", "Стокгольм"), ("Oslo", "Осло"), ("Zurich", "Цюрих"),
    ("Paris", "Париж"), ("London", "Лондон"), ("Moscow", "Москва"),
    ("Kiev", "Киев"), ("Warsaw", "Варшава"), ("Madrid", "Мадрид"),
    ("Rome", "Рим"), ("Milan", "Милан"), ("Vienna", "Вена"),
    ("Prague", "Прага"), ("Berlin", "Берлин"), ("Munich", "Мюнхен"),
    ("Hamburg", "Гамбург"), ("Lisbon", "Лиссабон"), ("Dublin", "Дублин"),
    ("Copenhagen", "Копенгаген"), ("Brussels", "Брюссель"), ("Budapest", "Будапешт"),
    ("Bucharest", "Бухарест"), ("Sofia", "София"), ("Athens", "Афины"),
    ("Riga", "Рига"), ("Tallinn", "Таллин"), ("Vilnius", "Вильнюс"),
    ("Belgrade", "Белград"), ("Bratislava", "Братислава"), ("Istanbul", "Стамбул"),
    ("Dubai", "Дубай"), ("Tel Aviv", "Тель-Авив"), ("Tokyo", "Токио"),
    ("Seoul", "Сеул"), ("Sydney", "Сидней"), ("Toronto", "Торонто"),
    ("New York", "Нью-Йорк"), ("Los Angeles", "Лос-Анджелес"), ("Miami", "Майами"),
    ("Chicago", "Чикаго"), ("Dallas", "Даллас"), ("Seattle", "Сиэтл"),
    ("Sao Paulo", "Сан-Паулу"), ("Mexico City", "Мехико"),
    ("Buenos Aires", "Буэнос-Айрес"), ("St Petersburg", "СПб"),
])

COUNTRY_FLAGS = {
    "Нидерланды": "🇳🇱", "Германия": "🇩🇪", "Финляндия": "🇫🇮",
    "Швеция": "🇸🇪", "Норвегия": "🇳🇴", "Швейцария": "🇨🇭",
    "Франция": "🇫🇷", "Великобритания": "🇬🇧", "США": "🇺🇸",
    "Канада": "🇨🇦", "Япония": "🇯🇵", "Сингапур": "🇸🇬",
    "Гонконг": "🇭🇰", "Италия": "🇮🇹", "Испания": "🇪🇸",
    "Польша": "🇵🇱", "Латвия": "🇱🇻", "Литва": "🇱🇹",
    "Эстония": "🇪🇪", "Россия": "🇷🇺", "Украина": "🇺🇦",
    "Турция": "🇹🇷", "Индия": "🇮🇳", "Бразилия": "🇧🇷",
    "Австралия": "🇦🇺", "Австрия": "🇦🇹", "Бельгия": "🇧🇪",
    "Чехия": "🇨🇿", "Дания": "🇩🇰", "Ирландия": "🇮🇪",
    "Португалия": "🇵🇹", "Румыния": "🇷🇴", "Словакия": "🇸🇰",
    "Болгария": "🇧🇬", "Хорватия": "🇭🇷", "Греция": "🇬🇷",
    "Венгрия": "🇭🇺", "Исландия": "🇮🇸", "Люксембург": "🇱🇺",
    "Сербия": "🇷🇸", "Корея": "🇰🇷", "Тайвань": "🇹🇼",
    "Вьетнам": "🇻🇳", "Таиланд": "🇹🇭", "Малайзия": "🇲🇾",
    "Индонезия": "🇮🇩", "Филиппины": "🇵🇭", "Мексика": "🇲🇽",
    "Аргентина": "🇦🇷", "Чили": "🇨🇱", "ЮАР": "🇿🇦",
    "Израиль": "🇮🇱", "ОАЭ": "🇦🇪", "Казахстан": "🇰🇿",
    "Беларусь": "🇧🇾", "Молдова": "🇲🇩", "Грузия": "🇬🇪",
    "Кипр": "🇨🇾", "Мальта": "🇲🇹", "Словения": "🇸🇮",
}

REMOVE_WORDS = [
    'server', 'vpn', 'proxy', 'node', 'tunnel', 'relay',
    'free', 'public', 'private', 'premium', 'elite',
    'vip', 'pro', 'plus', 'max', 'ultra', 'turbo',
    'test', 'demo', 'temp', 'old', 'new',
    'vless', 'vmess', 'trojan', 'shadowsocks',
    'tcp', 'ws', 'grpc', 'http', 'https', 'h2',
    'tls', 'xtls', 'reality', 'vision', 'flow',
    'cdn', 'anycast', 'multi', 'mix',
]

# ============================================================
# КЭШ ПИНГА
# ============================================================
class PingCache:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()
    
    def get(self, host, port):
        key = f"{host}:{port}"
        with self.lock:
            if key in self.cache:
                ping, ts = self.cache[key]
                if (datetime.now() - ts).seconds < PING_CACHE_TTL:
                    return ping
        return None
    
    def set(self, host, port, ping):
        key = f"{host}:{port}"
        with self.lock:
            self.cache[key] = (ping, datetime.now())
    
    def measure_async(self, servers):
        def measure(host, port):
            try:
                start = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((host, int(port)))
                ping = (time.time() - start) * 1000
                sock.close()
                self.set(host, int(port), round(ping, 1))
            except:
                self.set(host, int(port), float('inf'))
        
        for host, port in servers:
            t = threading.Thread(target=measure, args=(host, port))
            t.daemon = True
            t.start()

ping_cache = PingCache()

# ============================================================
# ФУНКЦИИ
# ============================================================
def extract_server_info(line):
    m = re.search(r'@([\d.]+):(\d+)', line)
    return (m.group(1), m.group(2)) if m else (None, None)

def extract_original_name(line):
    m = re.search(r'#([^#\n]+)$', line)
    return m.group(1).strip() if m else ""

def translate_all(text):
    result = text
    for eng, rus in LOCATION_TRANSLATIONS.items():
        pattern = re.compile(r'\b' + re.escape(eng) + r'\b', re.IGNORECASE)
        result = pattern.sub(rus, result)
    return result

def get_flag(text):
    for country, flag in COUNTRY_FLAGS.items():
        if country in text:
            return flag
    return ""

def shorten_name(name):
    name = translate_all(name)
    parts = name.replace('-', ' ').replace('_', ' ').split()
    
    clean = []
    for p in parts:
        if p.lower() not in REMOVE_WORDS and not p.isdigit():
            clean.append(p)
    
    city, country = "", ""
    for p in clean:
        if p in COUNTRY_FLAGS:
            country = p
        else:
            for loc in LOCATION_TRANSLATIONS.values():
                if p == loc and loc not in COUNTRY_FLAGS:
                    city = p
                    break
    
    flag = get_flag(name)
    
    if city and country:
        result = f"{city} {flag}"
    elif country:
        result = f"{country} {flag}"
    elif city:
        result = city
    else:
        result = ' '.join(clean[:2]) if len(clean) >= 2 else clean[0] if clean else name[:20]
    
    if len(result) > 30:
        result = result[:27] + "..."
    
    return result.strip()

def create_enhanced_name(line, ping, is_premium=False):
    original_name = extract_original_name(line)
    short_name = shorten_name(original_name)
    
    line_lower = line.lower()
    if is_premium:
        icon = "💎"
    elif "anycast" in line_lower:
        icon = "🌍"
    elif "cdn" in line_lower:
        icon = "📡"
    elif "reality" in line_lower:
        icon = "🔒"
    else:
        icon = "🌐"
    
    if ping is None:
        ping_str = ""
    elif ping == float('inf'):
        ping_str = "❌"
    elif ping < 50:
        ping_str = f"⚡{ping:.0f}ms"
    elif ping < 100:
        ping_str = f"🚀{ping:.0f}ms"
    elif ping < 200:
        ping_str = f"🐌{ping:.0f}ms"
    else:
        ping_str = f"💀{ping:.0f}ms"
    
    if ping_str:
        display = f"{icon} {short_name} | {ping_str}"
    else:
        display = f"{icon} {short_name}"
    
    if len(display) > 40:
        display = display[:37] + "..."
    
    return display

def process_configs_fast(raw, is_premium=False):
    try:
        content = raw.decode('utf-8', errors='ignore')
        lines = content.split('\n')
        
        configs = []
        servers = []
        
        for line in lines:
            line = line.strip()
            if line.startswith(('vless://', 'trojan://', 'vmess://', 'ss://', 'hysteria://', 'tuic://')):
                configs.append(line)
                host, port = extract_server_info(line)
                if host and port:
                    servers.append((host, port))
        
        if servers:
            ping_cache.measure_async(servers)
        
        result = []
        # Статический заголовок
        result.append(f"#profile-title: {'CBN VPN Premium' if is_premium else 'CBN VPN'}")
        result.append("#profile-update-interval: 6")
        result.append("")
        
        seen = set()
        for line in configs:
            base = line[:line.rfind('#')] if '#' in line else line[:80]
            if base in seen:
                continue
            seen.add(base)
            
            host, port = extract_server_info(line)
            ping = ping_cache.get(host, int(port)) if host and port else None
            name = create_enhanced_name(line, ping, is_premium)
            
            if '#' in line:
                new_config = f"{line[:line.rfind('#')]}#{name}"
            else:
                new_config = f"{line}#{name}"
            
            result.append(new_config)
        
        return '\n'.join(result).encode('utf-8')
    except Exception as e:
        print(f"Error: {e}")
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
# КЭШ КОНФИГОВ
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
def bg_ping():
    while True:
        try:
            raw = get_raw(VPN_CONFIG_URL)
            content = raw.decode('utf-8', errors='ignore')
            servers = []
            for line in content.split('\n'):
                if line.startswith(('vless://', 'trojan://', 'vmess://')):
                    host, port = extract_server_info(line)
                    if host and port:
                        servers.append((host, port))
            if servers:
                ping_cache.measure_async(servers)
        except: pass
        time.sleep(300)

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
threading.Thread(target=bg_ping, daemon=True).start()

# ============================================================
# МАРШРУТЫ
# ============================================================

@app.route('/<int:user_id>')
def serve_vpn(user_id):
    """Обычная подписка CBN VPN"""
    if is_banned_user(user_id):
        return '', 200
    try:
        is_prem = is_premium_user(user_id)
        content = process_configs_fast(get_raw(VPN_CONFIG_URL), is_prem)
        title = "CBN VPN Premium" if is_prem else "CBN VPN"
        return Response(content, status=200, headers={
            "Content-Type": "text/plain; charset=utf-8",
            "Cache-Control": "public, max-age=60",
            "profile-title": title,
        })
    except:
        try:
            return Response(get_raw(VPN_CONFIG_URL), status=200, headers={
                "Content-Type": "text/plain; charset=utf-8",
                "profile-title": "CBN VPN",
            })
        except:
            return "Error", 502

@app.route('/<int:user_id>/obs')
def serve_obs(user_id):
    """Премиум/OBS подписка CBN VPN Premium"""
    if is_banned_user(user_id):
        return '', 200
    if not is_premium_user(user_id):
        return redirect(VPN_CONFIG_URL, code=302)
    try:
        content = process_configs_fast(get_raw(OBHOD_CONFIG_URL), True)
        return Response(content, status=200, headers={
            "Content-Type": "text/plain; charset=utf-8",
            "Cache-Control": "public, max-age=60",
            "profile-title": "CBN VPN Premium",
        })
    except:
        return redirect(OBHOD_CONFIG_URL, code=302)

@app.route('/health')
def health():
    return {"status": "ok"}, 200

@app.route('/')
def root():
    return "CBN VPN Server", 200

# ============================================================
# ADMIN API
# ============================================================
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
    print("CBN VPN Server v3.2")
    print(f"Time: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    app.run(host='0.0.0.0', port=5000, debug=False)
