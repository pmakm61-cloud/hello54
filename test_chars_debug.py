# test_chars_debug.py
import sys
sys.path.append('.')
import logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from src.selenium_characteristics import debug_characteristics

# Настройка Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")  # Можно убрать для визуальной отладки
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

# Тестовый URL
test_url = "https://hello54.ru/catalog/sumka-remen-joy-room-jr-cy211-hiding-waist-m-l-black-rose.html"

driver = None
try:
    print("🚀 ЗАПУСК ДЕТАЛЬНОЙ ПРОВЕРКИ")
    print("="*60)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(test_url)
    
    # Даем время на полную загрузку
    import time
    time.sleep(3)
    
    # Запускаем отладочную функцию
    chars = debug_characteristics(driver, test_url)
    
    if chars:
        print(f"\n🎉 УСПЕХ! Собрано {len(chars)} характеристик")
        print("Данные готовы для записи в БД.")
    else:
        print(f"\n💥 ПРОБЛЕМА! Характеристики не собраны")
        print("Нужно проверить HTML-структуру страницы.")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
finally:
    if driver:
        driver.quit()