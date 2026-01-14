# test_connection.py
import sys
from pathlib import Path

# Добавляем src в путь Python
sys.path.append(str(Path(__file__).parent))

from src.config import DB_CONFIG
import psycopg2

print("🔍 Проверка настроек из .env:")
print(f"  Хост: {DB_CONFIG['host']}")
print(f"  Порт: {DB_CONFIG['port']}")
print(f"  База: {DB_CONFIG['database']}")
print(f"  Пользователь: {DB_CONFIG['user']}")
print(f"  Пароль: {'*' * len(DB_CONFIG['password']) if DB_CONFIG['password'] else 'НЕ УСТАНОВЛЕН!'}")

if DB_CONFIG['password']:
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Подключение к PostgreSQL успешно!")
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
else:
    print("❌ Установите пароль в файле .env!")