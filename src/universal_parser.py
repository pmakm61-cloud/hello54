# src/universal_parser.py
"""
Универсальный парсер для сайта hello54.ru
Поддерживает два типа страниц:
1. Структурированные (с div.spec-row, div.spec-name, div.spec-value)
2. Текстовые (характеристики в виде обычного текста)
"""

import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def parse_product_page(soup, url):
    """
    Универсальный парсинг страницы товара hello54.ru
    
    Args:
        soup: BeautifulSoup объект страницы
        url: URL страницы для отладки
    
    Returns:
        dict: {
            'prod_name': str,
            'prod_price_new': float,
            'prod_price_old': float,
            'prod_article': str,
            'prod_img_url': str,
            'characteristics': dict
        }
    """
    result = {
        'prod_name': None,
        'prod_price_new': None,
        'prod_price_old': None,
        'prod_article': None,
        'prod_img_url': None,
        'characteristics': {}
    }
    
    try:
        # 1. Название товара
        result['prod_name'] = _extract_product_name(soup)
        
        # 2. Цены
        result['prod_price_new'], result['prod_price_old'] = _extract_prices(soup)
        
        # 3. Артикул
        result['prod_article'] = _extract_article(soup, url)
        
        # 4. URL изображения
        result['prod_img_url'] = _extract_image_url(soup)
        
        # 5. Характеристики
        result['characteristics'] = _extract_characteristics(soup)
        
        logger.debug(f"✅ Универсальный парсер: {result['prod_name'][:50] if result['prod_name'] else 'Без названия'}")
        logger.debug(f"   Артикул: {result['prod_article']}, Цена: {result['prod_price_new']}₽")
        logger.debug(f"   Характеристик: {len(result['characteristics'])}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в универсальном парсере для {url}: {e}")
    
    return result

def _extract_product_name(soup):
    """Извлечение названия товара"""
    # Способ 1: H1 с классом product-title
    h1_tag = soup.find('h1', class_='product-title')
    if h1_tag:
        return h1_tag.get_text(strip=True)
    
    # Способ 2: Из title
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.get_text(strip=True)
        # Убираем " — hello54.ru" из title
        if '—' in title_text:
            return title_text.split('—')[0].strip()
        return title_text
    
    # Способ 3: Любой H1
    h1_any = soup.find('h1')
    if h1_any:
        return h1_any.get_text(strip=True)
    
    return None

def _extract_prices(soup):
    """Извлечение цен (новой и старой)"""
    price_new = None
    price_old = None
    
    # СПОСОБ 1: Структурированные цены (div.current-price, div.old-price)
    current_price_div = soup.find('div', class_='current-price')
    old_price_div = soup.find('div', class_='old-price')
    
    if current_price_div:
        price_text = current_price_div.get_text(strip=True)
        price_new = _clean_price(price_text)
    
    if old_price_div:
        price_text = old_price_div.get_text(strip=True)
        price_old = _clean_price(price_text)
    
    # СПОСОБ 2: Текстовые цены (ищем в тексте)
    if not price_new:
        # Ищем паттерны типа "59,40 руб." или "349 руб."
        all_text = soup.get_text()
        price_patterns = [
            r'(\d+[\s ]*[\d,]*)\s*руб[.\s]',  # "59,40 руб." или "1 290 руб"
            r'(\d+[\s ]*[\d,]*)₽',            # "1 290 ₽"
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            if matches:
                # Берем первую найденную цену как текущую
                price_text = matches[0].replace(' ', '').replace(' ', '')
                price_new = _clean_price(price_text)
                break
    
    # Если нашли только новую цену, пробуем найти старую
    if price_new and not price_old:
        all_text = soup.get_text()
        # Ищем старую цену рядом с новой (часто идет после)
        lines = all_text.split('\n')
        for i, line in enumerate(lines):
            if str(int(price_new)) in line.replace(' ', ''):
                # Смотрим следующие строки на наличие старой цены
                for j in range(i+1, min(i+5, len(lines))):
                    if re.search(r'\d+[\s,]*\d*\s*руб', lines[j]):
                        old_match = re.search(r'(\d+[\s,]*\d*)', lines[j])
                        if old_match:
                            price_old = _clean_price(old_match.group(1))
                            break
                break
    
    return price_new, price_old

def _extract_article(soup, url):
    """Извлечение артикула"""
    # СПОСОБ 1: Из структурированного блока
    sku_div = soup.find('div', class_='product-sku')
    if sku_div:
        value_span = sku_div.find('span', class_='value')
        if value_span:
            return value_span.get_text(strip=True)
    
    # СПОСОБ 2: Ищем текст "Артикул:"
    all_text = soup.get_text()
    article_match = re.search(r'Артикул[:\s]*([A-Za-z0-9\-]+)', all_text, re.IGNORECASE)
    if article_match:
        return article_match.group(1).strip()
    
    # СПОСОБ 3: Из URL
    url_match = re.search(r'/([^/]+)\.html$', url)
    if url_match:
        article_from_url = url_match.group(1)
        # Извлекаем последнюю часть после последнего -
        if '-' in article_from_url:
            return article_from_url.split('-')[-1]
        return article_from_url
    
    return None

def _extract_image_url(soup):
    """Извлечение URL изображения"""
    # Способ 1: Изображение с классом sp-image
    img_tag = soup.find('img', class_='sp-image')
    if img_tag:
        img_url = img_tag.get('src')
        if img_url:
            if img_url.startswith('/'):
                img_url = 'https://hello54.ru' + img_url
            return img_url
    
    # Способ 2: Любое изображение в основном блоке
    main_image_div = soup.find('div', class_='main-image')
    if main_image_div:
        img_tag = main_image_div.find('img')
        if img_tag and img_tag.get('src'):
            img_url = img_tag.get('src')
            if img_url.startswith('/'):
                img_url = 'https://hello54.ru' + img_url
            return img_url
    
    # Способ 3: Meta-тег og:image
    meta_image = soup.find('meta', property='og:image')
    if meta_image and meta_image.get('content'):
        return meta_image.get('content')
    
    return None

def _extract_characteristics(soup):
    """Извлечение характеристик (универсальный метод)"""
    characteristics = {}
    
    # СПОСОБ 1: Структурированные характеристики (div.spec-row)
    spec_section = soup.find('div', {'id': 'characteristics'})
    if not spec_section:
        spec_section = soup.find('div', class_='specifications')
    
    if spec_section:
        spec_rows = spec_section.find_all('div', class_='spec-row')
        
        for row in spec_rows:
            spec_name = row.find('div', class_='spec-name')
            spec_value = row.find('div', class_='spec-value')
            
            if spec_name and spec_value:
                name = spec_name.get_text(strip=True).rstrip(':')
                value = spec_value.get_text(strip=True)
                
                if name and value:
                    characteristics[name] = value
    
    # Если структурированных характеристик нет, используем текстовый парсинг
    if not characteristics:
        characteristics = _extract_text_characteristics(soup)
    
    return characteristics

def _extract_text_characteristics(soup):
    """Извлечение характеристик из текста (для неструктурированных страниц)"""
    characteristics = {}
    all_text = soup.get_text()
    
    # Паттерны для поиска характеристик
    patterns = [
        # "Название характеристики: значение"
        (r'([А-Яа-яA-Za-z\s\-]+)[:\-]\s*([^\n\r]+)', 'key_value'),
        # "Артикул: 206655"
        (r'(Артикул)[:\s]*([^\n\r]+)', 'key_value'),
        # "Основной цвет: blue"
        (r'(Основной цвет|Цвет|Материал|Размеры|Вес|Совместимость)[:\s]*([^\n\r]+)', 'key_value'),
    ]
    
    for pattern, pattern_type in patterns:
        matches = re.findall(pattern, all_text, re.IGNORECASE)
        for match in matches:
            if pattern_type == 'key_value' and len(match) == 2:
                key = match[0].strip()
                value = match[1].strip()
                
                # Очищаем ключ и значение
                key = re.sub(r'\s+', ' ', key).strip()
                value = re.sub(r'\s+', ' ', value).strip()
                
                # Убираем лишние символы
                value = value.rstrip('.,;')
                
                if key and value and len(key) < 50:
                    characteristics[key] = value
    
    # Также ищем в строках с разделителями
    lines = [line.strip() for line in all_text.split('\n') if line.strip()]
    
    for line in lines:
        # Пропускаем слишком длинные или короткие строки
        if len(line) < 10 or len(line) > 200:
            continue
        
        # Ищем строки с двоеточием
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                
                # Фильтруем очевидные не-характеристики
                if (key and value and 
                    not any(word in key.lower() for word in ['доставка', 'корзину', 'купить', 'руб', 'скидка']) and
                    not any(word in value.lower() for word in ['доставка', 'бесплатно', 'корзину'])):
                    
                    # Ограничиваем длину ключа
                    if len(key) < 40:
                        characteristics[key] = value
    
    return characteristics

def _clean_price(price_text):
    """Очистка текста цены"""
    if not price_text:
        return None
    
    # Убираем все нецифровые символы, кроме запятой и точки
    cleaned = re.sub(r'[^\d,]', '', price_text.strip())
    cleaned = cleaned.replace(',', '.')
    
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None