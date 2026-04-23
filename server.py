"""
CBN VPN Server - v4.0
- Простые названия для INCY
- Город + флаг + пинг
- Без лишних символов
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

# ============================================================
# ПЕРЕВОДЫ ( city -> (rus_city, flag) )
# ============================================================
CITY_MAP = {
    "amsterdam": ("Амстердам", "🇳🇱"),
    "frankfurt": ("Франкфурт", "🇩🇪"),
    "helsinki": ("Хельсинки", "🇫🇮"),
    "stockholm": ("Стокгольм", "🇸🇪"),
    "oslo": ("Осло", "🇳🇴"),
    "zurich": ("Цюрих", "🇨🇭"),
    "paris": ("Париж", "🇫🇷"),
    "london": ("Лондон", "🇬🇧"),
    "moscow": ("Москва", "🇷🇺"),
    "kiev": ("Киев", "🇺🇦"),
    "warsaw": ("Варшава", "🇵🇱"),
    "madrid": ("Мадрид", "🇪🇸"),
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
    "istanbul": ("Стамбул", "🇹🇷"),
    "dubai": ("Дубай", "🇦🇪"),
    "tokyo": ("Токио", "🇯🇵"),
    "seoul": ("Сеул", "🇰🇷"),
    "sydney": ("Сидней", "🇦🇺"),
    "toronto": ("Торонто", "🇨🇦"),
    "new york": ("Нью-Йорк", "🇺🇸"),
    "los angeles": ("Лос-Анджелес", "🇺🇸"),
    "chicago": ("Чикаго", "🇺🇸"),
    "dallas": ("Даллас", "🇺🇸"),
    "miami": ("Майами", "🇺🇸"),
    "seattle": ("Сиэтл", "🇺🇸"),
    "sao paulo": ("Сан-Паулу", "🇧🇷"),
    "mexico city": ("Мехико", "🇲🇽"),
    "buenos aires": ("Буэнос-Айрес", "🇦🇷"),
    "santiago": ("Сантьяго", "🇨🇱"),
    "singapore": ("Сингапур", "🇸🇬"),
    "hong kong": ("Гонконг", "🇭🇰"),
    "taipei": ("Тайбэй", "🇹🇼"),
    "mumbai": ("Мумбаи", "🇮🇳"),
    "delhi": ("Дели", "🇮🇳"),
    "tel aviv": ("Тель-Авив", "🇮🇱"),
    "st petersburg": ("СПб", "🇷🇺"),
    "saint petersburg": ("СПб", "🇷🇺"),
}

# Стандартные названия для неизвестных городов по странам
COUNTRY_FLAGS = {
    "netherlands": "🇳🇱", "germany": "🇩🇪", "finland": "🇫🇮",
    "sweden": "🇸🇪", "norway": "🇳🇴", "switzerland": "🇨🇭",
    "france": "🇫🇷", "uk": "🇬🇧", "usa": "🇺🇸",
    "canada": "🇨🇦", "japan": "🇯🇵", "singapore": "🇸🇬",
    "hong kong": "🇭🇰", "italy": "🇮🇹", "spain": "🇪🇸",
    "poland": "🇵🇱", "latvia": "🇱🇻", "lithuania": "🇱🇹",
    "estonia": "🇪🇪", "russia": "🇷🇺", "ukraine": "🇺🇦",
    "turkey": "🇹🇷", "india": "🇮🇳", "brazil": "🇧🇷",
    "australia": "🇦🇺", "austria": "🇦🇹", "belgium": "🇧🇪",
    "czech": "🇨🇿", "denmark": "🇩🇰", "ireland": "🇮🇪",
    "portugal": "🇵🇹", "romania": "🇷🇴", "slovakia": "🇸🇰",
    "bulgaria": "🇧🇬", "croatia": "🇭🇷", "greece": "🇬🇷",
    "hungary": "🇭🇺", "iceland": "🇮🇸", "luxembourg": "🇱🇺",
    "serbia": "🇷🇸", "south korea": "🇰🇷", "taiwan": "🇹🇼",
    "vietnam": "🇻🇳", "thailand": "🇹🇭", "malaysia": "🇲🇾",
    "indonesia": "🇮🇩", "philippines": "🇵🇭", "mexico": "🇲🇽",
    "argentina": "🇦🇷", "chile": "🇨🇱", "south africa": "🇿🇦",
    "israel": "🇮🇱", "uae": "🇦🇪", "kazakhstan": "🇰🇿",
    "belarus": "🇧🇾", "moldova": "🇲🇩", "georgia": "🇬🇪",
    "cyprus": "🇨🇾", "malta": "🇲🇹", "slovenia": "🇸🇮",
}

def extract_server_info(line):
    m = re.search(r'@([\d.]+):(\d+)', line)
    return (m.group(1), m.group(2)) if m else (None, None)

def extract_original_name(line):
    """Извлекает оригинальное название из конфига"""
    m = re.search(r'#([^#\n]+)$', line)
    return m.group(1).strip() if m else ""

def find_city(name):
    """Ищет город в названии"""
    name_lower = name.lower().replace('-', ' ').replace('_', ' ')
    
    # Ищем точное совпадение
    for city, (rus, flag) in CITY_MAP.items():
        if city in name_lower:
            return rus, flag
    
    # Ищем страну
    for country, flag in COUNTRY_FLAGS.items():
        if country in name_lower:
            # Берем первое слово как город
            words = name_lower.split()
            for word in words:
                if len(word) > 3 and word not in ['anycast', 'cdn', 'reality', 'vless', 'vmess', 'trojan', 'tcp', 'ws', 'grpc']:
                    return word.capitalize(), flag
    
    return name[:15], ""

def get_server_type(line):
    """Определяет тип сервера"""
    low = line.lower()
    if "anycast" in low:
        return "🌍"
    elif "cdn" in low:
        return "📡"
    elif "reality" in low:
        return "🔒"
    return "🌐"

def create_simple_name(line, ping=None):
    """
    Создает ПРОСТОЕ название для INCY
    Формат: 🌍 Город Флаг | 23ms
    Максимум 30 символов
    """
    original = extract_original_name(line)
    city, flag = find_city(original)
    icon = get_server_type(line)
    
    # Базовое название: иконка + город + флаг
    name = f"{icon} {city} {flag}"
    
    # Добавляем пинг если есть
    if ping is not None and ping != float('inf') and ping < 999:
        if ping < 50:
            name += f" ⚡{ping:.0f}ms"
        elif ping < 100:
            name += f" 🚀{ping:.0f}ms"
        elif ping < 200:
            name += f" 🐌{ping:.0f}ms"
        else:
            name += f" 💀{ping:.0f}ms"
    
    # Обрезаем до 35 символов
    if len(name) > 35:
        name = name[:32] + "..."
    
    return name.strip()

def process_configs(raw, is_premium=False):
    """Обработка конфигов"""
    try:
        content = raw.decode('utf-8', errors='ignore')
        lines = content.split('\n')
        
        configs = []
        servers = []
        
        for line in lines:
            line = line.strip()
            if line.startswith(('vless://', 'trojan://', 'vmess://', 'ss://')):
                configs.append(line)
                host, port = extract_server_info(line)
                if host and port:
                    servers.append((host, port))
        
        # Запускаем пинг в фоне
        if servers:
            ping_cache.measure_async(servers)
        
        result = []
        result.append("#profile-title: CBN VPN Premium" if is_premium else "#profile-title: CBN VPN")
        result.append("#profile-update-interval: 6")
        result.append("")
        
        seen = set()
        
        for line in configs:
            # Убираем query-параметры для сравнения дубликатов
            base = re.sub(r'\?.*$', '', line[:line.rfind('#')] if '#' in line else line)
            if base in seen:
                continue
            seen.add(base)
            
            host, port = extract_server_info(line)
            ping = ping_cache.get(host, int(port)) if host and port else None
            
            # Простое короткое название
            name = create_simple_name(line, ping)
            
            # Собираем конфиг заново (убираем старые параметры из fragment)
            if '#' in line:
                # Берем всё до # и добавляем новое название
                clean = line[:line.rfind('#')]
                # Убираем старый fragment если есть
                clean = re.sub(r'#.*$', '', clean)
                new_config = f"{clean}#{name}"
            else:
                new_config = f"{line}#{name}"
            
            result.append(new_config)
        
        return '\n'.join(result).encode('utf-8')
    except Exception as e:
        print(f"Error: {e}")
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
                if (datetime.now() - ts).seconds < 600:
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

threading.Thread(target=keep_alive, daemon=True).start()
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
            "Cache-Control": "public, max-age=60",
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
    return "CBN VPN Server v4", 200

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
    print("CBN VPN Server v4.0")
    app.run(host='0.0.0.0', port=5000, debug=False)
