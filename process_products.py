# process_products.py
#!/usr/bin/env python3
"""
Основной скрипт для обработки товаров с поддержкой двух режимов:
1. Быстрый режим (requests) - для обновления цен
2. Полный режим (selenium) - для первоначального сбора данных
"""

import argparse
import logging
import sys
from pathlib import Path
from tabulate import tabulate

# Добавляем src в путь
sys.path.append(str(Path(__file__).parent))

from src.product_processor import ProductProcessor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/product_processor.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def show_statistics(processor):
    """Показать статистику обработки"""
    stats_data = processor.show_statistics()
    
    if stats_data:
        type_stats = stats_data['type_stats']
        summary = stats_data['summary']
        categories = stats_data['categories']
        
        print("\n" + "="*60)
        print("📊 СТАТИСТИКА БАЗЫ ДАННЫХ")
        print("="*60)
        
        print(f"\n📈 Общая статистика:")
        print(f"   Всего записей в базе: {summary['total_products']}")
        print(f"   Из них реальных товаров: {summary['total_actual_products']}")
        print(f"   Товаров успешно обработано: {summary['products_parsed']}")
        print(f"   Последняя обработка: {summary['last_parsed']}")
        
        if summary['total_actual_products'] > 0:
            progress = (summary['products_parsed'] / summary['total_actual_products']) * 100
            print(f"   Прогресс обработки товаров: {progress:.1f}%")
        
        print(f"\n🏷️  Статистика по типам записей:")
        
        if type_stats:
            table_data = []
            for stat in type_stats:
                pending = stat['pending'] or 0
                total = stat['total_count']
                success = stat['parsed_success'] or 0
                
                table_data.append([
                    stat['prod_type'] or 'unknown',
                    total,
                    success,
                    stat['parsed_failed'] or 0,
                    stat['parsed_skipped'] or 0,
                    pending,
                    f"{(success / max(total, 1)) * 100:.1f}%" if stat['prod_type'] == 'product' else 'N/A'
                ])
            
            print(tabulate(table_data, 
                          headers=['Тип', 'Всего', 'Успешно', 'Ошибки', 'Пропущено', 'В ожидании', 'Прогресс'],
                          tablefmt='simple'))
        
        if categories:
            print(f"\n📂 Топ категорий по обработке товаров:")
            
            cat_table_data = []
            for cat in categories:
                actual_products = cat['actual_products'] or 0
                parsed_success = cat['parsed_success'] or 0
                
                if actual_products > 0:
                    progress = (parsed_success / actual_products) * 100
                else:
                    progress = 0
                
                cat_name = cat['category_name']
                if not cat_name:
                    cat_name = cat['category_url'].split('/')[-2].replace('-', ' ').title()
                
                cat_table_data.append([
                    cat_name[:30],
                    cat['total_products'],
                    actual_products,
                    parsed_success,
                    f"{progress:.1f}%"
                ])
            
            print(tabulate(cat_table_data, 
                          headers=['Категория', 'Всего URL', 'Товаров', 'Обработано', 'Прогресс'],
                          tablefmt='simple'))
        
        # Рекомендации
        print(f"\n💡 Рекомендации:")
        
        # Находим сколько товаров ждут обработки
        pending_products = 0
        for stat in type_stats:
            if stat['prod_type'] == 'product':
                pending_products = stat['pending'] or 0
                break
        
        if pending_products > 0:
            print(f"   Обработать товары: python process_products.py --process {min(pending_products, 50)}")
        
        # Проверяем есть ли неклассифицированные записи
        unknown_count = 0
        for stat in type_stats:
            if not stat['prod_type']:
                unknown_count = stat['total_count']
                break
        
        if unknown_count > 0:
            print(f"   ⚠️  Найдено {unknown_count} неклассифицированных записей")
            print(f"   Запустите скрипт для переклассификации")
        
        # Товары с ошибками
        failed_products = 0
        for stat in type_stats:
            if stat['prod_type'] == 'product':
                failed_products = stat['parsed_failed'] or 0
                break
        
        if failed_products > 0:
            print(f"   Повторная обработка с ошибками: python process_products.py --retry-failed")

def show_processed_products(processor, limit=10):
    """Показать обработанные товары"""
    try:
        with processor.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
            SELECT 
                id,
                prod_name,
                prod_price_new,
                prod_price_old,
                prod_article,
                prod_img_url,
                parse_status,
                parsed_at,
                prod_type
            FROM products 
            WHERE parse_status IN ('success', 'skipped')
            ORDER BY parsed_at DESC 
            LIMIT %s;
            """, (limit,))
            
            products = cursor.fetchall()
            
            print("\n" + "="*100)
            print(f"🔄 ПОСЛЕДНИЕ {len(products)} ОБРАБОТАННЫХ ЗАПИСЕЙ")
            print("="*100)
            
            if products:
                table_data = []
                for prod in products:
                    # Сокращаем длинные значения для таблицы
                    name = prod['prod_name']
                    if name and len(name) > 25:
                        name = name[:22] + '...'
                    
                    img_url = prod['prod_img_url']
                    if img_url and len(img_url) > 20:
                        img_url = '...' + img_url[-17:]
                    
                    status_icon = '✅' if prod['parse_status'] == 'success' else '⏭️'
                    
                    table_data.append([
                        prod['id'],
                        status_icon,
                        prod['prod_type'] or 'unknown',
                        name or 'N/A',
                        f"{prod['prod_price_new']}₽" if prod['prod_price_new'] else 'N/A',
                        f"{prod['prod_price_old']}₽" if prod['prod_price_old'] else 'N/A',
                        prod['prod_article'] or 'N/A',
                        img_url or 'N/A',
                        prod['parsed_at'].strftime('%H:%M:%S') if prod['parsed_at'] else 'N/A'
                    ])
                
                print(tabulate(table_data, 
                              headers=['ID', 'Статус', 'Тип', 'Название', 'Цена', 'Старая', 'Артикул', 'Картинка', 'Время'],
                              tablefmt='simple'))
                
                # Статистика по показанным записям
                success_count = sum(1 for p in products if p['parse_status'] == 'success')
                skipped_count = sum(1 for p in products if p['parse_status'] == 'skipped')
                
                print(f"\n📊 Среди показанных: {success_count} успешно, {skipped_count} пропущено")
                
            else:
                print("ℹ️ Нет обработанных записей")
                
    except Exception as e:
        logger.error(f"Ошибка при получении записей: {e}")

def retry_failed_products(processor):
    """Повторная обработка товаров с ошибками"""
    try:
        with processor.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
            SELECT COUNT(*) as failed_count
            FROM products 
            WHERE parse_status = 'failed' AND prod_type = 'product';
            """)
            
            failed_count = cursor.fetchone()['failed_count']
            
            if failed_count == 0:
                print("ℹ️ Нет товаров с ошибками для повторной обработки")
                return
            
            print(f"🔄 Найдено {failed_count} товаров с ошибками")
            answer = input("Повторить обработку? (y/N): ")
            
            if answer.lower() == 'y':
                # Сбрасываем статус ошибок
                cursor.execute("""
                UPDATE products 
                SET parse_status = 'pending',
                    parse_error = NULL,
                    parse_attempts = 0
                WHERE parse_status = 'failed' AND prod_type = 'product';
                """)
                
                processor.connection.commit()
                print(f"✅ Сброшен статус для {failed_count} товаров")
                print(f"💡 Теперь запустите: python process_products.py --process {min(failed_count, 20)}")
                
    except Exception as e:
        logger.error(f"Ошибка при повторной обработке: {e}")

def main():
    parser = argparse.ArgumentParser(
        description='Обработчик товаров hello54.ru с поддержкой двух режимов',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Быстрый режим (обновление цен, без Selenium)
  python process_products.py --process 20 --fast-mode
  
  # Полный режим (с Selenium, для новых товаров)
  python process_products.py --process 10 --selenium
  
  # Показать статистику
  python process_products.py --stats
  
  # Обработать товары с ошибками в быстром режиме
  python process_products.py --retry-failed --fast-mode
        """
    )
    
    parser.add_argument('--process', type=int, nargs='?', const=10, 
                       help='Обработать N записей (по умолчанию: 10)')
    
    parser.add_argument('--selenium', action='store_true',
                       help='Использовать Selenium (полный режим, для динамических страниц)')
    
    parser.add_argument('--fast-mode', action='store_true',
                       help='Быстрый режим без Selenium (только обновление цен)')
    
    parser.add_argument('--stats', action='store_true', 
                       help='Показать статистику')
    
    parser.add_argument('--show', type=int, nargs='?', const=10,
                       help='Показать N обработанных товаров')
    
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Задержка между запросами в секундах (по умолчанию: 1.0)')
    
    parser.add_argument('--retry-failed', action='store_true',
                       help='Повторно обработать товары с ошибками')
    
    parser.add_argument('--selenium-no-headless', action='store_true',
                       help='Запустить Selenium с видимым браузером (для отладки)')
    
    args = parser.parse_args()
    
    # Определяем режим работы
    use_selenium = False
    selenium_headless = True
    
    if args.selenium:
        use_selenium = True
        if args.selenium_no_headless:
            selenium_headless = False
            logger.info("🚀 Запуск в ПОЛНОМ режиме с Selenium (браузер виден)")
        else:
            logger.info("🚀 Запуск в ПОЛНОМ режиме с Selenium (headless)")
    elif args.fast_mode:
        logger.info("⚡ Запуск в БЫСТРОМ режиме (без Selenium)")
    else:
        # По умолчанию используем быстрый режим
        logger.info("⚡ Запуск в БЫСТРОМ режиме (без Selenium, по умолчанию)")
    
    # Инициализируем процессор
    processor = ProductProcessor(
        use_selenium=use_selenium,
        selenium_headless=selenium_headless
    )
    
    try:
        if args.stats:
            show_statistics(processor)
            
        elif args.show:
            show_processed_products(processor, args.show)
            
        elif args.process:
            logger.info(f"🔍 Начинаю обработку {args.process} записей")
            logger.info(f"⏱️  Задержка между запросами: {args.delay} сек")
            
            # Определяем, обрабатывать ли только товары
            # В быстром режиме - только товары, в полном - можно все
            only_products = not args.selenium
            
            success, skipped, errors = processor.process_products(
                limit=args.process, 
                delay=args.delay,
                only_products=only_products
            )
            
            print(f"\n" + "="*50)
            print("📊 РЕЗУЛЬТАТЫ ОБРАБОТКИ")
            print("="*50)
            print(f"✅ Успешно обработано: {success}")
            print(f"⏭️  Пропущено (не товары): {skipped}")
            print(f"❌ С ошибками: {errors}")
            print(f"🔧 Режим: {'Selenium' if args.selenium else 'Fast (requests)'}")
            
            if success > 0:
                show_statistics(processor)
                
        elif args.retry_failed:
            retry_failed_products(processor, use_selenium)
            
        else:
            parser.print_help()
            
    finally:
        processor.close()

if __name__ == "__main__":
    main()