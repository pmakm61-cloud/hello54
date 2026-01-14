# save_img.py
#!/usr/bin/env python3
"""
Скрипт для скачивания изображений товаров из БД hello54.ru
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import logging
from pathlib import Path
import urllib.parse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from src.config import DB_CONFIG
except ImportError:
    # Настройки по умолчанию если config.py не найден
    DB_CONFIG = {
        'host': 'localhost',
        'port': '5432',
        'database': 'hello54_parser',
        'user': 'postgres',
        'password': ''
    }

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/image_downloader.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ImageDownloader:
    """Загрузчик изображений товаров из базы данных"""
    
    def __init__(self, base_dir='prod_images', max_workers=3):
        self.base_dir = Path(base_dir)
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        
        # Создаем базовую директорию
        self.base_dir.mkdir(exist_ok=True, parents=True)
        
        # Подключаемся к базе данных
        self.connection = None
        self.connect_db()
        
        # Создаем необходимые колонки в БД
        self.create_image_columns()
    
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
    
    def create_image_columns(self):
        """
        Создание необходимых колонок для хранения информации об изображениях
        """
        try:
            with self.connection.cursor() as cursor:
                # Проверяем существующие колонки
                cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'products';
                """)
                existing_columns = {row[0] for row in cursor.fetchall()}
                
                # Колонки для добавления
                columns_to_add = [
                    ('img_local_path', 'TEXT'),
                    ('img_file_size', 'INTEGER'),
                    ('img_downloaded_at', 'TIMESTAMP')
                ]
                
                added_count = 0
                for column_name, column_type in columns_to_add:
                    if column_name not in existing_columns:
                        try:
                            cursor.execute(f"ALTER TABLE products ADD COLUMN {column_name} {column_type};")
                            logger.info(f"✅ Добавлена колонка: {column_name}")
                            added_count += 1
                        except Exception as e:
                            logger.error(f"❌ Ошибка добавления колонки {column_name}: {e}")
                
                if added_count > 0:
                    self.connection.commit()
                    logger.info(f"✅ Добавлено {added_count} новых колонок в таблицу products")
                else:
                    logger.info("✅ Все необходимые колонки уже существуют")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при создании колонок: {e}")
            self.connection.rollback()
    
    def get_products_with_images(self, limit=None, product_ids=None, only_not_downloaded=True):
        """
        Получение товаров с изображениями из БД
        
        Args:
            limit: Ограничение количества записей
            product_ids: Список конкретных ID для загрузки
            only_not_downloaded: Только товары без локальных копий
            
        Returns:
            list: Список словарей с данными товаров
        """
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                SELECT 
                    id,
                    prod_name,
                    prod_article,
                    prod_img_url,
                    url as product_url,
                    parsed_at,
                    img_local_path,
                    img_file_size,
                    img_downloaded_at
                FROM products 
                WHERE prod_img_url IS NOT NULL 
                  AND prod_img_url != ''
                  AND prod_type = 'product'
                """
                
                params = []
                
                # Только не загруженные
                if only_not_downloaded:
                    query += " AND img_local_path IS NULL"
                
                # Если указаны конкретные ID
                if product_ids:
                    placeholders = ','.join(['%s'] * len(product_ids))
                    query += f" AND id IN ({placeholders})"
                    params.extend(product_ids)
                
                # Сортировка по времени парсинга (сначала новые)
                query += " ORDER BY parsed_at DESC"
                
                # Ограничение количества
                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                
                cursor.execute(query, params)
                products = cursor.fetchall()
                
                status = "незагруженными" if only_not_downloaded else "всех"
                logger.info(f"📊 Найдено товаров с {status} изображениями: {len(products)}")
                return products
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения товаров: {e}")
            return []
    
    def parse_image_url(self, image_url):
        """
        Парсинг URL изображения для создания пути сохранения
        
        Args:
            image_url: Полный URL изображения
            
        Returns:
            tuple: (local_path, filename, extension)
        """
        try:
            # Парсим URL
            parsed = urllib.parse.urlparse(image_url)
            
            # Убираем домен и начальный слэш
            path = parsed.path.lstrip('/')
            
            # Разделяем путь и имя файла
            path_parts = path.split('/')
            filename = path_parts[-1]
            
            # Убираем имя файла из пути
            dir_parts = path_parts[:-1]
            
            # Создаем локальный путь
            local_path = self.base_dir / '/'.join(dir_parts)
            
            # Извлекаем расширение файла
            name, extension = os.path.splitext(filename)
            if not extension:
                extension = '.jpg'  # По умолчанию jpg
            
            return local_path, name, extension
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга URL {image_url}: {e}")
            return None, None, None
    
    def download_image(self, product):
        """
        Загрузка одного изображения
        
        Args:
            product: Словарь с данными товара
            
        Returns:
            dict: Результат загрузки
        """
        product_id = product['id']
        image_url = product['prod_img_url']
        prod_name = product['prod_name'] or f"product_{product_id}"
        article = product['prod_article'] or str(product_id)
        
        result = {
            'product_id': product_id,
            'image_url': image_url,
            'success': False,
            'error': None,
            'local_path': None,
            'file_size': 0
        }
        
        try:
            # Парсим URL для создания пути
            local_path, base_name, extension = self.parse_image_url(image_url)
            
            if not local_path:
                result['error'] = "Не удалось распарсить URL"
                return result
            
            # Создаем директории
            local_path.mkdir(exist_ok=True, parents=True)
            
            # Используем артикул или ID в имени файла для удобства
            safe_name = article.replace('/', '_').replace('\\', '_').replace(':', '_')
            
            # Проверяем, нет ли уже файла с таким именем
            counter = 1
            original_name = safe_name
            filename = f"{safe_name}{extension}"
            full_path = local_path / filename
            
            # Если файл существует, добавляем номер
            while full_path.exists():
                safe_name = f"{original_name}_{counter}"
                filename = f"{safe_name}{extension}"
                full_path = local_path / filename
                counter += 1
            
            # Загружаем изображение
            logger.debug(f"📥 Загрузка {product_id}: {image_url}")
            
            response = self.session.get(
                image_url, 
                timeout=30,
                stream=True
            )
            response.raise_for_status()
            
            # Определяем Content-Type для правильного расширения
            content_type = response.headers.get('Content-Type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                extension = '.jpg'
            elif 'png' in content_type:
                extension = '.png'
            elif 'webp' in content_type:
                extension = '.webp'
            elif 'gif' in content_type:
                extension = '.gif'
            
            # Сохраняем файл
            with open(full_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Получаем размер файла
            file_size = os.path.getsize(full_path)
            
            # Проверяем, что файл не пустой
            if file_size == 0:
                os.remove(full_path)
                result['error'] = "Файл пустой"
                return result
            
            # Записываем информацию о загруженном файле в БД
            self.save_download_info(product_id, str(full_path), file_size)
            
            result['success'] = True
            result['local_path'] = str(full_path)
            result['file_size'] = file_size
            
            logger.info(f"✅ {product_id}: {prod_name[:30]}... → {filename} ({file_size // 1024} KB)")
            
            # Небольшая пауза между запросами
            time.sleep(0.5)
            
        except requests.exceptions.RequestException as e:
            result['error'] = f"Ошибка сети: {e}"
            logger.error(f"❌ {product_id}: Ошибка загрузки: {e}")
        except Exception as e:
            result['error'] = f"Ошибка: {e}"
            logger.error(f"❌ {product_id}: Неожиданная ошибка: {e}")
        
        return result
    
    def save_download_info(self, product_id, local_path, file_size):
        """
        Сохранение информации о загруженном изображении в БД
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                UPDATE products 
                SET img_local_path = %s,
                    img_file_size = %s,
                    img_downloaded_at = NOW()
                WHERE id = %s;
                """, (local_path, file_size, product_id))
                
                self.connection.commit()
                logger.debug(f"💾 Информация о файле сохранена для товара {product_id}")
                
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить информацию о файле: {e}")
            self.connection.rollback()
    
    def download_images_batch(self, products, max_workers=None):
        """
        Пакетная загрузка изображений с многопоточностью
        
        Args:
            products: Список товаров
            max_workers: Количество потоков
            
        Returns:
            dict: Статистика загрузки
        """
        if max_workers is None:
            max_workers = self.max_workers
        
        stats = {
            'total': len(products),
            'success': 0,
            'failed': 0,
            'total_size': 0
        }
        
        logger.info(f"🚀 Начинаю загрузку {len(products)} изображений ({max_workers} потоков)")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Создаем задачи
            future_to_product = {
                executor.submit(self.download_image, product): product 
                for product in products
            }
            
            # Обрабатываем результаты
            for future in as_completed(future_to_product):
                product = future_to_product[future]
                try:
                    result = future.result()
                    
                    if result['success']:
                        stats['success'] += 1
                        stats['total_size'] += result['file_size']
                    else:
                        stats['failed'] += 1
                        logger.warning(f"⚠️ Не удалось загрузить {product['id']}: {result['error']}")
                        
                except Exception as e:
                    stats['failed'] += 1
                    logger.error(f"❌ Ошибка в потоке для {product['id']}: {e}")
        
        return stats
    
    def show_statistics(self):
        """
        Показать статистику загруженных изображений
        """
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Статистика по товарам
                cursor.execute("""
                SELECT 
                    COUNT(*) as total_products,
                    COUNT(prod_img_url) as with_images,
                    COUNT(img_local_path) as downloaded,
                    SUM(img_file_size) as total_size_bytes,
                    COUNT(CASE WHEN prod_img_url IS NOT NULL AND img_local_path IS NULL THEN 1 END) as pending_download
                FROM products 
                WHERE prod_type = 'product';
                """)
                
                stats = cursor.fetchone()
                
                print("\n📊 СТАТИСТИКА ИЗОБРАЖЕНИЙ")
                print("="*50)
                print(f"Всего товаров: {stats['total_products']}")
                print(f"С URL изображений: {stats['with_images']}")
                print(f"Уже загружено: {stats['downloaded']}")
                print(f"Ожидают загрузки: {stats['pending_download']}")
                
                if stats['total_size_bytes']:
                    size_mb = stats['total_size_bytes'] / (1024 * 1024)
                    print(f"Общий размер: {size_mb:.2f} MB")
                
                # Последние загруженные
                cursor.execute("""
                SELECT 
                    p.id,
                    p.prod_name,
                    p.img_local_path,
                    p.img_file_size,
                    p.img_downloaded_at
                FROM products p
                WHERE p.img_local_path IS NOT NULL
                ORDER BY p.img_downloaded_at DESC
                LIMIT 5;
                """)
                
                recent = cursor.fetchall()
                
                if recent:
                    print(f"\n🕒 ПОСЛЕДНИЕ 5 ЗАГРУЗОК:")
                    for row in recent:
                        name = row['prod_name'] or f"Товар {row['id']}"
                        path = row['img_local_path']
                        size = row['img_file_size'] or 0
                        time = row['img_downloaded_at']
                        
                        # Показываем относительный путь
                        if path and self.base_dir.as_posix() in path:
                            rel_path = path.replace(self.base_dir.as_posix(), '').lstrip('/')
                        else:
                            rel_path = path
                        
                        time_str = time.strftime('%H:%M:%S') if time else 'N/A'
                        
                        print(f"  • {name[:30]}...")
                        print(f"    📁 {rel_path[:40]}... ({size//1024} KB, {time_str})")
                
                print("="*50)
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
    
    def cleanup_empty_dirs(self, base_path=None):
        """
        Очистка пустых директорий
        """
        if base_path is None:
            base_path = self.base_dir
        
        removed = 0
        for root, dirs, files in os.walk(base_path, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        removed += 1
                        logger.debug(f"🗑️ Удалена пустая директория: {dir_path}")
                except OSError:
                    pass
        
        if removed:
            logger.info(f"✅ Удалено пустых директорий: {removed}")
    
    def close(self):
        """Закрытие соединений"""
        if self.connection:
            self.connection.close()
            logger.info("🔌 Соединение с PostgreSQL закрыто")
        
        self.session.close()

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(
        description='Загрузчик изображений товаров hello54.ru',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python save_img.py                      # Загрузить все незагруженные изображения
  python save_img.py --limit 10           # Загрузить 10 изображений
  python save_img.py --id 1 2 3           # Загрузить по ID товаров
  python save_img.py --all                # Загрузить все, даже уже загруженные
  python save_img.py --threads 5          # Использовать 5 потоков
  python save_img.py --stats              # Только статистика
  python save_img.py --cleanup            # Очистить пустые директории
        """
    )
    
    parser.add_argument('--limit', type=int, help='Ограничение количества изображений')
    parser.add_argument('--id', type=int, nargs='+', help='ID конкретных товаров для загрузки')
    parser.add_argument('--all', action='store_true', help='Загрузить все изображения, даже уже загруженные')
    parser.add_argument('--threads', type=int, default=3, help='Количество потоков (по умолчанию: 3)')
    parser.add_argument('--stats', action='store_true', help='Показать статистику')
    parser.add_argument('--cleanup', action='store_true', help='Очистить пустые директории')
    parser.add_argument('--output', type=str, default='prod_images', help='Базовая директория для сохранения')
    
    args = parser.parse_args()
    
    print("🖼️  ЗАГРУЗЧИК ИЗОБРАЖЕНИЙ ДЛЯ HELLO54.RU")
    print("="*60)
    
    downloader = ImageDownloader(base_dir=args.output, max_workers=args.threads)
    
    try:
        if args.stats:
            # Только статистика
            downloader.show_statistics()
            
        elif args.cleanup:
            # Очистка пустых директорий
            print("🧹 Очистка пустых директорий...")
            downloader.cleanup_empty_dirs()
            print("✅ Готово!")
            
        else:
            # Загрузка изображений
            # Получаем товары для загрузки
            products = downloader.get_products_with_images(
                limit=args.limit,
                product_ids=args.id,
                only_not_downloaded=not args.all
            )
            
            if not products:
                print("ℹ️ Нет товаров с изображениями для загрузки")
                
                # Предлагаем загрузить все
                if args.all:
                    print("Попробуйте без флага --all для загрузки только незагруженных")
                else:
                    print("Все изображения уже загружены или нет товаров с изображениями")
                return
            
            print(f"📥 Найдено {len(products)} товаров с изображениями")
            print(f"💾 Будет сохранено в: {args.output}/")
            print(f"🧵 Потоков: {args.threads}")
            
            if args.all:
                print("⚠️  Режим: загрузка ВСЕХ изображений (даже уже загруженных)")
            else:
                print("✅ Режим: загрузка только НЕЗАГРУЖЕННЫХ изображений")
            
            answer = input("\nПродолжить загрузку? (y/N): ")
            if answer.lower() != 'y':
                print("❌ Отменено")
                return
            
            # Загружаем изображения
            stats = downloader.download_images_batch(products)
            
            # Показываем результаты
            print(f"\n🎉 ЗАГРУЗКА ЗАВЕРШЕНА!")
            print("="*50)
            print(f"✅ Успешно: {stats['success']}")
            print(f"❌ Ошибок: {stats['failed']}")
            print(f"📊 Всего: {stats['total']}")
            
            if stats['total_size'] > 0:
                size_mb = stats['total_size'] / (1024 * 1024)
                print(f"💾 Общий размер: {size_mb:.2f} MB")
            
            # Показываем структуру
            print(f"\n📁 Структура каталогов создана в: {args.output}/")
            
            # Очищаем пустые директории
            downloader.cleanup_empty_dirs()
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Загрузка прервана пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        downloader.close()

if __name__ == "__main__":
    main()