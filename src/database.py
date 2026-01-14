# src/database.py
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime
from src.config import DB_CONFIG

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер для работы с PostgreSQL"""
 
# src/database.py (добавьте этот метод в класс DatabaseManager)
    def reclassify_products(self):
        """Переклассификация всех URL в таблице products"""
        try:
            with self.connection.cursor() as cursor:
                # Узнаем текущее состояние
                cursor.execute("""
                SELECT 
                    SUM(CASE WHEN prod_type = 'product' THEN 1 ELSE 0 END) as current_products,
                    SUM(CASE WHEN prod_type = 'not_prod' THEN 1 ELSE 0 END) as current_not_prod,
                    SUM(CASE WHEN prod_type IS NULL THEN 1 ELSE 0 END) as current_null
                FROM products;
                """)
                
                current_state = cursor.fetchone()
                
                print(f"\n📊 Текущее состояние классификации:")
                print(f"   Товары (product): {current_state[0] or 0}")
                print(f"   Не товары (not_prod): {current_state[1] or 0}")
                print(f"   Без классификации: {current_state[2] or 0}")
                
                answer = input("\nПереклассифицировать все записи? (y/N): ")
                
                if answer.lower() != 'y':
                    print("❌ Операция отменена")
                    return
                
                # Переклассифицируем ВСЕ записи
                cursor.execute("""
                UPDATE products 
                SET prod_type = CASE 
                    WHEN url LIKE '%.html' THEN 'product'
                    ELSE 'not_prod'
                END;
                """)
                
                self.connection.commit()
                
                # Получаем новую статистику
                cursor.execute("""
                SELECT 
                    prod_type,
                    COUNT(*) as count
                FROM products 
                GROUP BY prod_type
                ORDER BY count DESC;
                """)
                
                new_stats = cursor.fetchall()
                
                print(f"\n✅ Классификация завершена:")
                for prod_type, count in new_stats:
                    print(f"   {prod_type}: {count} записей")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при переклассификации: {e}")
            self.connection.rollback()
 
    def __init__(self):
        self.connection = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Подключение к PostgreSQL"""
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            logger.info("✅ Подключение к PostgreSQL успешно")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
            return False
    
    def create_tables(self):
        """Создание таблиц если их нет"""
        if not self.connection:
            return
        
        try:
            with self.connection.cursor() as cursor:
                # Таблица категорий
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    url VARCHAR(500) UNIQUE NOT NULL,
                    name VARCHAR(255),
                    total_products INTEGER DEFAULT 0,
                    last_parsed TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                """)
                
                # Таблица продуктов (URL)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    url VARCHAR(500) UNIQUE NOT NULL,
                    article VARCHAR(50),
                    category_id INTEGER REFERENCES categories(id),
                    parsed BOOLEAN DEFAULT FALSE,
                    parse_attempts INTEGER DEFAULT 0,
                    last_parse_attempt TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                """)
                
                # Таблица логов парсинга
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS parse_logs (
                    id SERIAL PRIMARY KEY,
                    category_url VARCHAR(500),
                    action VARCHAR(50),
                    details TEXT,
                    products_found INTEGER DEFAULT 0,
                    products_added INTEGER DEFAULT 0,
                    duration_seconds INTEGER,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                """)
                
                self.connection.commit()
                logger.info("✅ Таблицы созданы/проверены")
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц: {e}")
            self.connection.rollback()
    
    def save_category(self, url, name=None):
        """Сохранение категории в БД"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                INSERT INTO categories (url, name, last_parsed, updated_at)
                VALUES (%s, %s, NOW(), NOW())
                ON CONFLICT (url) 
                DO UPDATE SET
                    name = COALESCE(EXCLUDED.name, categories.name),
                    last_parsed = NOW(),
                    updated_at = NOW()
                RETURNING id;
                """, (url, name))
                
                category_id = cursor.fetchone()[0]
                self.connection.commit()
                return category_id
                
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения категории {url}: {e}")
            self.connection.rollback()
            return None
    
    def save_product_urls(self, urls, category_id):
        """Сохранение списка URL товаров"""
        if not urls:
            return 0
        
        added_count = 0
        
        try:
            with self.connection.cursor() as cursor:
                for url in urls:
                    # Извлекаем артикул из URL если есть
                    import re
                    article = None
                    match = re.search(r'-(\d+)\.html$', url)
                    if match:
                        article = match.group(1)
                    
                    try:
                        cursor.execute("""
                        INSERT INTO products (url, article, category_id, created_at)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (url) DO NOTHING
                        RETURNING id;
                        """, (url, article, category_id))
                        
                        if cursor.fetchone():
                            added_count += 1
                            
                    except Exception as e:
                        continue
                
                # Обновляем счетчик товаров в категории
                cursor.execute("""
                UPDATE categories 
                SET total_products = (
                    SELECT COUNT(*) FROM products 
                    WHERE category_id = %s
                ),
                updated_at = NOW()
                WHERE id = %s;
                """, (category_id, category_id))
                
                self.connection.commit()
                return added_count
                
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения товаров: {e}")
            self.connection.rollback()
            return 0
    
    def log_parse_session(self, category_url, action, details, products_found, products_added, duration):
        """Логирование сессии парсинга"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                INSERT INTO parse_logs 
                (category_url, action, details, products_found, products_added, duration_seconds, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW());
                """, (category_url, action, details, products_found, products_added, duration))
                
                self.connection.commit()
        except Exception as e:
            logger.error(f"Ошибка логирования: {e}")
    
    def get_statistics(self):
        """Получение статистики"""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                SELECT 
                    COUNT(*) as total_products,
                    SUM(CASE WHEN parsed THEN 1 ELSE 0 END) as parsed_products,
                    COUNT(DISTINCT category_id) as total_categories,
                    MAX(created_at) as last_update
                FROM products;
                """)
                
                stats = cursor.fetchone()
                
                cursor.execute("""
                SELECT c.name, c.url, COUNT(p.id) as product_count
                FROM categories c
                LEFT JOIN products p ON c.id = p.category_id
                GROUP BY c.id, c.name, c.url
                ORDER BY product_count DESC;
                """)
                
                categories = cursor.fetchall()
                
                return {
                    'stats': stats,
                    'categories': categories
                }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return None
    
    def close(self):
        """Закрытие соединения"""
        if self.connection:
            self.connection.close()