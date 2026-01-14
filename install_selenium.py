# install_selenium.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import sys

print("🚀 Установка и настройка Selenium...")

try:
    # 1. Проверяем установлен ли Selenium
    import selenium
    print("✅ Selenium уже установлен")
except ImportError:
    print("❌ Selenium не установлен")
    print("   Запустите: pip install selenium")
    sys.exit(1)

try:
    # 2. Автоматическая установка ChromeDriver через webdriver-manager
    print("🔧 Устанавливаем ChromeDriver...")
    
    # Устанавливаем менеджер драйверов
    from webdriver_manager.chrome import ChromeDriverManager
    
    # Автоматически скачиваем и устанавливаем ChromeDriver
    driver_path = ChromeDriverManager().install()
    
    print(f"✅ ChromeDriver установлен в: {driver_path}")
    
    # 3. Тестируем установку
    print("🧪 Тестируем установку...")
    
    # Настройка опций Chrome
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Фоновый режим
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Создаем драйвер
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    
    # Открываем тестовую страницу
    driver.get("https://www.google.com")
    
    # Проверяем заголовок
    print(f"✅ ChromeDriver работает! Заголовок страницы: {driver.title}")
    
    # Закрываем браузер
    driver.quit()
    print("✅ Все тесты пройдены успешно!")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    print("\n🔧 Попробуйте ручную установку (Способ 2)")