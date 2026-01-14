# check_database.py
import sys
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.append(str(Path(__file__).parent))

from src.config import DB_CONFIG

def check_db_status():
    """Проверка состояния базы данных"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔍 ДИАГНОСТИКА БАЗЫ ДАННЫХ")
        print("="*60)
        
        # 1. Проверяем структуру таблицы products
        cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'products'
        ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print("\n📋 Структура таблицы products:")
        for col in columns:
            print(f"  {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        # 2. Проверяем ограничения
        cursor.execute("""
        SELECT tc.constraint_name, tc.constraint_type
        FROM information_schema.table_constraints tc
        WHERE tc.table_name = 'products';
        """)
        
        constraints = cursor.fetchall()
        print("\n🔒 Ограничения таблицы products:")
        for const in constraints:
            print(f"  {const['constraint_name']}: {const['constraint_type']}")
        
        # 3. Статистика по записям
        cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT url) as unique_urls,
            SUM(CASE WHEN parse_status = 'success' THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN parse_status = 'failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN parse_status IS NULL OR parse_status = 'pending' THEN 1 ELSE 0 END) as pending,
            MIN(created_at) as first_record,
            MAX(updated_at) as last_update
        FROM products;
        """)
        
        stats = cursor.fetchone()
        print(f"\n📊 Статистика записей:")
        print(f"  Всего записей: {stats['total']}")
        print(f"  Уникальных URL: {stats['unique_urls']}")
        print(f"  Успешно обработано: {stats['success']}")
        print(f"  С ошибками: {stats['failed']}")
        print(f"  Ожидают обработки: {stats['pending']}")
        print(f"  Первая запись: {stats['first_record']}")
        print(f"  Последнее обновление: {stats['last_update']}")
        
        # 4. Проверяем, есть ли записи с одинаковым URL
        cursor.execute("""
        SELECT url, COUNT(*) as count
        FROM products 
        GROUP BY url 
        HAVING COUNT(*) > 1
        ORDER BY count DESC
        LIMIT 5;
        """)
        
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"\n⚠️  Найдены дубликаты URL:")
            for dup in duplicates:
                print(f"  {dup['url']}: {dup['count']} записей")
        else:
            print(f"\n✅ Дубликатов URL не найдено")
        
        # 5. Примеры записей с разным временем created_at и updated_at
        cursor.execute("""
        SELECT id, url, prod_name, created_at, updated_at,
               EXTRACT(EPOCH FROM (updated_at - created_at)) as diff_seconds
        FROM products 
        WHERE updated_at != created_at
        ORDER BY diff_seconds DESC
        LIMIT 3;
        """)
        
        updated_records = cursor.fetchall()
        if updated_records:
            print(f"\n🔄 Записи с разными created_at и updated_at:")
            for rec in updated_records:
                print(f"  ID {rec['id']}: разница {rec['diff_seconds']:.0f} сек")
                print(f"    created: {rec['created_at']}")
                print(f"    updated: {rec['updated_at']}")
        else:
            print(f"\nℹ️  Нет записей с разными created_at и updated_at")
        
        # 6. Последние 5 обработанных записей
        cursor.execute("""
        SELECT id, url, prod_name, prod_price_new, parse_status, 
               created_at, updated_at, parsed_at
        FROM products 
        WHERE parse_status IS NOT NULL
        ORDER BY parsed_at DESC NULLS LAST
        LIMIT 5;
        """)
        
        recent = cursor.fetchall()
        print(f"\n🕒 Последние обработанные записи:")
        for rec in recent:
            print(f"  ID {rec['id']}: {rec['parse_status']}")
            print(f"    URL: {rec['url'][:50]}...")
            print(f"    Название: {rec['prod_name'][:30] if rec['prod_name'] else 'N/A'}...")
            print(f"    Цена: {rec['prod_price_new']}")
            print(f"    created: {rec['created_at'].strftime('%H:%M:%S')}")
            print(f"    updated: {rec['updated_at'].strftime('%H:%M:%S')}")
            print(f"    parsed: {rec['parsed_at'].strftime('%H:%M:%S') if rec['parsed_at'] else 'N/A'}")
            print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при проверке БД: {e}")

if __name__ == "__main__":
    check_db_status()