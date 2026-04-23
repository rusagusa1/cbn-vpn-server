"""
CBN VPN Server - STATELESS VERSION with Async Ping
- МГНОВЕННАЯ отдача конфигов (без ожидания пинга)
- Пинг измеряется в фоне и кэшируется
- Переименование подписок
- Совместимость со всеми клиентами (INCY, Happ, V2Box, Streisand)
"""

import urllib.request
import threading
import time
import json
import re
import socket
import concurrent.futures
from datetime import datetime
from flask import Flask, request, Response, redirect

app = Flask(__name__)

VPN_CONFIG_URL = "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt"
OBHOD_CONFIG_URL = "https://raw.githack.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt"
RENDER_URL = "https://cbn-vpn-server.onrender.com/"
CHANNEL_LINK = "https://t.me/CBN_VPN"
SUPPORT_LINK = "https://t.me/cherniy_bez_nomerov"
SECRET_KEY = "cbn_secret_2026"
CACHE_TTL = 900
PING_CACHE_TTL = 600  # 10 минут кэш пинга

# ============================================================
# СЛОВАРЬ ПЕРЕВОДОВ
# ============================================================
LOCATION_TRANSLATIONS = {
    "Netherlands": "Нидерланды", "Germany": "Германия", "Finland": "Финляндия",
    "Sweden": "Швеция", "Norway": "Норвегия", "Switzerland": "Швейцария",
    "France": "Франция", "UK": "Великобритания", "United Kingdom": "Великобритания",
    "USA": "США", "United States": "США", "Canada": "Канада",
    "Japan": "Япония", "Singapore": "Сингапур", "Hong Kong": "Гонконг",
    "Italy": "Италия", "Spain": "Испания", "Poland": "Польша",
    "Latvia": "Латвия", "Lithuania": "Литва", "Estonia": "Эстония",
    "Russia": "Россия", "Ukraine": "Украина", "Turkey": "Турция",
    "India": "Индия", "Brazil": "Бразилия", "Australia": "Австралия",
    "Austria": "Австрия", "Belgium": "Бельгия", "Czech": "Чехия",
    "Denmark": "Дания", "Ireland": "Ирландия", "Portugal": "Португалия",
    "Romania": "Румыния", "Slovakia": "Словакия", "Bulgaria": "Болгария",
    "Croatia": "Хорватия", "Greece": "Греция", "Hungary": "Венгрия",
    "Iceland": "Исландия", "Luxembourg": "Люксембург", "Serbia": "Сербия",
    "Amsterdam": "Амстердам", "Frankfurt": "Франкфурт", "Helsinki": "Хельсинки",
    "Stockholm": "Стокгольм", "Oslo": "Осло", "Zurich": "Цюрих",
    "Paris": "Париж", "London": "Лондон", "New York": "Нью-Йорк",
    "Los Angeles": "Лос-Анджелес", "Toronto": "Торонто", "Tokyo": "Токио",
    "Moscow": "Москва", "Kiev": "Киев", "Warsaw": "Варшава",
    "Madrid": "Мадрид", "Rome": "Рим", "Milan": "Милан",
    "Vienna": "Вена", "Prague": "Прага", "Berlin": "Берлин",
    "Munich": "Мюнхен", "Hamburg": "Гамбург", "Lisbon": "Лиссабон",
    "Dublin": "Дублин", "Copenhagen": "Копенгаген", "Brussels": "Брюссель",
    "Barcelona": "Барселона", "Budapest": "Будапешт", "Bucharest": "Бухарест",
    "Sofia": "София", "Athens": "Афины", "Riga": "Рига",
    "Tallinn": "Таллин", "Vilnius": "Вильнюс",
}

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
    "Сербия": "🇷🇸",
}

# ============================================================
# КЭШ ПИНГА (СОХРАНЯЕТСЯ МЕЖДУ ЗАПРОСАМИ)
# ============================================================
class PingCache:
    def __init__(self):
        self.cache = {}  # host:port -> (ping, timestamp)
        self.lock = threading.Lock()
        self.is_measuring = False
    
    def get_cached_ping(self, host: str, port: int) -> float:
        """Получает пинг из кэша"""
        key = f"{host}:{port}"
        with self.lock:
            if key in self.cache:
                ping, timestamp = self.cache[key]
                if (datetime.now() - timestamp).seconds < PING_CACHE_TTL:
                    return ping
        return None  # Нет в кэше
    
    def set_ping(self, host: str, port: int, ping: float):
        """Сохраняет пинг в кэш"""
        key = f"{host}:{port}"
        with self.lock:
            self.cache[key] = (ping, datetime.now())
    
    def measure_async(self, servers: list):
        """Асинхронное измерение пинга в отдельных потоках"""
        def measure_and_cache(host, port):
            try:
                start = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)  # Короткий таймаут
                sock.connect((host, int(port)))
                ping = (time.time() - start) * 1000
                sock.close()
                self.set_ping(host, int(port), round(ping, 1))
            except:
                self.set_ping(host, int(port), float('inf'))
        
        threads = []
        for host, port in servers:
            t = threading.Thread(target=measure_and_cache, args=(host, port))
            t.daemon = True
            t.start()
            threads.append(t)
        
        # Не ждем завершения - пусть работают в фоне
        return threads

# Глобальный кэш пинга
ping_cache = PingCache()

# ============================================================
# ФУНКЦИИ ОБРАБОТКИ
# ============================================================

def extract_server_info(config_line: str) -> tuple:
    """Извлекает IP и порт из конфига"""
    match = re.search(r'@([\d.]+):(\d+)', config_line)
    if match:
        return match.group(1), match.group(2)
    return None, None

def detect_server_type(config_line: str) -> str:
    config_lower = config_line.lower()
    if "anycast" in config_lower:
        return "Anycast"
    elif "cdn" in config_lower:
        return "CDN"
    elif "reality" in config_lower:
        return "REALITY"
    return None

def extract_original_name(config_line: str) -> str:
    match = re.search(r'#(.+)$', config_line)
    if match:
        return match.group(1).strip()
    return ""

def translate_location(text: str) -> str:
    result = text
    for eng, rus in LOCATION_TRANSLATIONS.items():
        if eng in result:
            result = result.replace(eng, rus)
    return result

def get_country_flag(location: str) -> str:
    for country, flag in COUNTRY_FLAGS.items():
        if country in location:
            return flag
    return ""

def get_speed_emoji(ping: float) -> str:
    """Возвращает эмодзи скорости"""
    if ping is None:
        return "📡"  # Пинг еще не измерен
    if ping == float('inf'):
        return "❌"
    elif ping < 50:
        return "⚡"
    elif ping < 100:
        return "🚀"
    elif ping < 200:
        return "🐌"
    else:
        return "💀"

def get_ping_text(ping: float) -> str:
    """Возвращает текст пинга"""
    if ping is None:
        return "измеряется..."
    if ping == float('inf'):
        return "нет ответа"
    return f"{ping:.0f}ms"

def create_enhanced_name(config_line: str, ping: float, is_premium: bool = False) -> str:
    """Создает улучшенное название (быстро, без задержек)"""
    server_type = detect_server_type(config_line)
    original_name = extract_original_name(config_line)
    translated = translate_location(original_name)
    country_flag = get_country_flag(translated)
    
    # Иконка
    if is_premium:
        icon = "💎"
    elif server_type == "Anycast":
        icon = "🌍"
    elif server_type == "CDN":
        icon = "📡"
    elif server_type == "REALITY":
        icon = "🔒"
    else:
        icon = "🌐"
    
    speed_emoji = get_speed_emoji(ping)
    ping_text = get_ping_text(ping)
    
    # Чистое название
    clean_name = translated.replace('-', ' ').replace('_', ' ').strip()
    clean_name = ' '.join(clean_name.split())
    
    # Формируем название
    if server_type:
        display_name = f"{icon} {server_type} | {clean_name} {country_flag} | {speed_emoji} {ping_text}"
    else:
        display_name = f"{icon} {clean_name} {country_flag} | {speed_emoji} {ping_text}"
    
    if len(display_name) > 80:
        display_name = display_name[:77] + "..."
    
    return display_name

def process_configs_fast(raw_content: bytes, user_id: int = None, is_premium: bool = False) -> bytes:
    """
    БЫСТРАЯ обработка конфигов без ожидания пинга
    Использует кэшированный пинг, если есть
    Запускает измерение пинга в фоне
    """
    try:
        content = raw_content.decode('utf-8', errors='ignore')
        lines = content.split('\n')
        
        config_lines = []
        servers_to_measure = []
        
        for line in lines:
            line = line.strip()
            if line.startswith(('vless://', 'trojan://', 'vmess://', 'ss://', 'hysteria://', 'tuic://')):
                config_lines.append(line)
                host, port = extract_server_info(line)
                if host and port:
                    servers_to_measure.append((host, port))
        
        # Запускаем измерение пинга В ФОНЕ (не ждем)
        if servers_to_measure:
            ping_cache.measure_async(servers_to_measure)
        
        # Формируем результат МГНОВЕННО
        result_lines = []
        current_time = datetime.now().strftime('%H:%M')
        premium_text = "Premium" if is_premium else "Standard"
        
        # Заголовок
        result_lines.append(f"#profile-title: CBN VPN {premium_text} | {current_time}")
        result_lines.append(f"#profile-update-interval: 6")
        result_lines.append("")
        
        seen_hashes = set()
        
        for line in config_lines:
            config_hash = line[:100]
            if config_hash in seen_hashes:
                continue
            seen_hashes.add(config_hash)
            
            # Получаем пинг из кэша (мгновенно)
            host, port = extract_server_info(line)
            if host and port:
                ping = ping_cache.get_cached_ping(host, int(port))
            else:
                ping = None
            
            # Создаем название
            enhanced_name = create_enhanced_name(line, ping, is_premium)
            
            # Заменяем название
            if '#' in line:
                base = line[:line.rfind('#')]
                new_config = f"{base}#{enhanced_name}"
            else:
                new_config = f"{line}#{enhanced_name}"
            
            result_lines.append(new_config)
        
        return '\n'.join(result_lines).encode('utf-8')
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return raw_content

# ============================================================
# СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================
_premium_users: dict[int, bool] = {}
_banned_users: dict[int, bool] = {}
_state_lock = threading.Lock()

def set_premium(user_id: int, status: bool):
    with _state_lock:
        _premium_users[user_id] = status

def set_banned(user_id: int, status: bool):
    with _state_lock:
        _banned_users[user_id] = status
        if status:
            _premium_users[user_id] = False

def is_premium_user(user_id: int) -> bool:
    with _state_lock:
        if _banned_users.get(user_id):
            return False
        return _premium_users.get(user_id, False)

def is_banned_user(user_id: int) -> bool:
    with _state_lock:
        return _banned_users.get(user_id, False)

# ============================================================
# КЭШ КОНФИГОВ
# ============================================================
_raw_cache = {}
_raw_cache_lock = threading.Lock()

def _download(url: str, timeout: int = 20, retries: int = 2) -> bytes:
    """Быстрая загрузка с коротким таймаутом"""
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(1)
    raise last_err

def get_raw_config(url: str) -> bytes:
    cache_key = url
    with _raw_cache_lock:
        if cache_key in _raw_cache:
            data, timestamp = _raw_cache[cache_key]
            if time.time() - timestamp < CACHE_TTL:
                return data
    
    data = _download(url)
    with _raw_cache_lock:
        _raw_cache[cache_key] = (data, time.time())
    
    return data

# ============================================================
# ФОНОВЫЕ ЗАДАЧИ
# ============================================================
def background_ping_measurement():
    """Фоновое измерение пинга всех серверов каждые 5 минут"""
    while True:
        try:
            print(f"[ping] Фоновое измерение пинга...")
            raw = get_raw_config(VPN_CONFIG_URL)
            content = raw.decode('utf-8', errors='ignore')
            
            servers = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith(('vless://', 'trojan://', 'vmess://')):
                    host, port = extract_server_info(line)
                    if host and port:
                        servers.append((host, port))
            
            if servers:
                # Запускаем измерение и ждем (это фоновый процесс)
                threads = ping_cache.measure_async(servers)
                for t in threads:
                    t.join(timeout=3)
                print(f"[ping] Измерено {len(servers)} серверов")
        except Exception as e:
            print(f"[ping] Ошибка: {e}")
        
        time.sleep(300)  # Каждые 5 минут

def keep_alive():
    while True:
        time.sleep(600)
        try:
            urllib.request.urlopen(RENDER_URL + "/health", timeout=10)
        except:
            pass

def refresh_raw_cache():
    while True:
        time.sleep(CACHE_TTL)
        try:
            _download(VPN_CONFIG_URL)
            _download(OBHOD_CONFIG_URL)
        except:
            pass

threading.Thread(target=keep_alive, daemon=True).start()
threading.Thread(target=refresh_raw_cache, daemon=True).start()
threading.Thread(target=background_ping_measurement, daemon=True).start()

# ============================================================
# МАРШРУТЫ
# ============================================================

@app.route('/<int:user_id>')
def serve_vpn(user_id):
    """Отдает VPN конфиг МГНОВЕННО"""
    if is_banned_user(user_id):
        return '', 200
    
    try:
        is_premium = is_premium_user(user_id)
        # Используем быструю обработку без ожидания пинга
        content = process_configs_fast(
            get_raw_config(VPN_CONFIG_URL), 
            user_id, 
            is_premium
        )
        
        return Response(
            content, 
            status=200, 
            headers={
                "Content-Type": "text/plain; charset=utf-8",
                "Cache-Control": "public, max-age=60",  # Кэширование на 1 минуту
            }
        )
    except Exception as e:
        print(f"Error: {e}")
        # В случае ошибки отдаем сырой конфиг
        try:
            raw = get_raw_config(VPN_CONFIG_URL)
            return Response(raw, status=200, headers={"Content-Type": "text/plain; charset=utf-8"})
        except:
            return "Server error", 502

@app.route('/<int:user_id>/obs')
def serve_obs(user_id):
    """Отдает OBS конфиг МГНОВЕННО"""
    if is_banned_user(user_id):
        return '', 200
    
    if not is_premium_user(user_id):
        return redirect(VPN_CONFIG_URL, code=302)
    
    try:
        content = process_configs_fast(
            get_raw_config(OBHOD_CONFIG_URL), 
            user_id, 
            True
        )
        
        return Response(
            content, 
            status=200, 
            headers={
                "Content-Type": "text/plain; charset=utf-8",
                "Cache-Control": "public, max-age=60",
            }
        )
    except Exception as e:
        print(f"Error: {e}")
        try:
            raw = get_raw_config(OBHOD_CONFIG_URL)
            return Response(raw, status=200, headers={"Content-Type": "text/plain; charset=utf-8"})
        except:
            return redirect(OBHOD_CONFIG_URL, code=302)

@app.route('/health')
def health():
    return {"status": "ok", "timestamp": time.time()}, 200

@app.route('/')
def root():
    return f"CBN VPN Server | {datetime.now().strftime('%H:%M')}", 200

# ============================================================
# ADMIN API
# ============================================================
@app.route('/set_premium/<int:user_id>/<int:status>', methods=['POST'])
def api_set_premium(user_id, status):
    if request.headers.get('X-Secret', '') != SECRET_KEY:
        return 'Forbidden', 403
    set_premium(user_id, bool(status))
    return 'OK', 200

@app.route('/unban_user/<int:user_id>', methods=['POST'])
def api_unban_user(user_id):
    if request.headers.get('X-Secret', '') != SECRET_KEY:
        return 'Forbidden', 403
    set_banned(user_id, False)
    return 'OK', 200

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def api_delete_user(user_id):
    if request.headers.get('X-Secret', '') != SECRET_KEY:
        return 'Forbidden', 403
    set_banned(user_id, True)
    return 'OK', 200

@app.route('/sync', methods=['POST'])
def api_sync():
    if request.headers.get('X-Secret', '') != SECRET_KEY:
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
    
    return 'OK', 200

@app.route('/flush_cache', methods=['POST'])
def flush_cache():
    if request.headers.get('X-Secret', '') != SECRET_KEY:
        return 'Forbidden', 403
    
    with _raw_cache_lock:
        _raw_cache.clear()
    
    return 'OK', 200

if __name__ == '__main__':
    print("=" * 50)
    print("CBN VPN Server v2.0")
    print(f"Time: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("Features: Fast response, Async ping, Cross-platform")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
