python -c "
import sys
sys.path.append('.')
from src.product_processor import ProductProcessor
import logging
import json

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

print('='*60)
print('🔍 ДИАГНОСТИКА ПРОБЛЕМЫ С ХАРАКТЕРИСТИКАМИ')
print('='*60)

p = ProductProcessor(use_selenium=False)

# Тестовый URL
url = 'https://hello54.ru/catalog/kartkholder-ch09-safemag-pc-transparent-242461.html'

print(f'\\n1. 📄 ПАРСИНГ СТРАНИЦЫ: {url}')
result = p._parse_with_requests(url)

if result['success']:
    data = result['data']
    
    print(f'\\n2. 📊 ДАННЫЕ В РЕЗУЛЬТАТЕ:')
    print(f'   Название: {data[\"prod_name\"]}')
    print(f'   Артикул: {data[\"prod_article\"]}')
    print(f'   Цена: {data[\"prod_price_new\"]}₽')
    
    print(f'\\n3. 🔍 ХАРАКТЕРИСТИКИ:')
    chars = data.get('characteristics', {})
    print(f'   Количество: {len(chars)}')
    if chars:
        for i, (name, value) in enumerate(chars.items(), 1):
            print(f'   {i:2}. {name}: {value}')
    else:
        print('   ⚠️ Характеристики отсутствуют в результате')
    
    print(f'\\n4. 📦 ПРЕОБРАЗОВАНИЕ В JSON:')
    if chars:
        try:
            json_str = json.dumps(chars, ensure_ascii=False, indent=2)
            print(f'   ✅ Успешно: {len(json_str)} символов')
            print(f'   Первые 200 символов JSON:')
            print('   ' + json_str[:200].replace('\\n', '\\n   '))
        except Exception as e:
            print(f'   ❌ Ошибка: {e}')
    else:
        print('   ⚠️ Нечего преобразовывать')
    
    print(f'\\n5. 🗄️ ТЕСТИРУЕМ ОБНОВЛЕНИЕ В БД:')
    # Создадим тестовый ID (например, 99999 для теста)
    test_product_id = 99999
    print(f'   Тестовый ID продукта: {test_product_id}')
    
    # Моделируем вызов update_product_data
    print(f'   Данные для обновления:')
    print(f'     - prod_name: {data[\"prod_name\"]}')
    print(f'     - prod_article: {data[\"prod_article\"]}')
    print(f'     - characteristics: {len(chars)} шт.')
    
else:
    print(f'❌ Ошибка парсинга: {result[\"error\"]}')

print('\\n' + '='*60)
print('📋 ДИАГНОСТИКА ЗАВЕРШЕНА')
print('='*60)

p.close()
"