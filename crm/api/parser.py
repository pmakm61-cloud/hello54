# hello54_crm/api/parser.py
import subprocess
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from utils import config

router = APIRouter()

@router.post("/parse/{product_id}")
async def parse_product(product_id: int, use_selenium: bool = True):
    """Запуск парсинга конкретного товара"""
    try:
        # Запускаем скрипт парсера
        script_path = Path(config.PARSER_SCRIPTS['process_products'])
        
        cmd = [
            "python", str(script_path),
            "--process", "1",
            "--selenium" if use_selenium else "--fast-mode",
            "--delay", "1.0"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=script_path.parent  # Запускаем из директории скрипта
        )
        
        return {
            "success": result.returncode == 0,
            "product_id": product_id,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка запуска парсера: {str(e)}")

@router.post("/parse-batch")
async def parse_batch(count: int = 10, use_selenium: bool = True):
    """Пакетный парсинг товаров"""
    try:
        script_path = Path(config.PARSER_SCRIPTS['process_products'])
        
        cmd = [
            "python", str(script_path),
            "--process", str(count),
            "--selenium" if use_selenium else "--fast-mode"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=script_path.parent
        )
        
        return {
            "success": result.returncode == 0,
            "count": count,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка запуска парсера: {str(e)}")

@router.post("/stats")
async def update_stats():
    """Запуск скрипта статистики"""
    try:
        script_path = Path(config.PARSER_SCRIPTS['process_products'])
        
        result = subprocess.run(
            ["python", str(script_path), "--stats"],
            capture_output=True,
            text=True,
            cwd=script_path.parent
        )
        
        return {
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")