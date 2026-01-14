# src/crawler.py
import requests
from bs4 import BeautifulSoup
import time
import re
import urllib.parse
import logging
from datetime import datetime
from src.config import PARSER_CONFIG

logger = logging.getLogger(__name__)

class Hello54Crawler:
    """Парсер категорий сайта hello54.ru"""
    
    def __init__(self, db_manager):
        self.base_url = "https://hello54.ru"
        self.db = db_manager
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': PARSER_CONFIG['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        })
    
    def parse_category(self, category_url, max_pages_override=None):
        """Парсинг категории с пагинацией (ограничено 5 страницами по умолчанию)"""
        start_time = datetime.now()
        
        # Используем переданное ограничение или из конфига
        max_pages = max_pages_override or PARSER_CONFIG['max_pages_per_category']
        
        logger.info(f"🚀 Начинаю парсинг категории: {category_url}")
        logger.info(f"⚙️  Ограничение: максимум {max_pages} страниц")
        
        # Сохраняем категорию в БД
        category_name = self._extract_category_name(category_url)
        category_id = self.db.save_category(category_url, category_name)
        
        if not category_id:
            logger.error("❌ Не удалось сохранить категорию")
            return []
        
        all_product_urls = []
        page_num = 1
        
        try:
            while page_num <= max_pages:  # ← Здесь ограничение
                page_url = self._get_page_url(category_url, page_num)
                logger.info(f"📄 Страница {page_num}/{max_pages}: {page_url}")
                
                page_html = self._fetch_page(page_url)
                if not page_html:
                    logger.warning(f"⚠️ Не удалось загрузить страницу {page_num}")
                    break
                
                page_urls = self._extract_product_urls(page_html, category_url)
                logger.info(f"   Найдено товаров: {len(page_urls)}")
                
                added = self.db.save_product_urls(page_urls, category_id)
                all_product_urls.extend(page_urls)
                
                # Показываем прогресс
                self.show_progress(page_num, max_pages, len(all_product_urls))
                
                # ОСТАНОВИТЬ если достигнут лимит страниц
                if page_num >= max_pages:
                    logger.info(f"\n⏹️  Достигнут лимит в {max_pages} страниц")
                    break
                
                # Проверяем есть ли следующая страница
                if not self._has_next_page(page_html, page_num):
                    logger.info(f"\n✅ Достигнут конец категории на странице {page_num}")
                    break
                
                page_num += 1
                time.sleep(PARSER_CONFIG['delay_between_requests'])
                
        except Exception as e:
            logger.error(f"❌ Ошибка при парсинге: {e}")
        
        # Логируем результаты
        duration = (datetime.now() - start_time).total_seconds()
        self.db.log_parse_session(
            category_url=category_url,
            action="category_parse",
            details=f"Обработано {page_num-1} страниц (лимит {max_pages})",
            products_found=len(all_product_urls),
            products_added=len(set(all_product_urls)),
            duration=duration
        )
        
        unique_urls = list(set(all_product_urls))
        logger.info(f"✅ Завершено! Найдено {len(unique_urls)} уникальных товаров")
        logger.info(f"   Потрачено: {duration:.1f} сек, {len(unique_urls)/max(duration, 0.1):.1f} товаров/сек")
        
        return unique_urls
    
    def show_progress(self, page_num, max_pages, urls_found):
        """Показ прогресса парсинга"""
        progress = (page_num / max_pages) * 100
        print(f"\r📊 Прогресс: {page_num}/{max_pages} страниц ({progress:.0f}%) | "
              f"Товаров: {urls_found}", end='', flush=True)
    
    def _fetch_page(self, url):
        """Загрузка страницы"""
        try:
            response = self.session.get(url, timeout=PARSER_CONFIG['timeout'])
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Ошибка загрузки {url}: {e}")
            return None
    
    def _extract_product_urls(self, html, base_url):
        """Извлечение URL товаров со страницы"""
        urls = []
        
        if not html:
            return urls
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Ищем все ссылки
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link['href']
            
            # Проверяем, ведет ли на товар
            if self._is_product_url(href):
                full_url = self._make_absolute_url(href, base_url)
                if full_url and full_url not in urls:
                    urls.append(full_url)
        
        # Дополнительный поиск по структуре карточек
        product_cards = soup.find_all(['div', 'article'], class_=re.compile(r'card|product|item'))
        for card in product_cards:
            link = card.find('a', href=True)
            if link:
                href = link['href']
                if self._is_product_url(href):
                    full_url = self._make_absolute_url(href, base_url)
                    if full_url and full_url not in urls:
                        urls.append(full_url)
        
        return urls
    
    def _is_product_url(self, href):
        """Проверка, является ли ссылка товаром"""
        product_patterns = [
            r'\.html$',  # заканчивается на .html
            r'/catalog/',  # содержит /catalog/
            r'-\d+\.html$',  # содержит артикул в конце
        ]
        
        # Исключаем не товары
        exclude_patterns = [
            r'\.php$',
            r'\.xml$',
            r'\.json$',
            r'#',
            r'\?PAGEN_',
            r'/cart/',
            r'/auth/',
            r'/search/',
        ]
        
        href_lower = href.lower()
        
        # Проверка исключений
        for pattern in exclude_patterns:
            if re.search(pattern, href_lower):
                return False
        
        # Проверка на товар
        for pattern in product_patterns:
            if re.search(pattern, href_lower):
                return True
        
        return False
    
    def _make_absolute_url(self, href, base_url):
        """Преобразование относительного URL в абсолютный"""
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            return urllib.parse.urljoin(self.base_url, href)
        else:
            return urllib.parse.urljoin(base_url, href)
    
    def _get_page_url(self, base_url, page_num):
        """Формирование URL страницы с пагинацией"""
        if page_num == 1:
            return base_url
        else:
            # hello54.ru использует ?PAGEN_1=2 для пагинации
            separator = '?' if '?' not in base_url else '&'
            return f"{base_url}{separator}PAGEN_1={page_num}"
    
    def _has_next_page(self, html, current_page):
        """Проверка наличия следующей страницы"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Ищем кнопку "Следующая" или номер следующей страницы
        next_patterns = [
            f'PAGEN_1={current_page + 1}',
            'Следующая',
            'Далее',
            '>',
            '»'
        ]
        
        for pattern in next_patterns:
            if soup.find('a', href=lambda href: href and pattern in str(href)):
                return True
        
        return False
    
    def _detect_total_pages(self, html):
        """Определение общего количества страниц"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Ищем пагинацию
        pagination = soup.find('div', class_=re.compile(r'pagination|pages'))
        if pagination:
            page_numbers = pagination.find_all('a', href=True)
            max_page = 1
            
            for link in page_numbers:
                href = link.get('href', '')
                match = re.search(r'PAGEN_1=(\d+)', href)
                if match:
                    page_num = int(match.group(1))
                    if page_num > max_page:
                        max_page = page_num
            
            return max_page
        
        return 1
    
    def _extract_category_name(self, url):
        """Извлечение названия категории из URL"""
        # Пример: https://hello54.ru/catalog/chekhly-dlya-smartfonov/
        match = re.search(r'/catalog/([^/]+)/', url)
        if match:
            name = match.group(1).replace('-', ' ').title()
            return name
        return None