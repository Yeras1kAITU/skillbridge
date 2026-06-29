import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth
from ..services.cloudinary_storage import upload_portfolio_file, delete_portfolio_file

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

    file_content = await file.read()
    upload_result = upload_portfolio_file(
        file_content,
        current_user.id,
        title,
        category or "other"
    )

    if not upload_result:
        raise HTTPException(status_code=500, detail="Failed to upload to Cloudinary")

    # Create database record with Cloudinary URL
    db_item = models.Portfolio(
        user_id=current_user.id,
        title=title,
        description=description,
        file_path=upload_result["url"],  # Store Cloudinary URL
        category=category,
        is_public=is_public,
        cloudinary_public_id=upload_result["public_id"]  # Store for deletion
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

    # Delete from Cloudinary
    if hasattr(item, 'cloudinary_public_id') and item.cloudinary_public_id:
        delete_portfolio_file(item.cloudinary_public_id)

    db.delete(item)
    db.commit()
    return