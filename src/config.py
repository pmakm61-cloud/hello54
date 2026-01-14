# src/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Определяем путь к .env файлу
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'

# Загружаем переменные из .env
load_dotenv(ENV_PATH)

# Настройки PostgreSQL
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'hello54_project'),
    'user': os.getenv('DB_USER', 'hello54_parser'),
    'password': os.getenv('DB_PASSWORD', 'Hello54Parser2024!')
}

# НАСТРОЙКИ ПАРСЕРА С ОГРАНИЧЕНИЕМ 5 СТРАНИЦ
PARSER_CONFIG = {
    'delay_between_requests': float(os.getenv('REQUEST_DELAY', 1.0)),
    'max_pages_per_category': int(os.getenv('MAX_PAGES', 5)),  # 5 страниц по умолчанию
    'user_agent': os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
    'timeout': 15
}

# Настройки логирования
LOG_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'file': os.getenv('LOG_FILE', 'data/logs/parser.log')
}

# Проверяем, что пароль есть
if not DB_CONFIG['password']:
    print("⚠️  ВНИМАНИЕ: Пароль PostgreSQL не установлен в .env файле!")
    print(f"   Файл .env должен быть здесь: {ENV_PATH}")
    print("   Добавьте строку: DB_PASSWORD=ваш_пароль")
else:
    print(f"⚙️  Настройки парсера: максимум {PARSER_CONFIG['max_pages_per_category']} страниц на категорию")