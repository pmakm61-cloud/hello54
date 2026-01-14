# src/selenium_parser.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import logging
from src.selenium_characteristics import extract_characteristics_hello54

logger = logging.getLogger(__name__)

class SeleniumParser:
    """
    Парсер на Selenium для загрузки динамических страниц.
    Используется только для сложных страниц, где нужен JavaScript.
    """
    
    def __init__(self, headless=True, driver_path=None):
        self.driver_path = driver_path
        self.headless = headless
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Настройка ChromeDriver с увеличенными таймаутами"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')  # Без GUI
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Стратегия загрузки - eager для скорости
        chrome_options.page_load_strategy = "eager"
        
        # User-Agent
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        try:
            if self.driver_path:
                service = Service(self.driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
            
            # УВЕЛИЧЕННЫЕ ТАЙМАУТЫ (130 секунд как вы просили)
            self.driver.set_page_load_timeout(130)  # Таймаут загрузки страницы
            self.driver.set_script_timeout(130)     # Таймаут выполнения скриптов
            
            logger.info("✅ Selenium ChromeDriver инициализирован с таймаутами 130с")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Selenium: {e}")
            raise
    
    def get_page_source(self, url, wait_for_elements=None, wait_time=10):
        """
        Получение полного HTML после загрузки JavaScript
        
        Args:
            url: URL страницы
            wait_for_elements: Список селекторов для ожидания (например, ['.b-price__value', 'h1'])
            wait_time: Время ожидания элементов в секундах
            
        Returns:
            str: Полный HTML код страницы или None при ошибке
        """
        try:
            logger.info(f"🌐 Selenium загружает: {url}")
            
            # Загрузка страницы
            self.driver.get(url)
            logger.debug("✅ Страница загружена")
            
            # Ожидание динамических элементов если указаны
            if wait_for_elements:
                wait = WebDriverWait(self.driver, wait_time)
                for selector in wait_for_elements:
                    try:
                        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                        logger.debug(f"✅ Элемент найден: {selector}")
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось найти элемент {selector}: {e}")
            
            # Дополнительная пауза для стабилизации
            time.sleep(1)
            
            # Получение полного HTML
            html = self.driver.page_source
            logger.info(f"✅ HTML получен ({len(html)} символов)")
            
            return html
            
        except Exception as e:
            logger.error(f"❌ Ошибка Selenium при загрузке {url}: {e}")
            return None
    
    def extract_data_directly(self, url):
        """
        Прямое извлечение данных через Selenium (без BeautifulSoup)
        Используется для сложных динамических страниц
        """
        try:
            logger.info(f"🔍 Selenium прямое извлечение: {url}")
            self.driver.get(url)
            
            wait = WebDriverWait(self.driver, 20)
            
            # Ожидаем загрузки ключевых элементов
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            data = {
                'prod_name': None,
                'prod_price_new': None,
                'prod_price_old': None,
                'prod_article': None,
                'prod_img_url': None
            }
            
            # 1. Название (div.b-title > h1) - для динамических страниц
            try:
                title_div = self.driver.find_element(By.CSS_SELECTOR, 'div.b-title')
                h1_element = title_div.find_element(By.TAG_NAME, 'h1')
                data['prod_name'] = h1_element.text.strip()
                logger.debug(f"✅ Название найдено (div.b-title > h1): {data['prod_name'][:50]}...")
            except:
                # Альтернатива: обычный h1
                try:
                    h1_element = self.driver.find_element(By.TAG_NAME, 'h1')
                    data['prod_name'] = h1_element.text.strip()
                    logger.debug(f"✅ Название найдено (h1): {data['prod_name'][:50]}...")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось найти название: {e}")
            
            # 2. Цена (div.b-price__value) - для динамических страниц
            try:
                price_element = self.driver.find_element(By.CSS_SELECTOR, 'div.b-price__value')
                data['prod_price_new'] = self._clean_price(price_element.text)
                logger.debug(f"✅ Новая цена найдена: {data['prod_price_new']}")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось найти цену: {e}")
            
            # 3. Старая цена (div.b-price__sale) - для динамических страниц
            try:
                old_price_element = self.driver.find_element(By.CSS_SELECTOR, 'div.b-price__sale')
                data['prod_price_old'] = self._clean_price(old_price_element.text)
                logger.debug(f"✅ Старая цена найдена: {data['prod_price_old']}")
            except Exception as e:
                logger.debug(f"ℹ️ Старая цена не найдена: {e}")
            
            # 4. Артикул (div.b-card-detail__code > span) - для динамических страниц
            try:
                code_div = self.driver.find_element(By.CSS_SELECTOR, 'div.b-card-detail__code')
                span_element = code_div.find_element(By.TAG_NAME, 'span')
                data['prod_article'] = span_element.text.strip()
                logger.debug(f"✅ Артикул найден: {data['prod_article']}")
            except:
                # Альтернативный поиск артикула
                try:
                    # Ищем текст "Артикул" на странице
                    page_text = self.driver.page_source
                    import re
                    match = re.search(r'Артикул[:\s]*(\d+)', page_text)
                    if match:
                        data['prod_article'] = match.group(1)
                        logger.debug(f"✅ Артикул найден (регулярка): {data['prod_article']}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось найти артикул: {e}")
            
            # 5. Изображение (img.sp-image) - для динамических страниц
            try:
                img_element = self.driver.find_element(By.CSS_SELECTOR, 'img.sp-image')
                data['prod_img_url'] = img_element.get_attribute('src')
                # Делаем URL абсолютным если нужно
                if data['prod_img_url'] and data['prod_img_url'].startswith('/'):
                    data['prod_img_url'] = 'https://hello54.ru' + data['prod_img_url']
                logger.debug(f"✅ URL изображения найден: {data['prod_img_url'][:50]}...")
            except Exception as e:
                logger.debug(f"ℹ️ Изображение не найдено: {e}")
            
            # 6. Характеристики товара
            try:
                characteristics = extract_characteristics_hello54(self.driver)
                if characteristics:
                    data['characteristics'] = characteristics
                    logger.info(f"✅ Собрано {len(characteristics)} характеристик")
                    # Для отладки покажем первые 3
                    for name, value in list(characteristics.items())[:3]:
                        logger.debug(f"   • {name}: {value}")
                else:
                    data['characteristics'] = {}
                    logger.warning("⚠️ Характеристики не найдены")
            except Exception as e:
                logger.error(f"❌ Ошибка сбора характеристик: {e}")
                data['characteristics'] = {}
            
            return {
                'success': True,
                'data': data,  # Теперь с характеристиками!
                'error': None,
                'source': 'selenium_direct'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка прямого извлечения Selenium: {e}")
            return {
                'success': False,
                'data': None,
                'error': f"Selenium ошибка: {e}",
                'source': 'selenium_direct'
            }
    
    def _clean_price(self, price_text):
        """Очистка текста цены"""
        if not price_text:
            return None
        
        # Удаляем "руб.", пробелы, заменяем запятую на точку
        import re
        cleaned = re.sub(r'[^\d,]', '', price_text.strip())
        cleaned = cleaned.replace(',', '.')
        
        try:
            return float(cleaned) if cleaned else None
        except:
            return None
            
    def extract_with_characteristics(self, url):
        """
        Полный сбор данных с характеристиками через Selenium
        """
        result = {
            'success': False,
            'data': None,
            'error': None,
            'source': 'selenium_full'
        }
        
        driver = None
        try:
            # Получаем драйвер
            driver = self.get_driver()
            if not driver:
                result['error'] = 'Не удалось инициализировать браузер'
                return result
            
            # Загружаем страницу
            driver.get(url)
            
            # Ждем загрузки
            import time
            time.sleep(2)  # Базовая задержка
            
            # Собираем основные данные (существующий метод)
            data = self.extract_data_directly(url)['data']
            if not data:
                result['error'] = 'Не удалось собрать основные данные'
                return result
            
            # ДОБАВЛЯЕМ: Собираем характеристики
            characteristics = extract_characteristics_hello54(driver)
            
            # Объединяем данные
            if characteristics:
                data['characteristics'] = characteristics
                self.logger.info(f"✅ Добавлено {len(characteristics)} характеристик")
            
            result['success'] = True
            result['data'] = data
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сбора данных: {e}")
            result['error'] = str(e)
            return result
        finally:
            if driver:
                driver.quit()        
    
    def close(self):
        """Закрытие драйвера"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("🔌 Selenium браузер закрыт")
            except Exception as e:
                logger.error(f"⚠️ Ошибка при закрытии браузера: {e}")
    
    def __del__(self):
        """Деструктор - автоматическое закрытие при удалении объекта"""
        self.close()