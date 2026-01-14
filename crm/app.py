# hello54_crm/app.py
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Импортируем наши утилиты
from utils import database, config
from api import products, parser, images

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOGS_DIR / 'crm.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Создаем приложение
app = FastAPI(
    title="Hello54 Parser CRM",
    description="Управление парсером сайта hello54.ru",
    version="1.0.0"
)

# Настраиваем статические файлы и шаблоны
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
templates = Jinja2Templates(directory=config.TEMPLATES_DIR)

# Подключаем API роутеры
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(parser.router, prefix="/api/parser", tags=["parser"])
app.include_router(images.router, prefix="/api/images", tags=["images"])

# ======================
# ВЕБ-ИНТЕРФЕЙС (страницы)
# ======================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, limit: int = 50, offset: int = 0):
    """Главная страница - список товаров"""
    data = database.get_products(limit=limit, offset=offset)
    stats = database.get_statistics()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "products": data['products'],
        "total": data['total'],
        "limit": limit,
        "offset": offset,
        "stats": stats
    })

@app.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: int):
    """Детальная страница товара"""
    product = database.get_product_by_id(product_id)
    
    if not product:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Товар с ID {product_id} не найден"
        })
    
    return templates.TemplateResponse("product_detail.html", {
        "request": request,
        "product": product
    })

@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    """Страница статистики"""
    stats = database.get_statistics()
    
    return templates.TemplateResponse("stats.html", {
        "request": request,
        "stats": stats
    })

# ======================
# Запуск приложения
# ======================

if __name__ == "__main__":
    import uvicorn
    logger.info(f"🚀 Запуск CRM на http://{config.SERVER_CONFIG['host']}:{config.SERVER_CONFIG['port']}")
    uvicorn.run(
        "app:app",
        host=config.SERVER_CONFIG['host'],
        port=config.SERVER_CONFIG['port'],
        reload=config.SERVER_CONFIG['debug']
    )