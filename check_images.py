# check_images.py
import sys
sys.path.append('.')
from save_img import ImageDownloader

downloader = ImageDownloader()
products = downloader.get_products_with_images(limit=5)

print("Примеры URL изображений:")
for product in products:
    print(f"\nID: {product['id']}")
    print(f"Название: {product['prod_name']}")
    print(f"URL: {product['prod_img_url']}")
    
    # Показываем как будет сохранено
    local_path, name, ext = downloader.parse_image_url(product['prod_img_url'])
    if local_path:
        print(f"→ Сохранится в: {local_path}/{name}{ext}")

downloader.close()