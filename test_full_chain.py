# test_full_chain.py
import sys
sys.path.append('.')
import logging

logging.basicConfig(level=logging.DEBUG, format='%(message)s')

print("🔗 ТЕСТ ВСЕЙ ЦЕПОЧКИ ОБРАБОТКИ")
print("="*60)

# 1. Тестируем selenium_characteristics напрямую
print("\n1. ТЕСТ selenium_characteristics.py напрямую:")
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from src.selenium_characteristics import extract_characteristics_hello54

chrome_options = Options()
chrome_options.add_argument("--headless")
driver = webdriver.Chrome(options=chrome_options)

test_url = "https://hello54.ru/catalog/sumka-remen-joy-room-jr-cy211-hiding-waist-m-l-black-rose.html"
driver.get(test_url)
import time
time.sleep(3)

chars = extract_characteristics_hello54(driver)
print(f"   ✅ Характеристик собрано: {len(chars)}")
if chars:
    for name, value in chars.items():
        print(f"      • {name}: {value}")

driver.quit()

# 2. Тестируем selenium_parser через product_processor
print("\n2. ТЕСТ product_processor -> selenium_parser:")
from src.product_processor import ProductProcessor

p = ProductProcessor(use_selenium=True)
print(f"   Processor создан, use_selenium: {p.use_selenium}")

result = p.parse_product_page(test_url)
print(f"   Результат парсинга:")
print(f"      Успех: {result['success']}")
if result['success'] and result['data']:
    data = result['data']
    print(f"      Ключи в данных: {list(data.keys())}")
    print(f"      Есть характеристики: {'characteristics' in data}")
    if 'characteristics' in data:
        chars = data['characteristics']
        print(f"      Количество характеристик: {len(chars)}")
        if chars:
            for name, value in list(chars.items())[:3]:
                print(f"         • {name}: {value}")

p.close()

print("\n" + "="*60)