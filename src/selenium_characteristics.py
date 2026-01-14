# src/selenium_characteristics.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
import logging
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)

def extract_characteristics_hello54(driver, timeout=15):
    """
    Извлечение характеристик товара для hello54.ru
    ИСПРАВЛЕННАЯ версия
    """
    characteristics = {}
    
    try:
        logger.info("🔍 Начинаю поиск характеристик...")
        
        # 1. Ждем загрузки ВСЕЙ страницы
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # 2. Ищем блок характеристик РАЗНЫМИ способами
        properties_div = None
        
        # Попробуем несколько селекторов
        selectors_to_try = [
            (By.CLASS_NAME, "b-properties"),
            (By.CLASS_NAME, "b-card-detail__properties"),
            (By.CSS_SELECTOR, "div[class*='properties']"),
            (By.XPATH, "//div[contains(@class, 'properties')]"),
            (By.XPATH, "//div[text()='Основные характеристики']/parent::div"),
            (By.XPATH, "//div[contains(text(), 'характеристик')]/parent::div")
        ]
        
        for by, selector in selectors_to_try:
            try:
                logger.debug(f"Пробую селектор: {selector}")
                properties_div = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((by, selector))
                )
                logger.info(f"✅ Найден блок характеристик: {selector}")
                break
            except (TimeoutException, NoSuchElementException):
                continue
        
        if not properties_div:
            logger.warning("❌ Блок характеристик не найден ни одним селектором")
            # Проверим, что вообще на странице
            logger.debug(f"Текущий URL: {driver.current_url}")
            logger.debug(f"Заголовок страницы: {driver.title}")
            logger.debug(f"Page source length: {len(driver.page_source)}")
            return characteristics
        
        # 3. Прокручиваем к блоку характеристик (если нужно)
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", properties_div)
            import time
            time.sleep(0.5)  # Даем время на прокрутку
        except:
            pass
        
        # 4. Ищем элементы характеристик ВНУТРИ блока
        try:
            # Способ 1: Стандартные элементы b-properties__item
            property_items = properties_div.find_elements(By.CLASS_NAME, "b-properties__item")
            
            if not property_items:
                # Способ 2: Любые div внутри блока
                property_items = properties_div.find_elements(By.XPATH, ".//div[div[@class='b-properties__name'] and div[@class='b-properties__value']]")
            
            if not property_items:
                # Способ 3: Ищем пары названий и значений
                names = properties_div.find_elements(By.CLASS_NAME, "b-properties__name")
                values = properties_div.find_elements(By.CLASS_NAME, "b-properties__value")
                
                if len(names) == len(values):
                    for i in range(len(names)):
                        name = names[i].text.strip().rstrip(':')
                        value = values[i].text.strip()
                        if name and value:
                            characteristics[name] = value
                    logger.info(f"✅ Найдено {len(characteristics)} характеристик (способ 3)")
                    return characteristics
            
            logger.info(f"📊 Найдено элементов характеристик: {len(property_items)}")
            
            # 5. Обрабатываем каждый элемент
            for i, item in enumerate(property_items):
                try:
                    # Прокручиваем к элементу
                    driver.execute_script("arguments[0].scrollIntoView(true);", item)
                    
                    # Ищем название и значение
                    name_elem = item.find_element(By.CLASS_NAME, "b-properties__name")
                    value_elem = item.find_element(By.CLASS_NAME, "b-properties__value")
                    
                    name = name_elem.text.strip().rstrip(':').strip()
                    value = value_elem.text.strip()
                    
                    if name and value:
                        characteristics[name] = value
                        logger.debug(f"   [{i+1}] ✅ {name}: {value}")
                    else:
                        logger.debug(f"   [{i+1}] ⚠️ Пустые значения: name='{name}', value='{value}'")
                        
                except NoSuchElementException:
                    # Пробуем альтернативные селекторы внутри элемента
                    try:
                        name_elem = item.find_element(By.XPATH, ".//div[contains(@class, 'name')]")
                        value_elem = item.find_element(By.XPATH, ".//div[contains(@class, 'value')]")
                        
                        name = name_elem.text.strip().rstrip(':').strip()
                        value = value_elem.text.strip()
                        
                        if name and value:
                            characteristics[name] = value
                            logger.debug(f"   [{i+1}] ✅ (alt) {name}: {value}")
                    except:
                        logger.debug(f"   [{i+1}] ❌ Не удалось извлечь характеристику")
                        continue
                except Exception as e:
                    logger.debug(f"   [{i+1}] ❌ Ошибка: {e}")
                    continue
            
            logger.info(f"✅ ИТОГО собрано характеристик: {len(characteristics)}")
            
            # 6. Если не нашли - делаем скриншот для отладки
            if not characteristics:
                try:
                    screenshot_path = f"debug_characteristics_{driver.current_url.split('/')[-1]}.png"
                    driver.save_screenshot(screenshot_path)
                    logger.warning(f"⚠️ Характеристики не найдены. Скриншот сохранен: {screenshot_path}")
                except:
                    pass
            
            return characteristics
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке элементов: {e}")
            return characteristics
            
    except Exception as e:
        logger.error(f"❌ Общая ошибка сбора характеристик: {e}")
        return characteristics

# ДОПОЛНИТЕЛЬНО: функция для быстрой проверки
def debug_characteristics(driver, url):
    """
    Расширенная отладка сбора характеристик
    """
    print("\n" + "="*80)
    print(f"🔍 ДЕБАГ ХАРАКТЕРИСТИК: {url}")
    print("="*80)
    
    # 1. Проверяем текущее состояние страницы
    print(f"1. Текущий URL: {driver.current_url}")
    print(f"2. Заголовок: {driver.title}")
    print(f"3. Длина page source: {len(driver.page_source)} символов")
    
    # 2. Ищем ВСЕ элементы с классами
    from selenium.webdriver.common.by import By
    all_properties = driver.find_elements(By.CSS_SELECTOR, "[class*='properties']")
    print(f"4. Всего элементов с 'properties' в классе: {len(all_properties)}")
    
    for i, elem in enumerate(all_properties[:5]):
        classes = elem.get_attribute('class')
        text = elem.text[:100] if elem.text else "пусто"
        print(f"   {i+1}. Классы: {classes}")
        print(f"      Текст: {text}")
    
    # 3. Ищем конкретно b-properties__item
    all_items = driver.find_elements(By.CLASS_NAME, "b-properties__item")
    print(f"5. Элементов b-properties__item: {len(all_items)}")
    
    for i, item in enumerate(all_items[:3]):
        html = item.get_attribute('outerHTML')[:200]
        print(f"   {i+1}. HTML: {html}")
    
    # 4. Пробуем собрать характеристики
    print("\n6. Пробуем собрать характеристики...")
    chars = extract_characteristics_hello54(driver)
    
    if chars:
        print(f"✅ УСПЕХ! Собрано {len(chars)} характеристик:")
        for name, value in chars.items():
            print(f"   • {name}: {value}")
    else:
        print("❌ Характеристики не собраны")
        
        # Делаем скриншот
        try:
            import time
            filename = f"debug_{int(time.time())}.png"
            driver.save_screenshot(filename)
            print(f"📸 Скриншот сохранен: {filename}")
        except:
            pass
    
    print("="*80)
    return chars