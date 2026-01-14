# hello54_crm/api/products.py
from fastapi import APIRouter, HTTPException
from utils import database

router = APIRouter()

@router.get("/")
async def get_products(limit: int = 50, offset: int = 0):
    """Получение списка товаров"""
    return database.get_products(limit=limit, offset=offset)

@router.get("/{product_id}")
async def get_product(product_id: int):
    """Получение товара по ID"""
    product = database.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product

@router.get("/{product_id}/characteristics")
async def get_product_characteristics(product_id: int):
    """Получение характеристик товара"""
    product = database.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    
    return {
        "product_id": product_id,
        "characteristics": product.get('prod_characteristics', {})
    }