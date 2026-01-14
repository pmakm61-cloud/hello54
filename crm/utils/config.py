# hello54_crm/utils/config.py
import os
from pathlib import Path

# Пути
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
LOGS_DIR = BASE_DIR / "logs"

# Настройки БД (адаптируем под ваш hello54 проект)
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'database': 'hello54_parser',  # ваша база
    'user': 'postgres',
    'password': 'ваш_пароль',      # из .env или config.py hello54
}

# Пути к скриптам парсера (относительно CRM)
PARSER_SCRIPTS = {
    'process_products': '../hello54/process_products.py',
    'save_img': '../hello54/save_img.py',
    'main': '../hello54/main.py',
}

# Настройки сервера
SERVER_CONFIG = {
    'host': '127.0.0.1',
    'port': 8000,
    'debug': True,
}

# Создаем необходимые директории
LOGS_DIR.mkdir(exist_ok=True)