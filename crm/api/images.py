# hello54_crm/api/images.py
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException
from utils import config

router = APIRouter()

@router.post("/download/{product_id}")
async def download_product_image(product_id: int):
    """Загрузка изображения для конкретного товара"""
    try:
        script_path = Path(config.PARSER_SCRIPTS['save_img'])
        
        result = subprocess.run(
            ["python", str(script_path), "--id", str(product_id)],
            capture_output=True,
            text=True,
            cwd=script_path.parent
        )
        
        return {
            "success": result.returncode == 0,
            "product_id": product_id,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки изображения: {str(e)}")

@router.post("/download-batch")
async def download_batch_images(count: int = 10):
    """Пакетная загрузка изображений"""
    try:
        script_path = Path(config.PARSER_SCRIPTS['save_img'])
        
        result = subprocess.run(
            ["python", str(script_path), "--limit", str(count)],
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
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки изображений: {str(e)}")