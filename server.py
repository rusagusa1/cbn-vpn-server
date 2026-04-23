"""
CBN VPN Server - STATELESS VERSION with Real Ping & Cross-Platform Renaming
- Реальное измерение пинга
- Правильное переименование для Happ Android/iOS и INCY
- Группировка по скорости
- Anycast остается на английском
"""

import urllib.request
import threading
import time
import json
import re
import socket
import concurrent.futures
from datetime import datetime
from collections import defaultdict
from flask import Flask, request, Response, redirect

app = Flask(__name__)

VPN_CONFIG_URL = "https://raw.githack.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt"
OBHOD_CONFIG_URL = "https://raw.githack.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt"
RENDER_URL = "https://cbn-vpn-server.onrender.com/"
CHANNEL_LINK = "https://t.me/CBN_VPN"
SUPPORT_LINK = "https://t.me/cherniy_bez_nomerov"
SECRET_KEY = "cbn_secret_2026"
CACHE_TTL = 900

# ============================================================
# СЛОВАРЬ ПЕРЕВОДОВ
# ============================================================
LOCATION_TRANSLATIONS = {
    # Страны
    "Netherlands": "Нидерланды",
    "Germany": "Германия",
    "Finland": "Финляндия",
    "Sweden": "Швеция",
    "Norway": "Норвегия",
    "Switzerland": "Швейцария",
    "France": "Франция",
    "UK": "Великобритания",
    "United Kingdom": "Великобритания",
    "USA": "США",
    "United States": "США",
    "Canada": "Канада",
    "Japan": "Япония",
    "Singapore": "Сингапур",
    "Hong Kong": "Гонконг",
    "Italy": "Италия",
    "Spain": "Испания",
    "Poland": "Польша",
    "Latvia": "Латвия",
    "Lithuania": "Литва",
    "Estonia": "Эстония",
    "Russia": "Россия",
    "Ukraine": "Украина",
    "Turkey": "Турция",
    "India": "Индия",
    "Brazil": "Бразилия",
    "Australia": "Австралия",
    "Austria": "Австрия",
    "Belgium": "Бельгия",
    "Czech": "Чехия",
    "Denmark": "Дания",
    "Ireland": "Ирландия",
    "Portugal": "Португалия",
    "Romania": "Румыния",
    "Slovakia": "Словакия",
    "Bulgaria": "Болгария",
    "Croatia": "Хорватия",
    "Greece": "Греция",
    "Hungary": "Венгрия",
    "Iceland": "Исландия",
    "Luxembourg": "Люксембург",
    "Serbia": "Сербия",
    
    # Города
    "Amsterdam": "Амстердам",
    "Frankfurt": "Франкфурт",
    "Helsinki": "Хельсинки",
    "Stockholm": "Стокгольм",
    "Oslo": "Осло",
    "Zurich": "Цюрих",
    "Paris": "Париж",
    "London": "Лондон",
    "New York": "Нью-Йорк",
    "Los Angeles": "Лос-Анджелес",
    "Toronto": "Торонто",
    "Tokyo": "Токио",
    "Moscow": "Москва",
    "Kiev": "Киев",
    "Warsaw": "Варшава",
    "Madrid": "Мадрид",
    "Rome": "Рим",
    "Milan": "Милан",
    "Vienna": "Вена",
    "Prague": "Прага",
    "Berlin": "Берлин",
    "Munich": "Мюнхен",
    "Hamburg": "Гамбург",
    "Lisbon": "Лиссабон",
    "Dublin": "Дублин",
    "Copenhagen": "Копенгаген",
    "Brussels": "Брюссель",
    "Barcelona": "Барселона",
    "Budapest": "Будапешт",
    "Bucharest": "Бухарест",
    "Sofia": "София",
    "Athens": "Афины",
    "Riga": "Рига",
    "Tallinn": "Таллин",
    "Vilnius": "Вильнюс",
}

# Флаги стран
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
# СЕРВИС ИЗМЕРЕНИЯ ПИНГА
# ============================================================
class PingService:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300
        self.lock = threading.Lock()
    
    def measure_tcp_ping(self, host: str, port: int = 443, timeout: float = 3.0) -> float:
        """Измеряет TCP пинг до сервера"""
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            ping = (time.time() - start) * 1000
            sock.close()
            return round(ping, 1)
        except:
            return float('inf')
    
    def get_ping(self, host: str, port: int = 443) -> float:
        """Получает пинг из кэша или измеряет"""
        cache_key = f"{host}:{port}"
        
        with self.lock:
            if cache_key in self.cache:
                ping, timestamp = self.cache[cache_key]
                if (datetime.now() - timestamp).seconds < self.cache_ttl:
                    return ping
        
        ping = self.measure_tcp_ping(host, port)
        
        with self.lock:
            self.cache[cache_key] = (ping, datetime.now())
        
        return ping
    
    def batch_measure(self, servers: list) -> dict:
        """Параллельное измерение пинга"""
        results = {}
        
        def measure_one(server_info):
            host, port, config_hash = server_info
            ping = self.get_ping(host, port)
            return config_hash, ping
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for s in servers:
                futures.append(executor.submit(measure_one, s))
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    config_hash, ping = future.result(timeout=5)
                    results[config_hash] = ping
                except:
                    pass
        
        return results

# Глобальный сервис пинга
ping_service = PingService()

# ============================================================
# ФУНКЦИИ ОБРАБОТКИ КОНФИГОВ
# ============================================================

def extract_server_info(config_line: str) -> tuple:
    """Извлекает IP и порт из конфига"""
    # Ищем IP:port после @
    match = re.search(r'@([\d.]+):(\d+)', config_line)
    if match:
        return match.group(1), int(match.group(2))
    return None, None

def detect_server_type(config_line: str) -> str:
    """Определяет тип сервера"""
    config_lower = config_line.lower()
    if "anycast" in config_lower:
        return "Anycast"
    elif "cdn" in config_lower:
        return "CDN"
    elif "reality" in config_lower:
        return "REALITY"
    elif "vless" in config_lower:
        return "VLESS"
    return None

def extract_original_name(config_line: str) -> str:
    """Извлекает оригинальное название из конфига"""
    # Ищем название после # в конце строки
    match = re.search(r'#(.+)$', config_line)
    if match:
        return match.group(1).strip()
    return ""

def translate_location(text: str) -> str:
    """Переводит локации на русский"""
    result = text
    for eng, rus in LOCATION_TRANSLATIONS.items():
        if eng in result:
            result = result.replace(eng, rus)
    return result

def get_country_flag(location: str) -> str:
    """Определяет флаг страны по названию"""
    for country, flag in COUNTRY_FLAGS.items():
        if country in location:
            return flag
    return ""

def create_enhanced_name(config_line: str, ping: float, is_premium: bool = False) -> str:
    """
    Создает улучшенное название для конфига
    Учитывает особенности Happ Android (нужен # в конце)
    """
    # Определяем тип сервера
    server_type = detect_server_type(config_line)
    
    # Извлекаем оригинальное название
    original_name = extract_original_name(config_line)
    
    # Переводим локации
    translated = translate_location(original_name)
    
    # Определяем флаг страны
    country_flag = get_country_flag(translated)
    
    # Определяем иконку и приоритет
    if server_type == "Anycast":
        icon = "🌍"
        type_name = "Anycast"  # Оставляем на английском
        priority = 1
    elif server_type == "CDN":
        icon = "📡"
        type_name = "CDN"
        priority = 2
    elif server_type == "REALITY":
        icon = "🔒"
        type_name = "Reality"
        priority = 3
    elif server_type == "VLESS":
        icon = "🔐"
        type_name = "VLESS"
        priority = 4
    else:
        icon = "🌐"
        type_name = ""
        priority = 5
    
    # Определяем скорость по пингу
    if ping == float('inf'):
        speed_emoji = "❌"
        speed_text = "Недоступен"
        speed_priority = 99
    elif ping < 50:
        speed_emoji = "⚡️"
        speed_text = f"{ping:.0f}ms"
        speed_priority = 1
    elif ping < 100:
        speed_emoji = "🚀"
        speed_text = f"{ping:.0f}ms"
        speed_priority = 2
    elif ping < 200:
        speed_emoji = "🐌"
        speed_text = f"{ping:.0f}ms"
        speed_priority = 3
    else:
        speed_emoji = "💀"
        speed_text = f"{ping:.0f}ms"
        speed_priority = 4
    
    # Для премиума меняем иконку
    if is_premium:
        icon = "💎"
    
    # Формируем чистое название (без дефисов, с пробелами)
    clean_name = translated.replace('-', ' ').replace('_', ' ')
    
    # Убираем технические части из названия
    for tech in ['Anycast', 'CDN', 'REALITY', 'VLESS', 'anycast', 'cdn', 'reality', 'vless']:
        clean_name = clean_name.replace(tech, '').strip()
    
    # Убираем лишние пробелы
    clean_name = ' '.join(clean_name.split())
    
    # Формируем финальное название
    if type_name:
        if country_flag:
            display_name = f"{icon} {type_name} | {clean_name} {country_flag} | {speed_emoji} {speed_text}"
        else:
            display_name = f"{icon} {type_name} | {clean_name} | {speed_emoji} {speed_text}"
    else:
        if country_flag:
            display_name = f"{icon} {clean_name} {country_flag} | {speed_emoji} {speed_text}"
        else:
            display_name = f"{icon} {clean_name} | {speed_emoji} {speed_text}"
    
    # Ограничиваем длину для совместимости
    if len(display_name) > 80:
        display_name = display_name[:77] + "..."
    
    # Заменяем название в конфиге
    # Ищем часть после # и заменяем её
    hash_pos = config_line.rfind('#')
    if hash_pos != -1:
        base_config = config_line[:hash_pos]
        return f"{base_config}#{display_name}"
    else:
        return f"{config_line}#{display_name}"

def process_configs(raw_content: bytes, user_id: int = None, is_premium: bool = False, measure_ping: bool = True) -> bytes:
    """
    Основная функция обработки всех конфигов
    """
    try:
        content = raw_content.decode('utf-8', errors='ignore')
        lines = content.split('\n')
        
        # Собираем серверы для измерения пинга
        servers_to_measure = []
        config_lines = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('vless://') or line.startswith('trojan://') or line.startswith('vmess://'):
                config_lines.append(line)
                if measure_ping:
                    host, port = extract_server_info(line)
                    if host and port:
                        # Используем хеш конфига как ключ
                        config_hash = line[:100]
                        servers_to_measure.append((host, port, config_hash))
        
        # Измеряем пинг
        ping_results = {}
        if measure_ping and servers_to_measure:
            print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Измеряем пинг для {len(servers_to_measure)} серверов...")
            start_time = time.time()
            ping_results = ping_service.batch_measure(servers_to_measure)
            elapsed = time.time() - start_time
            print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Пинг измерен за {elapsed:.1f}с для {len(ping_results)} серверов")
        
        # Группируем серверы по скорости
        categories = {
            "⚡️ Отличный пинг (0-50ms)": [],
            "🚀 Хороший пинг (50-100ms)": [],
            "🐌 Средний пинг (100-200ms)": [],
            "💀 Плохой пинг (200ms+)": [],
            "❌ Недоступны": [],
        }
        
        seen_hashes = set()
        processed_count = 0
        
        for line in config_lines:
            config_hash = line[:100]
            
            # Пропускаем дубликаты
            if config_hash in seen_hashes:
                continue
            seen_hashes.add(config_hash)
            
            # Получаем пинг
            ping = ping_results.get(config_hash, 999.0)
            
            # Создаем улучшенное название
            enhanced_line = create_enhanced_name(line, ping, is_premium)
            
            # Добавляем в категорию
            if ping == float('inf') or ping >= 999:
                categories["❌ Недоступны"].append(enhanced_line)
            elif ping < 50:
                categories["⚡️ Отличный пинг (0-50ms)"].append(enhanced_line)
            elif ping < 100:
                categories["🚀 Хороший пинг (50-100ms)"].append(enhanced_line)
            elif ping < 200:
                categories["🐌 Средний пинг (100-200ms)"].append(enhanced_line)
            else:
                categories["💀 Плохой пинг (200ms+)"].append(enhanced_line)
            
            processed_count += 1
        
        # Формируем результат
        result_lines = []
        current_time = datetime.now().strftime('%H:%M')
        current_date = datetime.now().strftime('%d.%m.%Y')
        
        # Заголовок профиля (важно для всех клиентов)
        premium_text = "💎 Premium" if is_premium else "🌐 Standard"
        result_lines.append(f"#profile-title: CBN VPN {premium_text} | {current_date} {current_time}")
        result_lines.append(f"#profile-update-interval: 6")
        result_lines.append(f"#profile-web-page-url: {CHANNEL_LINK}")
        result_lines.append(f"#profile-support-url: {SUPPORT_LINK}")
        result_lines.append("")
        
        # Добавляем серверы по категориям
        total_available = 0
        for category_name, servers in categories.items():
            if servers:
                # Сортируем серверы внутри категории по пингу
                result_lines.append(f"# ===== {category_name} =====")
                for server in servers:
                    result_lines.append(server)
                result_lines.append("")
                if "Недоступны" not in category_name:
                    total_available += len(servers)
        
        # Информационная секция
        result_lines.append(f"# 📊 Всего серверов: {processed_count}")
        result_lines.append(f"# ✅ Доступно: {total_available}")
        result_lines.append(f"# 🕐 Обновлено: {current_date} {current_time}")
        result_lines.append("")
        result_lines.append("# 💡 Советы:")
        result_lines.append("# • Серверы с 🌍 Anycast лучше всего для Telegram")
        result_lines.append("# • Выбирайте серверы с ⚡️ (наименьший пинг)")
        if is_premium:
            result_lines.append("# • 💎 Премиум серверы имеют приоритетный доступ")
        result_lines.append("# • Обновляйте подписку каждые 6 часов")
        result_lines.append("# • При проблемах смените сервер")
        
        return '\n'.join(result_lines).encode('utf-8')
        
    except Exception as e:
        print(f"❌ Ошибка обработки конфигов: {e}")
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

# ============================================================
# КЭШ КОНФИГОВ
# ============================================================
_cache = {}
_cache_lock = threading.Lock()

def _download(url: str, timeout: int = 30, retries: int = 3) -> bytes:
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; CBN-VPN/1.0)"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise last_err

def get_raw_config(url: str) -> bytes:
    """Получает сырой конфиг с кэшированием"""
    cache_key = url
    
    with _cache_lock:
        if cache_key in _cache:
            data, timestamp = _cache[cache_key]
            if time.time() - timestamp < CACHE_TTL:
                return data
    
    data = _download(url)
    
    with _cache_lock:
        _cache[cache_key] = (data, time.time())
    
    return data

def get_enhanced_config(url: str, user_id: int = None, is_premium: bool = False, measure_ping: bool = True) -> bytes:
    """Получает улучшенный конфиг"""
    try:
        raw = get_raw_config(url)
        enhanced = process_configs(raw, user_id, is_premium, measure_ping)
        return enhanced
    except Exception as e:
        print(f"Error: {e}")
        # Возвращаем сырой конфиг если обработка не удалась
        return get_raw_config(url)

# ============================================================
# ФОНОВЫЕ ЗАДАЧИ
# ============================================================
def refresh_cache_background():
    """Фоновое обновление кэша"""
    while True:
        time.sleep(CACHE_TTL)
        try:
            print(f"[cache] Обновление кэша...")
            _download(VPN_CONFIG_URL)
            _download(OBHOD_CONFIG_URL)
            print(f"[cache] Кэш обновлен")
        except Exception as e:
            print(f"[cache] Ошибка обновления: {e}")

def keep_alive():
    """Поддержание сервера активным"""
    while True:
        time.sleep(600)
        try:
            urllib.request.urlopen(RENDER_URL + "/health", timeout=10)
        except:
            pass

threading.Thread(target=keep_alive, daemon=True).start()
threading.Thread(target=refresh_cache_background, daemon=True).start()

# ============================================================
# МАРШРУТЫ
# ============================================================

@app.route('/<int:user_id>')
def serve_vpn(user_id):
    """Отдает VPN конфиг для пользователя"""
    if is_banned_user(user_id):
        return '', 200
    
    try:
        is_premium = is_premium_user(user_id)
        content = get_enhanced_config(VPN_CONFIG_URL, user_id, is_premium, measure_ping=True)
        
        current_time = datetime.now().strftime('%H:%M')
        if is_premium:
            title = f"CBN VPN 💎 Premium | {current_time}"
        else:
            title = f"CBN VPN 🌐 Standard | {current_time}"
        
        return Response(
            content, 
            status=200, 
            headers={
                "Content-Type": "text/plain; charset=utf-8",
                "profile-title": title,
                "profile-update-interval": "6",
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Content-Disposition": "inline",
                "profile-web-page-url": CHANNEL_LINK,
                "profile-support-url": SUPPORT_LINK,
            }
        )
    except Exception as e:
        print(f"Error serving VPN: {e}")
        return f"Server error: {e}", 502

@app.route('/<int:user_id>/obs')
def serve_obs(user_id):
    """Отдает OBS конфиг для премиум пользователей"""
    if is_banned_user(user_id):
        return '', 200
    
    if not is_premium_user(user_id):
        return redirect(VPN_CONFIG_URL, code=302)
    
    try:
        content = get_enhanced_config(OBHOD_CONFIG_URL, user_id, True, measure_ping=True)
        
        current_time = datetime.now().strftime('%H:%M')
        title = f"CBN VPN 💎 Premium OBS | {current_time}"
        
        return Response(
            content, 
            status=200, 
            headers={
                "Content-Type": "text/plain; charset=utf-8",
                "profile-title": title,
                "profile-update-interval": "6",
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Content-Disposition": "inline",
                "profile-web-page-url": CHANNEL_LINK,
                "profile-support-url": SUPPORT_LINK,
            }
        )
    except Exception as e:
        print(f"Error serving OBS: {e}")
        return redirect(OBHOD_CONFIG_URL, code=302)

@app.route('/health')
def health():
    """Health check"""
    with _state_lock:
        return {
            "status": "ok", 
            "timestamp": time.time(), 
            "premium": len(_premium_users), 
            "banned": len(_banned_users),
            "ping_cache": len(ping_service.cache)
        }, 200

@app.route('/')
def root():
    """Корневой эндпоинт"""
    with _state_lock:
        return f"CBN VPN Server Online | Premium: {len(_premium_users)} | Banned: {len(_banned_users)}", 200

# ============================================================
# ADMIN API
# ============================================================
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
    
    print(f"[sync] Premium: {len(premium_ids)}, Banned: {len(banned_ids)}")
    return 'OK', 200

@app.route('/flush_cache', methods=['POST'])
def flush_cache():
    secret = request.headers.get('X-Secret', '')
    if secret != SECRET_KEY:
        return 'Forbidden', 403
    
    with _cache_lock:
        _cache.clear()
    
    print("[cache] Кэш сброшен")
    return 'OK', 200

if __name__ == '__main__':
    print("=" * 50)
    print("CBN VPN Server Starting...")
    print(f"Time: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
