# main.py
#!/usr/bin/env python3
"""
Главный скрипт парсера hello54.ru
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from src.database import DatabaseManager
from src.crawler import Hello54Crawler

# Принудительно загружаем .env из корня проекта
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

# Проверяем наличие пароля
if not os.getenv('DB_PASSWORD'):
    print("❌ ОШИБКА: .env файл не найден или DB_PASSWORD не установлен!")
    print(f"   Создайте файл: {BASE_DIR / '.env'}")
    print("   Содержимое:")
    print("   DB_HOST=localhost")
    print("   DB_PORT=5432")
    print("   DB_NAME=hello54_parser")
    print("   DB_USER=postgres")
    print("   DB_PASSWORD=ваш_пароль")
    exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/parser.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Парсер сайта hello54.ru')
    parser.add_argument('--category', type=str, help='URL категории для парсинга')
    parser.add_argument('--categories-file', type=str, help='Файл со списком категорий')
    parser.add_argument('--stats', action='store_true', help='Показать статистику')
    parser.add_argument('--export', type=str, help='Экспорт URL в файл (csv или txt)')
    parser.add_argument('--max-pages', type=int, default=5,
                       help='Максимальное количество страниц для парсинга (по умолчанию: 5)')
    
    args = parser.parse_args()
    
    # Инициализация базы данных
    db = DatabaseManager()
    
    if args.stats:
        # Показать статистику
        stats = db.get_statistics()
        if stats:
            print("\n" + "="*60)
            print("СТАТИСТИКА ПАРСЕРА")
            print("="*60)
            print(f"📊 Всего товаров: {stats['stats']['total_products']}")
            print(f"✅ Обработано: {stats['stats']['parsed_products']}")
            print(f"📁 Категорий: {stats['stats']['total_categories']}")
            print(f"🕒 Последнее обновление: {stats['stats']['last_update']}")
            
            print(f"\n📂 Категории:")
            for cat in stats['categories']:
                print(f"  • {cat['name'] or cat['url']}: {cat['product_count']} товаров")
        
        db.close()
        return
    
    if args.category:
        # Парсинг одной категории
        crawler = Hello54Crawler(db)
        urls = crawler.parse_category(args.category, max_pages_override=args.max_pages)
        
        print(f"\n" + "="*50)
        print("📊 РЕЗУЛЬТАТЫ ПАРСИНГА")
        print("="*50)
        print(f"   Категория: {args.category}")
        print(f"   Макс. страниц: {args.max_pages}")
        print(f"   Найдено товаров: {len(urls)}")
        
        if urls:
            print(f"\n🔗 Примеры найденных URL:")
            for i, url in enumerate(urls[:3], 1):
                print(f"   {i}. {url}")
            if len(urls) > 3:
                print(f"   ... и ещё {len(urls) - 3} URL")
        
        if args.export:
            export_urls(urls, args.export)
    
    elif args.categories_file:
        # Парсинг из файла с категориями
        try:
            with open(args.categories_file, 'r', encoding='utf-8') as f:
                categories = [line.strip() for line in f if line.strip()]
            
            print(f"📁 Найдено {len(categories)} категорий для парсинга")
            
            crawler = Hello54Crawler(db)
            
            for i, category_url in enumerate(categories, 1):
                print(f"\n[{i}/{len(categories)}] Парсинг: {category_url}")
                urls = crawler.parse_category(category_url, max_pages_override=args.max_pages)
                print(f"   Результат: {len(urls)} товаров")
        
        except Exception as e:
            logger.error(f"Ошибка чтения файла категорий: {e}")
    
    else:
        parser.print_help()
    
    db.close()

def export_urls(urls, filename):
    """Экспорт URL в файл"""
    try:
        if filename.endswith('.csv'):
            import pandas as pd
            df = pd.DataFrame({'url': urls})
            df.to_csv(filename, index=False, encoding='utf-8-sig')
        else:
            with open(filename, 'w', encoding='utf-8') as f:
                for url in urls:
                    f.write(url + '\n')
        
        print(f"💾 URL экспортированы в {filename}")
    except Exception as e:
        logger.error(f"Ошибка экспорта: {e}")

if __name__ == "__main__":
    main()