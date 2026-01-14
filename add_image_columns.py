# add_image_columns.py
import sys
sys.path.append('.')
from src.config import DB_CONFIG
import psycopg2

conn = psycopg2.connect(**DB_CONFIG)

with conn.cursor() as cursor:
    # Добавляем колонки для отслеживания загруженных файлов
    columns = [
        ('img_local_path', 'TEXT'),
        ('img_file_size', 'INTEGER'),
        ('img_downloaded_at', 'TIMESTAMP')
    ]
    
    for col_name, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE products ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
            print(f"✅ Добавлена колонка: {col_name}")
        except Exception as e:
            print(f"⚠️ Ошибка с колонкой {col_name}: {e}")
    
    conn.commit()

conn.close()
print("\n✅ Структура БД обновлена для работы с изображениями")