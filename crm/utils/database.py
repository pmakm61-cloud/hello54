# hello54_crm/utils/database.py
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from .config import DB_CONFIG

logger = logging.getLogger(__name__)

def get_db_connection():
    """Создание соединения с БД"""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise

def get_products(limit=50, offset=0, filters=None):
    """
    Получение списка товаров
    
    Args:
        limit: Количество записей
        offset: Смещение
        filters: Словарь фильтров {поле: значение}
    
    Returns:
        list: Список товаров
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            query = """
            SELECT 
                id,
                url,
                prod_name,
                prod_price_new,
                prod_price_old,
                prod_article,
                prod_img_url,
                img_local_path,
                parse_status,
                parsed_at,
                created_at,
                updated_at
            FROM products 
            WHERE prod_type = 'product'
            """
            
            params = []
            
            # Применяем фильтры
            if filters:
                conditions = []
                for key, value in filters.items():
                    if value is not None:
                        conditions.append(f"{key} = %s")
                        params.append(value)
                
                if conditions:
                    query += " AND " + " AND ".join(conditions)
            
            # Сортировка и лимиты
            query += " ORDER BY updated_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            products = cursor.fetchall()
            
            # Получаем общее количество
            count_query = "SELECT COUNT(*) as total FROM products WHERE prod_type = 'product'"
            cursor.execute(count_query)
            total = cursor.fetchone()['total']
            
            return {
                'products': products,
                'total': total,
                'limit': limit,
                'offset': offset
            }
            
    except Exception as e:
        logger.error(f"Ошибка получения товаров: {e}")
        return {'products': [], 'total': 0, 'limit': limit, 'offset': offset}
    finally:
        conn.close()

def get_product_by_id(product_id):
    """Получение товара по ID"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
            SELECT 
                *,
                CASE 
                    WHEN img_local_path IS NOT NULL THEN TRUE 
                    ELSE FALSE 
                END as has_local_image
            FROM products 
            WHERE id = %s
            """, (product_id,))
            
            product = cursor.fetchone()
            return product
            
    except Exception as e:
        logger.error(f"Ошибка получения товара {product_id}: {e}")
        return None
    finally:
        conn.close()

def get_statistics():
    """Получение статистики по БД"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
            SELECT 
                COUNT(*) as total_products,
                COUNT(CASE WHEN parse_status = 'success' THEN 1 END) as parsed_success,
                COUNT(CASE WHEN parse_status = 'failed' THEN 1 END) as parsed_failed,
                COUNT(CASE WHEN parse_status = 'pending' THEN 1 END) as pending,
                COUNT(CASE WHEN parse_status IS NULL THEN 1 END) as not_parsed,
                COUNT(CASE WHEN prod_price_new IS NOT NULL THEN 1 END) as has_price,
                COUNT(CASE WHEN prod_img_url IS NOT NULL THEN 1 END) as has_image_url,
                COUNT(CASE WHEN img_local_path IS NOT NULL THEN 1 END) as has_local_image,
                COUNT(CASE WHEN prod_article IS NOT NULL THEN 1 END) as has_article,
                MAX(parsed_at) as last_parsed
            FROM products 
            WHERE prod_type = 'product'
            """)
            
            stats = cursor.fetchone()
            return stats
            
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return None
    finally:
        conn.close()