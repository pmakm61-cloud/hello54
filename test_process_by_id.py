#!/usr/bin/env python3
"""
test_process_by_id.py
Тестовый скрипт для обработки конкретного товара по ID из БД
Запускает process_products.py с фильтрацией по ID
"""

import sys
import os
import subprocess
import logging
import argparse

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def safe_subprocess_run(cmd):
    """
    Безопасный запуск subprocess с обработкой ошибок кодировки
    """
    try:
        logger.debug(f"Запуск команды: {' '.join(cmd)}")
        
        # Запускаем с text=False чтобы получить байты
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=False,  # ВАЖНО: получаем байты, не строку
            shell=False,
            timeout=300  # Таймаут 5 минут
        )
        
        # Декодируем вывод с обработкой ошибок
        stdout = ""
        stderr = ""
        
        if result.stdout:
            try:
                stdout = result.stdout.decode('utf-8', errors='ignore')
            except Exception as decode_error:
                logger.warning(f"Ошибка декодирования stdout: {decode_error}")
                # Пробуем альтернативные кодировки
                for encoding in ['cp1251', 'cp866', 'iso-8859-1']:
                    try:
                        stdout = result.stdout.decode(encoding, errors='ignore')
                        logger.debug(f"Использована кодировка {encoding} для stdout")
                        break
                    except:
                        continue
        
        if result.stderr:
            try:
                stderr = result.stderr.decode('utf-8', errors='ignore')
            except Exception as decode_error:
                logger.warning(f"Ошибка декодирования stderr: {decode_error}")
                # Пробуем альтернативные кодировки
                for encoding in ['cp1251', 'cp866', 'iso-8859-1']:
                    try:
                        stderr = result.stderr.decode(encoding, errors='ignore')
                        logger.debug(f"Использована кодировка {encoding} для stderr")
                        break
                    except:
                        continue
        
        # Заменяем объект result с декодированными строками
        result.stdout = stdout
        result.stderr = stderr
        
        return result
        
    except subprocess.TimeoutExpired:
        logger.error(f"Таймаут выполнения команды: {' '.join(cmd)}")
        raise
    except Exception as e:
        logger.error(f"Ошибка в safe_subprocess_run: {e}")
        raise

def get_product_info(product_id):
    """Получить информацию о товаре по ID"""
    try:
        from src.database import DatabaseManager
        db = DatabaseManager()
        with db.connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id, 
                    url, 
                    prod_type,
                    parse_status,
                    prod_name,
                    prod_article
                FROM products 
                WHERE id = %s;
            """, (product_id,))
            
            product = cursor.fetchone()
            return product
            
    except ImportError:
        logger.error("Не удалось импортировать DatabaseManager")
        return None
    except Exception as e:
        logger.error(f"Ошибка получения товара {product_id}: {e}")
        return None
    finally:
        if 'db' in locals():
            db.close()

def prepare_product_for_processing(product_id):
    """Подготовить товар для обработки - установить статус pending"""
    try:
        from src.database import DatabaseManager
        db = DatabaseManager()
        with db.connection.cursor() as cursor:
            # Получаем текущий статус
            cursor.execute("SELECT parse_status FROM products WHERE id = %s", (product_id,))
            current_status = cursor.fetchone()
            
            if current_status:
                original_status = current_status[0]
            else:
                original_status = None
            
            # Устанавливаем статус pending для обработки
            cursor.execute("""
                UPDATE products 
                SET parse_status = 'pending',
                    parse_error = NULL
                WHERE id = %s;
            """, (product_id,))
            
            db.connection.commit()
            logger.info(f"✅ Товар {product_id} подготовлен для обработки")
            return original_status
            
    except Exception as e:
        logger.error(f"❌ Ошибка подготовки товара: {e}")
        if 'db' in locals():
            db.connection.rollback()
        return None
    finally:
        if 'db' in locals():
            db.close()

def restore_product_status(product_id, original_status):
    """Восстановить оригинальный статус товара"""
    if original_status is None:
        return
    
    try:
        from src.database import DatabaseManager
        db = DatabaseManager()
        with db.connection.cursor() as cursor:
            cursor.execute("""
                UPDATE products 
                SET parse_status = %s
                WHERE id = %s;
            """, (original_status, product_id))
            
            db.connection.commit()
            logger.info(f"✅ Восстановлен статус товара {product_id}: {original_status}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка восстановления статуса: {e}")
    finally:
        if 'db' in locals():
            db.close()

def process_specific_product(product_id, use_selenium=False, delay=1.0):
    """
    Обработать конкретный товар по ID
    Использует существующий process_products.py
    """
    
    print(f"\n🔧 ОБРАБОТКА ТОВАРА ID: {product_id}")
    print("="*60)
    
    # 1. Получаем информацию о товаре
    product = get_product_info(product_id)
    
    if not product:
        logger.error(f"❌ Товар с ID {product_id} не найден в базе данных")
        return False
    
    prod_id, url, prod_type, status, name, article = product
    
    logger.info(f"📋 Информация о товаре:")
    logger.info(f"   ID: {prod_id}")
    logger.info(f"   URL: {url}")
    logger.info(f"   Тип: {prod_type}")
    logger.info(f"   Текущий статус: {status}")
    logger.info(f"   Название: {name or 'Нет'}")
    logger.info(f"   Артикул: {article or 'Нет'}")
    
    # 2. Подготавливаем товар (устанавливаем статус pending)
    original_status = prepare_product_for_processing(product_id)
    if original_status is None:
        return False
    
    # 3. Запускаем process_products.py
    try:
        # Определяем команду
        cmd = [sys.executable, "process_products.py", "--process", "1"]
        
        if use_selenium:
            cmd.append("--selenium")
            logger.info("🚀 Запуск в ПОЛНОМ режиме (с Selenium)")
        else:
            cmd.append("--fast-mode")
            logger.info("⚡ Запуск в БЫСТРОМ режиме (без Selenium)")
        
        if delay:
            cmd.extend(["--delay", str(delay)])
            logger.info(f"⏱️  Задержка: {delay} сек")
        
        logger.info(f"▶️  Выполняю команду: {' '.join(cmd)}")
        
        # Запускаем процесс с безопасной обработкой кодировки
        result = safe_subprocess_run(cmd)
        
        # Выводим результат
        print("\n" + "="*60)
        print("📊 ВЫВОД ПРОГРАММЫ:")
        print("="*60)
        
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("\n⚠️  ОШИБКИ/ПРЕДУПРЕЖДЕНИЯ:")
            print("-" * 40)
            print(result.stderr)
        
        print("="*60)
        
        # 4. Проверяем результат
        if result.returncode != 0:
            logger.warning(f"⚠️  Обработка завершилась с кодом {result.returncode}")
            
            # Восстанавливаем оригинальный статус
            restore_product_status(product_id, original_status)
            
            # Проверяем результат в базе
            check_processing_result(product_id)
            
            return False
        
        logger.info(f"✅ Команда выполнена успешно (код: {result.returncode})")
        
        # 5. Проверяем результат обработки в базе
        success = check_processing_result(product_id)
        
        if success:
            logger.info(f"🎉 Товар {product_id} успешно обработан!")
        else:
            logger.warning(f"⚠️  Товар {product_id} обработан, но есть проблемы")
            # Восстанавливаем оригинальный статус если не успех
            restore_product_status(product_id, original_status)
        
        return success
        
    except subprocess.TimeoutExpired:
        logger.error(f"⏰ Таймаут обработки товара {product_id}")
        restore_product_status(product_id, original_status)
        return False
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска process_products.py: {e}")
        restore_product_status(product_id, original_status)
        return False

def check_processing_result(product_id):
    """Проверить результат обработки товара в базе"""
    try:
        from src.database import DatabaseManager
        db = DatabaseManager()
        with db.connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    prod_name,
                    parse_status,
                    parse_error,
                    parsed_at,
                    prod_price_new,
                    prod_article,
                    prod_img_url
                FROM products 
                WHERE id = %s;
            """, (product_id,))
            
            result = cursor.fetchone()
            
            if not result:
                logger.error(f"❌ Товар {product_id} не найден после обработки")
                return False
            
            name, status, error, parsed_at, price, article, img_url = result
            
            print(f"\n📊 РЕЗУЛЬТАТ ОБРАБОТКИ ТОВАРА {product_id}:")
            print("-" * 50)
            print(f"  Название: {name or 'Нет'}")
            print(f"  Артикул: {article or 'Нет'}")
            print(f"  Цена: {price or 'Нет'}₽")
            print(f"  Статус: {status or 'Нет'}")
            print(f"  Ошибка: {error or 'Нет'}")
            print(f"  Время обработки: {parsed_at or 'Нет'}")
            print(f"  Изображение: {'Есть' if img_url else 'Нет'}")
            
            if status == 'success':
                print(f"\n✅ ОБРАБОТКА УСПЕШНА!")
                return True
            elif status == 'failed':
                print(f"\n❌ ОБРАБОТКА ПРОВАЛИЛАСЬ: {error}")
                return False
            elif status == 'pending':
                print(f"\n⚠️  ТОВАР ВСЕ ЕЩЕ В ОЖИДАНИИ ОБРАБОТКИ")
                return False
            else:
                print(f"\n❓ НЕИЗВЕСТНЫЙ СТАТУС: {status}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Ошибка проверки результата: {e}")
        return False
    finally:
        if 'db' in locals():
            db.close()

def list_available_products(limit=20):
    """Показать список доступных товаров"""
    try:
        from src.database import DatabaseManager
        db = DatabaseManager()
        with db.connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id, 
                    url, 
                    prod_type,
                    parse_status,
                    prod_name,
                    prod_article,
                    parsed_at,
                    prod_price_new
                FROM products 
                WHERE prod_type = 'product'
                ORDER BY 
                    CASE 
                        WHEN parse_status = 'failed' THEN 1
                        WHEN parse_status = 'pending' THEN 2
                        WHEN parse_status IS NULL THEN 3
                        ELSE 4
                    END,
                    id ASC
                LIMIT %s;
            """, (limit,))
            
            products = cursor.fetchall()
            
            print("\n📋 ДОСТУПНЫЕ ТОВАРЫ ДЛЯ ОБРАБОТКИ:")
            print("="*100)
            print(f"{'ID':4} | {'Статус':10} | {'Цена':8} | {'Артикул':12} | {'Название':30} | {'URL'}")
            print("-"*100)
            
            for prod in products:
                prod_id, url, prod_type, status, name, article, parsed_at, price = prod
                
                # Сокращаем URL и название для отображения
                short_url = url[:30] + "..." if len(url) > 30 else url
                short_name = (name[:27] + "...") if name and len(name) > 30 else (name or "Нет")
                
                # Иконка статуса
                status_icon = "❓"
                if status == 'success':
                    status_icon = "✅"
                elif status == 'failed':
                    status_icon = "❌"
                elif status == 'pending':
                    status_icon = "⏳"
                elif status is None:
                    status_icon = "❔"
                
                # Форматируем цену
                price_str = f"{price}₽" if price else "—"
                
                print(f"{prod_id:4} | {status_icon} {status or 'NULL':8} | {price_str:8} | {article or '':12} | {short_name:30} | {short_url}")
            
            print("="*100)
            print(f"Всего товаров: {len(products)}")
            
            if products:
                print(f"\n💡 Пример команды для обработки: python {sys.argv[0]} --id {products[0][0]}")
            
    except ImportError:
        print("❌ Не удалось подключиться к базе данных. Проверьте настройки подключения.")
    except Exception as e:
        logger.error(f"Ошибка получения списка товаров: {e}")
    finally:
        if 'db' in locals():
            db.close()

def main():
    parser = argparse.ArgumentParser(
        description='Обработка товара по ID из БД hello54.ru',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python test_process_by_id.py --list                # Показать список товаров
  python test_process_by_id.py --id 123              # Обработать товар ID 123
  python test_process_by_id.py --id 123 --selenium   # Обработать с Selenium
  python test_process_by_id.py --id 123 --delay 2.0  # С задержкой 2 сек

Доступные режимы:
  --fast-mode (по умолчанию) - быстрая обработка через requests
  --selenium                 - полная обработка через браузер
"""
    )
    
    parser.add_argument('--id', type=int, help='ID товара для обработки')
    parser.add_argument('--list', action='store_true', help='Показать список товаров')
    parser.add_argument('--selenium', action='store_true', help='Использовать Selenium')
    parser.add_argument('--delay', type=float, default=1.0, help='Задержка между запросами (сек)')
    parser.add_argument('--limit', type=int, default=20, help='Количество товаров в списке')
    parser.add_argument('--debug', action='store_true', help='Включить отладочный вывод')
    
    args = parser.parse_args()
    
    # Настраиваем уровень логирования
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Включен отладочный режим")
    
    print("🔧 ТЕСТОВЫЙ СКРИПТ ДЛЯ ОБРАБОТКИ ТОВАРА ПО ID")
    print("="*60)
    
    if args.list:
        list_available_products(args.limit)
    elif args.id:
        success = process_specific_product(
            product_id=args.id,
            use_selenium=args.selenium,
            delay=args.delay
        )
        
        if success:
            print(f"\n🎉 ТОВАР ID {args.id} УСПЕШНО ОБРАБОТАН!")
        else:
            print(f"\n💥 ОШИБКА ОБРАБОТКИ ТОВАРА ID {args.id}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()