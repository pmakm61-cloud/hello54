# src/product_processor.py
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
from bs4 import BeautifulSoup
import logging
import time
import re
import json
from datetime import datetime
from src.config import DB_CONFIG, PARSER_CONFIG
from src.selenium_parser import SeleniumParser
from src.universal_parser import parse_product_page as universal_parse_product

logger = logging.getLogger(__name__)

class ProductProcessor:
    """Обработчик товаров с поддержкой двух режимов: requests и selenium"""
    
    def __init__(self, use_selenium=False, selenium_headless=True):
        self.connection = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': PARSER_CONFIG['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        self.use_selenium = use_selenium
        self.selenium_headless = selenium_headless
        self.selenium_parser = None
        
        # Подключаемся к базе данных
        self.connect_db()
        self.ensure_columns_exist()
        self.classify_urls()
        
        # Инициализируем Selenium если нужен
        if self.use_selenium:
            self.init_selenium()
    
    def connect_db(self):
        """Подключение к PostgreSQL"""
        try:
            self.connection = psycopg2.connect(
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                database=DB_CONFIG['database'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password']
            )
            logger.info("✅ Подключение к PostgreSQL успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
            raise
    
    def init_selenium(self):
        """Инициализация Selenium парсера"""
        try:
            self.selenium_parser = SeleniumParser(
                headless=self.selenium_headless,
                driver_path=None
            )
            logger.info("✅ Selenium парсер инициализирован")
        except Exception as e:
            logger.error(f"❌ Не удалось инициализировать Selenium: {e}")
            logger.warning("⚠️ Будет использоваться режим requests")
            self.use_selenium = False
    
    def ensure_columns_exist(self):
        """Создание недостающих колонок в таблице products"""
        columns_to_add = [
            ('prod_type', 'VARCHAR(20) DEFAULT NULL'),
            ('prod_name', 'TEXT'),
            ('prod_price_new', 'DECIMAL(10,2)'),
            ('prod_price_old', 'DECIMAL(10,2)'),
            ('prod_article', 'VARCHAR(100)'),
            ('prod_img_url', 'TEXT'),
            ('prod_characteristics', 'JSONB'),  # НОВАЯ КОЛОНКА ДЛЯ ХАРАКТЕРИСТИК
            ('parsed_at', 'TIMESTAMP'),
            ('parse_status', 'VARCHAR(20) DEFAULT \'pending\''),
            ('parse_error', 'TEXT')
        ]
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'products';
                """)
                existing_columns = [row[0] for row in cursor.fetchall()]
                
                added_count = 0
                for column_name, column_type in columns_to_add:
                    if column_name not in existing_columns:
                        cursor.execute(f"ALTER TABLE products ADD COLUMN {column_name} {column_type};")
                        logger.info(f"✅ Добавлена колонка: {column_name}")
                        added_count += 1
                
                if added_count > 0:
                    self.connection.commit()
                    logger.info(f"✅ Добавлено {added_count} новых колонок")
                else:
                    logger.info("✅ Все необходимые колонки уже существуют")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при создании колонок: {e}")
            self.connection.rollback()
    
    def classify_urls(self):
        """Классификация URL: определяем товары (product) и не-товары (not_prod)"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as unclassified_count FROM products WHERE prod_type IS NULL;")
                unclassified = cursor.fetchone()[0]
                
                if unclassified > 0:
                    logger.info(f"🔍 Найдено {unclassified} URL без классификации")
                    
                    cursor.execute("""
                    UPDATE products 
                    SET prod_type = CASE 
                        WHEN url LIKE '%.html' THEN 'product'
                        ELSE 'not_prod'
                    END
                    WHERE prod_type IS NULL;
                    """)
                    
                    self.connection.commit()
                    
                    cursor.execute("""
                    SELECT prod_type, COUNT(*) as count
                    FROM products 
                    WHERE prod_type IS NOT NULL
                    GROUP BY prod_type;
                    """)
                    
                    classification_stats = cursor.fetchall()
                    logger.info("✅ Классификация URL завершена:")
                    for prod_type, count in classification_stats:
                        logger.info(f"   {prod_type}: {count} URL")
                    
                else:
                    logger.info("✅ Все URL уже классифицированы")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при классификации URL: {e}")
            self.connection.rollback()
    
    def get_unparsed_products(self, limit=10, only_products=True):
        """Получение непропарсенных товаров (только с prod_type='product')"""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                if only_products:
                    cursor.execute("""
                    SELECT id, url, article, parse_status, prod_type
                    FROM products 
                    WHERE prod_type = 'product'
                      AND (parse_status IS NULL 
                           OR parse_status = 'pending'
                           OR parse_status = 'failed')
                    ORDER BY 
                        CASE 
                            WHEN parse_status = 'failed' THEN 2
                            WHEN parse_status IS NULL THEN 1
                            ELSE 0 
                        END,
                        created_at ASC
                    LIMIT %s;
                    """, (limit,))
                else:
                    cursor.execute("""
                    SELECT id, url, article, parse_status, prod_type
                    FROM products 
                    WHERE (parse_status IS NULL 
                           OR parse_status = 'pending'
                           OR parse_status = 'failed')
                    ORDER BY prod_type DESC,
                        CASE 
                            WHEN parse_status = 'failed' THEN 2
                            WHEN parse_status IS NULL THEN 1
                            ELSE 0 
                        END,
                        created_at ASC
                    LIMIT %s;
                    """, (limit,))
                
                products = cursor.fetchall()
                
                if products:
                    types_count = {}
                    for product in products:
                        prod_type = product.get('prod_type', 'unknown')
                        types_count[prod_type] = types_count.get(prod_type, 0) + 1
                    
                    type_stats = ', '.join([f"{t}: {c}" for t, c in types_count.items()])
                    logger.info(f"📊 Для обработки выбрано: {len(products)} записей ({type_stats})")
                
                return products
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения товаров: {e}")
            return []
    
    def parse_product_page(self, url):
        """
        Парсинг страницы товара в двух режимах:
        1. Без Selenium (быстрый) - для простых страниц
        2. С Selenium (полный) - для динамических страниц
        """
        if self.use_selenium and self.selenium_parser:
            logger.debug(f"🔄 Использую Selenium для парсинга: {url}")
            return self._parse_with_selenium(url)
        else:
            logger.debug(f"⚡ Использую requests для парсинга: {url}")
            return self._parse_with_requests(url)
    
    def _parse_with_requests(self, url):
        """
        Парсинг товара через requests с использованием универсального парсера
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
        
            soup = BeautifulSoup(response.content, 'html.parser')
        
            # Используем универсальный парсер
            product_data = universal_parse_product(soup, url)
        
            return {
                'success': True,
                'data': product_data,
                'error': None,
                'source': 'requests_fast'
            }
        
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга {url}: {e}")
            return {'success': False, 'data': None, 'error': str(e), 'source': 'requests_fast'}
            
    def _find_article(self, soup, url):
        """
        Поиск артикула (теперь поддерживает строковые артикулы)
        """
        import re
    
        # СПОСОБ 1: Ищем в характеристиках
        for char_row in soup.find_all('div', class_='char-row'):
            char_name = char_row.find('span', class_='char-name')
            if char_name and 'Артикул' in char_name.get_text():
                char_value = char_row.find('span', class_='char-value')
                if char_value:
                    article = char_value.get_text(strip=True)
                    logger.debug(f"🔍 Артикул найден в char-row: {article}")
                    return article  # Может быть '005-black' или '206661'
    
        # СПОСОБ 2: Ищем текст "Артикул:" (поддерживаем строки)
        page_text = soup.get_text()
        # Ищем "Артикул:" и берем текст до конца строки или до следующего свойства
        article_match = re.search(r'Артикул[:\s]*([^\n\r]+)', page_text)
        if article_match:
            article = article_match.group(1).strip()
            # Очищаем от лишних пробелов
            article = re.sub(r'\s+', ' ', article)
            logger.debug(f"🔍 Артикул найден через текст: {article}")
            return article
    
        # СПОСОБ 3: Из URL (последняя часть перед .html)
        url_match = re.search(r'/([^/]+)\.html$', url)
        if url_match:
            # Берем все после последнего / и до .html
            article = url_match.group(1)
            # Извлекаем только часть после последнего -
            if '-' in article:
                article = article.split('-')[-1]
            logger.debug(f"🔍 Артикул взят из URL: {article}")
            return article
    
        logger.warning("⚠️ Артикул не найден ни одним способом")
        return None
    
    def _parse_with_selenium(self, url):
        """
        Парсинг с Selenium - полный режим для извлечения всех данных
        Ищет элементы, которые загружаются динамически
        """
        if not self.selenium_parser:
            return self._parse_with_requests(url)
        
        result = self.selenium_parser.extract_data_directly(url)
        
        # Если Selenium не нашел данные, пробуем requests как fallback
        if not result['success'] or not result['data'] or not result['data'].get('prod_name'):
            logger.warning(f"⚠️ Selenium не нашел данные, пробую requests: {url}")
            requests_result = self._parse_with_requests(url)
            requests_result['source'] = 'selenium_fallback'
            return requests_result
        
        return result
    
    def _clean_price(self, price_text):
        """Очистка текста цены"""
        if not price_text:
            return None
        
        cleaned = re.sub(r'[^\d,]', '', price_text.strip())
        cleaned = cleaned.replace(',', '.')
        
        try:
            return float(cleaned) if cleaned else None
        except:
            return None
    
    def update_product_data(self, product_id, parse_result, prod_type='product'):
        """Обновление данных товара в БД, включая характеристики"""
        try:
            with self.connection.cursor() as cursor:
                if parse_result['success'] and prod_type == 'product':
                    data = parse_result['data']
                    
                    # Преобразуем характеристики в JSON для PostgreSQL
                    characteristics_json = None
                    if 'characteristics' in data and data['characteristics']:
                        try:
                            characteristics_json = json.dumps(data['characteristics'], ensure_ascii=False)
                        except Exception as e:
                            logger.warning(f"⚠️ Не удалось преобразовать характеристики в JSON: {e}")
                            characteristics_json = None
                    
                    # Обновляем запись, включая характеристики
                    cursor.execute("""
                    UPDATE products 
                    SET prod_name = %s,
                        prod_price_new = %s,
                        prod_price_old = %s,
                        prod_article = %s,
                        prod_img_url = %s,
                        prod_characteristics = %s,  -- НОВОЕ ПОЛЕ
                        parsed_at = NOW(),
                        parse_status = 'success',
                        parse_error = NULL,
                        parse_attempts = COALESCE(parse_attempts, 0) + 1,
                        updated_at = NOW()  
                    WHERE id = %s;
                    """, (
                        data['prod_name'],
                        data['prod_price_new'],
                        data['prod_price_old'],
                        data['prod_article'],
                        data['prod_img_url'],
                        characteristics_json,  # ДОБАВЛЕНО
                        product_id
                    ))
                    
                    # Проверяем, сколько строк обновилось
                    rows_updated = cursor.rowcount
                    if rows_updated == 0:
                        logger.warning(f"⚠️ Запись с ID {product_id} не найдена для обновления")
                        return False
                    elif rows_updated == 1:
                        # Логируем количество характеристик
                        if characteristics_json:
                            char_count = len(data['characteristics'])
                            logger.debug(f"✅ Товар {product_id} успешно обновлен ({char_count} характеристик)")
                        else:
                            logger.debug(f"✅ Товар {product_id} успешно обновлен (без характеристик)")
                        self.connection.commit()
                        return True
                    else:
                        logger.error(f"❌ Обновлено {rows_updated} записей вместо 1 для ID {product_id}")
                        self.connection.rollback()
                        return False
                    
                elif prod_type != 'product':
                    # Для не-товаров
                    cursor.execute("""
                    UPDATE products 
                    SET parsed_at = NOW(),
                        parse_status = 'skipped',
                        parse_error = %s,
                        parse_attempts = COALESCE(parse_attempts, 0) + 1,
                        updated_at = NOW()
                    WHERE id = %s;
                    """, ('Не является товаром (prod_type != "product")', product_id))
                    
                    rows_updated = cursor.rowcount
                    if rows_updated > 0:
                        self.connection.commit()
                        logger.debug(f"⏭️  Пропущен не-товар {product_id}")
                        return True
                    else:
                        logger.warning(f"⚠️ Не удалось обновить не-товар {product_id}")
                        self.connection.rollback()
                        return False
                    
                else:
                    # Ошибка парсинга товара
                    cursor.execute("""
                    UPDATE products 
                    SET parsed_at = NOW(),
                        parse_status = 'failed',
                        parse_error = %s,
                        parse_attempts = COALESCE(parse_attempts, 0) + 1,
                        updated_at = NOW()
                    WHERE id = %s;
                    """, (parse_result['error'], product_id))
                    
                    rows_updated = cursor.rowcount
                    if rows_updated > 0:
                        self.connection.commit()
                        logger.warning(f"⚠️ Ошибка парсинга товара {product_id}: {parse_result['error']}")
                        return True
                    else:
                        logger.error(f"❌ Не удалось обновить статус ошибки для товара {product_id}")
                        self.connection.rollback()
                        return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка обновления товара {product_id}: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def get_product_characteristics(self, product_id):
        """Получить характеристики конкретного товара"""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                SELECT prod_name, prod_article, prod_characteristics
                FROM products 
                WHERE id = %s AND prod_characteristics IS NOT NULL;
                """, (product_id,))
                
                product = cursor.fetchone()
                
                if product:
                    return {
                        'success': True,
                        'product_name': product['prod_name'],
                        'article': product['prod_article'],
                        'characteristics': product['prod_characteristics']
                    }
                else:
                    return {'success': False, 'error': 'Товар не найден или нет характеристик'}
                    
        except Exception as e:
            logger.error(f"Ошибка получения характеристик: {e}")
            return {'success': False, 'error': str(e)}
            
    def process_products(self, limit=10, delay=1.0, only_products=True):
        """Обработка непропарсенных товаров"""
        products = self.get_unparsed_products(limit, only_products)
        
        if not products:
            logger.info("ℹ️ Нет товаров для обработки")
            return 0, 0, 0
        
        logger.info(f"🔍 Найдено {len(products)} записей для обработки")
        
        success_count = 0
        skipped_count = 0
        error_count = 0
        
        for i, product in enumerate(products, 1):
            prod_type = product.get('prod_type', 'unknown')
            
            if prod_type == 'product':
                logger.info(f"[{i}/{len(products)}] Обработка ТОВАРА {product['id']}: {product['url'][:60]}...")
                
                parse_result = self.parse_product_page(product['url'])
                
                if self.update_product_data(product['id'], parse_result, prod_type):
                    success_count += 1
                else:
                    error_count += 1
                    
            else:
                logger.info(f"[{i}/{len(products)}] ⏭️ Пропуск НЕ-ТОВАРА {product['id']} (тип: {prod_type})")
                
                if self.update_product_data(product['id'], {'success': False}, prod_type):
                    skipped_count += 1
                else:
                    error_count += 1
            
            if i < len(products):
                time.sleep(delay)
        
        logger.info(f"✅ Обработка завершена: {success_count} успешно, {skipped_count} пропущено, {error_count} с ошибками")
        return success_count, skipped_count, error_count
    
    def show_statistics(self):
        """Показать статистику обработки"""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                SELECT 
                    prod_type,
                    COUNT(*) as total_count,
                    SUM(CASE WHEN parse_status = 'success' THEN 1 ELSE 0 END) as parsed_success,
                    SUM(CASE WHEN parse_status = 'failed' THEN 1 ELSE 0 END) as parsed_failed,
                    SUM(CASE WHEN parse_status = 'skipped' THEN 1 ELSE 0 END) as parsed_skipped,
                    SUM(CASE WHEN parse_status IS NULL OR parse_status = 'pending' THEN 1 ELSE 0 END) as pending
                FROM products
                GROUP BY prod_type
                ORDER BY total_count DESC;
                """)
                
                type_stats = cursor.fetchall()
                
                cursor.execute("""
                SELECT 
                    COUNT(*) as total_products,
                    SUM(CASE WHEN prod_type = 'product' THEN 1 ELSE 0 END) as total_actual_products,
                    SUM(CASE WHEN parse_status = 'success' AND prod_type = 'product' THEN 1 ELSE 0 END) as products_parsed,
                    MAX(parsed_at) as last_parsed
                FROM products;
                """)
                
                summary = cursor.fetchone()
                
                cursor.execute("""
                SELECT 
                    c.name as category_name,
                    c.url as category_url,
                    COUNT(p.id) as total_products,
                    SUM(CASE WHEN p.prod_type = 'product' THEN 1 ELSE 0 END) as actual_products,
                    SUM(CASE WHEN p.parse_status = 'success' AND p.prod_type = 'product' THEN 1 ELSE 0 END) as parsed_success
                FROM categories c
                JOIN products p ON c.id = p.category_id
                GROUP BY c.id, c.name, c.url
                ORDER BY parsed_success DESC
                LIMIT 10;
                """)
                
                categories = cursor.fetchall()
                
                return {
                    'type_stats': type_stats,
                    'summary': summary,
                    'categories': categories
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return None
    
    def close(self):
        """Закрытие всех соединений"""
        if self.selenium_parser:
            self.selenium_parser.close()
        
        if self.connection:
            self.connection.close()
            logger.info("🔌 Соединение с PostgreSQL закрыто")