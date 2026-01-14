# test_article_finder.py
import sys
from pathlib import Path
import logging

sys.path.append(str(Path(__file__).parent))

from src.product_processor import ProductProcessor

# Настройка логирования с DEBUG уровнем
logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

def test_article_finding():
    """Тестируем поиск артикула"""
    
    test_urls = [
        "https://hello54.ru/catalog/kartkholder-ch01-futlyar-dlya-kart-na-kleevoy-osnove-black-206661.html",
        "https://hello54.ru/catalog/kartkholder-ch01-futlyar-dlya-kart-na-kleevoy-osnove-green-206656.html",
        "https://hello54.ru/catalog/kartkholder-ch01-futlyar-dlya-kart-na-kleevoy-osnove-violet-206659.html"
    ]
    
    processor = ProductProcessor(use_selenium=False)
    
    print("🧪 ТЕСТ ПОИСКА АРТИКУЛОВ")
    print("="*60)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}. Тестируем: {url}")
        
        result = processor._parse_with_requests(url)
        
        if result['success']:
            data = result['data']
            print(f"   ✅ Название: {data['prod_name'][:40]}...")
            print(f"   ✅ Цена: {data['prod_price_new']} руб.")
            print(f"   ✅ Артикул: {data['prod_article'] or 'НЕ НАЙДЕН!'}")
            print(f"   ✅ Источник: {result['source']}")
        else:
            print(f"   ❌ Ошибка: {result['error']}")
    
    processor.close()

if __name__ == "__main__":
    test_article_finding()