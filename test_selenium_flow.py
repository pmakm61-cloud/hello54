# test_selenium_flow.py
import sys
sys.path.append('.')
import logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

from src.product_processor import ProductProcessor

# Тестовый URL (тот, где точно есть характеристики)
test_url = "https://hello54.ru/catalog/sumka-remen-joy-room-jr-cy211-hiding-waist-m-l-black-rose.html"

print("🔍 ТЕСТ ПОТОКА ДАННЫХ Selenium -> БД")
print("="*60)

p = ProductProcessor(use_selenium=True)

# 1. Парсим страницу
print(f"\n1. ПАРСИНГ С SELENIUM: {test_url}")
result = p.parse_product_page(test_url)

if result['success']:
    data = result['data']
    print(f"✅ Успешно!")
    print(f"   Название: {data.get('prod_name')}")
    print(f"   Цена: {data.get('prod_price_new')}")
    print(f"   Артикул: {data.get('prod_article')}")
    
    # Характеристики
    if 'characteristics' in data:
        chars = data['characteristics']
        print(f"   Характеристики: {len(chars)} шт")
        if chars:
            print("   Примеры:")
            for name, value in list(chars.items())[:5]:
                print(f"      • {name}: {value}")
    else:
        print(f"   ❌ Характеристики ОТСУТСТВУЮТ в данных!")
else:
    print(f"❌ Ошибка парсинга: {result['error']}")

print(f"\n2. ТЕСТИРУЕМ update_product_data()...")
# Представим, что у нас тестовый ID 999
test_data = {
    'success': True,
    'data': data if result['success'] else {},
    'error': None
}

if result['success']:
    # Проверяем, что будет передано в update_product_data
    print(f"   Данные для записи в БД:")
    print(f"     - prod_name: {data.get('prod_name')}")
    print(f"     - prod_price_new: {data.get('prod_price_new')}")
    print(f"     - characteristics присутствуют: {'characteristics' in data}")
    if 'characteristics' in data:
        print(f"     - количество: {len(data['characteristics'])}")
    
    # Проверяем преобразование в JSON
    import json
    if 'characteristics' in data and data['characteristics']:
        try:
            json_str = json.dumps(data['characteristics'], ensure_ascii=False)
            print(f"     - JSON успешно: {len(json_str)} символов")
        except Exception as e:
            print(f"     - ❌ Ошибка JSON: {e}")

p.close()