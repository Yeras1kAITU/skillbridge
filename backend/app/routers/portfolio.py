import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=schemas.PortfolioItemResponse)
async def upload_portfolio_item(
        title: str = Form(...),
        description: str = Form(None),
        category: str = Form(None),
        is_public: bool = Form(False),
        file: UploadFile = File(...),
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    # Валидация типа файла и размера (100MB)
    if file.size > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 100MB)")

    # Генерация безопасного имени файла
    file_extension = os.path.splitext(file.filename)[1]
    safe_filename = f"{current_user.id}_{title}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    # Сохранение файла
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")

    # Создание записи в БД
    db_item = models.Portfolio(
        user_id=current_user.id,
        title=title,
        description=description,
        file_path=file_path,
        category=category,
        is_public=is_public
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/", response_model=List[schemas.PortfolioItemResponse])
async def get_portfolio_items(
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    items = db.query(models.Portfolio).filter(models.Portfolio.user_id == current_user.id).all()
    return items

@router.get("/{item_id}", response_model=schemas.PortfolioItemResponse)
async def get_portfolio_item(
        item_id: str,
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    item = db.query(models.Portfolio).filter(models.Portfolio.id == item_id).first()
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.put("/{item_id}", response_model=schemas.PortfolioItemResponse)
async def update_portfolio_item(
        item_id: str,
        item_update: schemas.PortfolioItemUpdate,
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    item = db.query(models.Portfolio).filter(models.Portfolio.id == item_id).first()
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Item not found")
    for key, value in item_update.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio_item(
        item_id: str,
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    item = db.query(models.Portfolio).filter(models.Portfolio.id == item_id).first()
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Item not found")
    # Удаление файла
    if os.path.exists(item.file_path):
        os.remove(item.file_path)
    db.delete(item)
    db.commit()
    return