"""
CBN VPN Server - v4.5
- Anycast: 🌍 Anycast ⚡пинг (без локации)
- Остальные: иконка Город Флаг пинг
- Фикс VMess/OBS/всех протоколов
"""

import urllib.request
import threading
import time
import re
import socket
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
PING_TTL = 600

# ============================================================
# СЛОВАРЬ ГОРОД -> (рус, флаг)
# ============================================================
CITY_DATA = {
    "amsterdam": ("Амстердам", "🇳🇱"),
    "frankfurt": ("Франкфурт", "🇩🇪"),
    "helsinki": ("Хельсинки", "🇫🇮"),
    "stockholm": ("Стокгольм", "🇸🇪"),
    "oslo": ("Осло", "🇳🇴"),
    "zurich": ("Цюрих", "🇨🇭"),
    "paris": ("Париж", "🇫🇷"),
    "london": ("Лондон", "🇬🇧"),
    "moscow": ("Москва", "🇷🇺"),
    "st petersburg": ("СПб", "🇷🇺"),
    "saint petersburg": ("СПб", "🇷🇺"),
    "kiev": ("Киев", "🇺🇦"),
    "warsaw": ("Варшава", "🇵🇱"),
    "madrid": ("Мадрид", "🇪🇸"),
    "barcelona": ("Барселона", "🇪🇸"),
    "rome": ("Рим", "🇮🇹"),
    "milan": ("Милан", "🇮🇹"),
    "vienna": ("Вена", "🇦🇹"),
    "prague": ("Прага", "🇨🇿"),
    "berlin": ("Берлин", "🇩🇪"),
    "munich": ("Мюнхен", "🇩🇪"),
    "hamburg": ("Гамбург", "🇩🇪"),
    "lisbon": ("Лиссабон", "🇵🇹"),
    "dublin": ("Дублин", "🇮🇪"),
    "copenhagen": ("Копенгаген", "🇩🇰"),
    "brussels": ("Брюссель", "🇧🇪"),
    "budapest": ("Будапешт", "🇭🇺"),
    "bucharest": ("Бухарест", "🇷🇴"),
    "sofia": ("София", "🇧🇬"),
    "athens": ("Афины", "🇬🇷"),
    "riga": ("Рига", "🇱🇻"),
    "tallinn": ("Таллин", "🇪🇪"),
    "vilnius": ("Вильнюс", "🇱🇹"),
    "belgrade": ("Белград", "🇷🇸"),
    "bratislava": ("Братислава", "🇸🇰"),
    "ljubljana": ("Любляна", "🇸🇮"),
    "zagreb": ("Загреб", "🇭🇷"),
    "istanbul": ("Стамбул", "🇹🇷"),
    "dubai": ("Дубай", "🇦🇪"),
    "tokyo": ("Токио", "🇯🇵"),
    "osaka": ("Осака", "🇯🇵"),
    "seoul": ("Сеул", "🇰🇷"),
    "busan": ("Пусан", "🇰🇷"),
    "sydney": ("Сидней", "🇦🇺"),
    "melbourne": ("Мельбурн", "🇦🇺"),
    "toronto": ("Торонто", "🇨🇦"),
    "vancouver": ("Ванкувер", "🇨🇦"),
    "new york": ("Нью-Йорк", "🇺🇸"),
    "los angeles": ("Лос-Анджелес", "🇺🇸"),
    "chicago": ("Чикаго", "🇺🇸"),
    "dallas": ("Даллас", "🇺🇸"),
    "miami": ("Майами", "🇺🇸"),
    "seattle": ("Сиэтл", "🇺🇸"),
    "san francisco": ("Сан-Франциско", "🇺🇸"),
    "sao paulo": ("Сан-Паулу", "🇧🇷"),
    "rio de janeiro": ("Рио", "🇧🇷"),
    "mexico city": ("Мехико", "🇲🇽"),
    "buenos aires": ("Буэнос-Айрес", "🇦🇷"),
    "santiago": ("Сантьяго", "🇨🇱"),
    "lima": ("Лима", "🇵🇪"),
    "bogota": ("Богота", "🇨🇴"),
    "singapore": ("Сингапур", "🇸🇬"),
    "hong kong": ("Гонконг", "🇭🇰"),
    "taipei": ("Тайбэй", "🇹🇼"),
    "mumbai": ("Мумбаи", "🇮🇳"),
    "delhi": ("Дели", "🇮🇳"),
    "bangalore": ("Бангалор", "🇮🇳"),
    "tel aviv": ("Тель-Авив", "🇮🇱"),
    "jakarta": ("Джакарта", "🇮🇩"),
    "bangkok": ("Бангкок", "🇹🇭"),
    "kuala lumpur": ("Куала-Лумпур", "🇲🇾"),
    "manila": ("Манила", "🇵🇭"),
    "ho chi minh": ("Хошимин", "🇻🇳"),
    "hanoi": ("Ханой", "🇻🇳"),
}

# ============================================================
# ФУНКЦИИ
# ============================================================

def extract_host_port(line):
    """
    Извлекает хост и порт из ЛЮБОГО типа конфига
    VLESS/VMess/Trojan/SS
    """
    # VLESS/Trojan: @host:port
    m = re.search(r'@([\d.]+):(\d+)', line)
    if m:
        return m.group(1), m.group(2)
    
    # VMess в base64
    if line.startswith('vmess://'):
        try:
            b64 = line[8:]
            # Добавляем padding если нужно
            padding = 4 - len(b64) % 4
            if padding != 4:
                b64 += '=' * padding
            decoded = base64.b64decode(b64).decode('utf-8')
            data = json.loads(decoded)
            return data.get('add'), str(data.get('port', '443'))
        except:
            pass
    
    return None, None

def extract_name(line):
    """Извлекает название из конфига"""
    # Ищем #name в конце
    m = re.search(r'#([^#\n]+)$', line)
    if m:
        return m.group(1).strip()
    
    # Для VMess имя в JSON
    if line.startswith('vmess://'):
        try:
            b64 = line[8:]
            padding = 4 - len(b64) % 4
            if padding != 4:
                b64 += '=' * padding
            decoded = base64.b64decode(b64).decode('utf-8')
            data = json.loads(decoded)
            return data.get('ps', '')
        except:
            pass
    
    return ""

def is_anycast(line):
    """Проверяет, Anycast ли это"""
    low = line.lower()
    name = extract_name(line).lower()
    return 'anycast' in low or 'anycast' in name

def is_cdn(line):
    low = line.lower()
    name = extract_name(line).lower()
    return 'cdn' in low or 'cdn' in name

def is_reality(line):
    low = line.lower()
    return 'reality' in low

def find_city(name):
    """Ищет город в названии"""
    name_lower = name.lower().replace('-', ' ').replace('_', ' ')
    
    # Ищем точное совпадение города
    for city_key, (rus, flag) in CITY_DATA.items():
        if city_key in name_lower:
            return rus, flag
    
    # Если не нашли - берем первое слово как город
    words = [w for w in name_lower.split() if len(w) > 2]
    if words:
        return words[0].capitalize(), ""
    
    return name[:12], ""

def get_server_icon(line):
    if is_anycast(line):
        return "🌍"
    elif is_cdn(line):
        return "📡"
    elif is_reality(line):
        return "🔒"
    else:
        return "🌐"

def get_ping_emoji(ping):
    if ping is None:
        return ""
    if ping == float('inf'):
        return "❌"
    if ping < 50:
        return f"⚡{ping:.0f}ms"
    if ping < 100:
        return f"🚀{ping:.0f}ms"
    if ping < 200:
        return f"🐌{ping:.0f}ms"
    return f"💀{ping:.0f}ms"

def create_name(line, ping=None):
    """Создает красивое короткое название"""
    name = extract_name(line)
    icon = get_server_icon(line)
    ping_str = get_ping_emoji(ping)
    
    # Anycast - просто Anycast
    if is_anycast(line):
        if ping_str:
            return f"{icon} Anycast {ping_str}"
        return f"{icon} Anycast"
    
    # Остальные - Город Флаг
    city, flag = find_city(name)
    if flag:
        if ping_str:
            return f"{icon} {city} {flag} {ping_str}"
        return f"{icon} {city} {flag}"
    else:
        if ping_str:
            return f"{icon} {city} {ping_str}"
        return f"{icon} {city}"

def process_configs(raw, is_premium=False):
    """Обработка всех конфигов"""
    try:
        content = raw.decode('utf-8', errors='ignore')
        lines = content.split('\n')
        
        configs = []
        servers = []
        
        for line in lines:
            line = line.strip()
            if line.startswith(('vless://', 'vmess://', 'trojan://', 'ss://', 'hysteria://', 'tuic://')):
                configs.append(line)
                host, port = extract_host_port(line)
                if host and port:
                    servers.append((host, port))
        
        # Фоновый пинг
        if servers:
            ping_cache.measure_async(servers)
        
        result = []
        result.append("#profile-title: CBN VPN Premium" if is_premium else "#profile-title: CBN VPN")
        result.append("#profile-update-interval: 6")
        result.append("")
        
        seen = set()
        
        for line in configs:
            # Убираем query params для проверки дубликатов
            clean = re.sub(r'\?.*$', '', line)
            if '#' in clean:
                clean = clean[:clean.rfind('#')]
            
            if clean in seen:
                continue
            seen.add(clean)
            
            host, port = extract_host_port(line)
            ping = ping_cache.get(host, int(port)) if host and port else None
            
            name = create_name(line, ping)
            
            # Собираем конфиг с новым названием
            if '#' in line:
                base = line[:line.rfind('#')]
            else:
                base = line
            
            # Убираем старый fragment
            base = re.sub(r'#[^#]*$', '', base)
            
            result.append(f"{base}#{name}")
        
        return '\n'.join(result).encode('utf-8')
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return raw

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
                if (datetime.now() - ts).seconds < PING_TTL:
                    return ping
        return None
    
    def set(self, host, port, ping):
        with self.lock:
            self.cache[f"{host}:{port}"] = (ping, datetime.now())
    
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
            for url in [VPN_CONFIG_URL, OBHOD_CONFIG_URL]:
                raw = get_raw(url)
                content = raw.decode('utf-8', errors='ignore')
                servers = []
                for line in content.split('\n'):
                    if line.startswith(('vless://', 'vmess://', 'trojan://')):
                        host, port = extract_host_port(line)
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
    return "CBN VPN Server v4.5", 200

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
    print("=" * 50)
    print("CBN VPN Server v4.5")
    print("Anycast: 🌍 Anycast ⚡ping")
    print("Others: 📡 City 🇫🇮 🚀ping")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
