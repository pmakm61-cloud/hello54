# test_selenium.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_selenium_setup():
    """Тестируем установку Selenium"""
    print("🧪 Запускаем тест Selenium...")
    
    # Вариант 1: Если ChromeDriver в PATH
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Без графического интерфейса
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=options)
        print("✅ ChromeDriver найден в PATH")
        
    except Exception as e:
        print(f"❌ ChromeDriver не найден в PATH: {e}")
        
        # Вариант 2: Указать путь явно
        try:
            # Укажите путь к chromedriver.exe если он не в PATH
            # Для Windows: r'C:\path\to\chromedriver.exe'
            # Для Linux/macOS: '/usr/local/bin/chromedriver'
            chrome_driver_path = 'chromedriver'  # Или полный путь
            
            service = Service(chrome_driver_path)
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            
            driver = webdriver.Chrome(service=service, options=options)
            print(f"✅ ChromeDriver найден по указанному пути")
            
        except Exception as e2:
            print(f"❌ Не удалось запустить ChromeDriver: {e2}")
            print("\n🔧 Решение проблем:")
            print("1. Убедитесь, что Chrome установлен")
            print("2. Скачайте правильную версию ChromeDriver")
            print("3. Поместите chromedriver в PATH или укажите путь явно")
            return
    
    # Тестируем работу
    try:
        print("🌐 Открываем тестовую страницу...")
        driver.get("https://httpbin.org/html")
        
        # Ждем загрузки
        time.sleep(2)
        
        # Проверяем заголовок
        print(f"✅ Страница загружена: {driver.title}")
        
        # Ищем элемент
        h1_element = driver.find_element(By.TAG_NAME, 'h1')
        print(f"✅ Найден элемент h1: {h1_element.text}")
        
        # Делаем скриншот
        driver.save_screenshot('test_selenium.png')
        print("✅ Скриншот сохранен: test_selenium.png")
        
        # Тестируем ваш сайт
        print("\n🔍 Тестируем hello54.ru...")
        driver.get("https://hello54.ru/catalog/kartkholder-ch01-futlyar-dlya-kart-na-kleevoy-osnove-black-206661.html")
        
        # Ждем загрузки динамического контента
        wait = WebDriverWait(driver, 10)
        
        # Ждем появления цены
        price_element = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "b-price__value"))
        )
        print(f"✅ Динамический контент загружен!")
        print(f"   Цена на странице: {price_element.text}")
        
        # Ищем заголовок
        h1_tags = driver.find_elements(By.TAG_NAME, 'h1')
        if h1_tags:
            print(f"   Заголовок h1: {h1_tags[0].text}")
        
        # Сохраняем полный HTML для анализа
        with open('full_page_source.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("💾 Полный HTML сохранен в full_page_source.html")
        
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        
    except Exception as e:
        print(f"❌ Ошибка во время теста: {e}")
        
    finally:
        # Важно закрыть драйвер
        driver.quit()
        print("🔌 Браузер закрыт")

if __name__ == "__main__":
    test_selenium_setup()