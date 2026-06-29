from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas, auth
from datetime import date

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user

@router.put("/me", response_model=schemas.UserResponse)
async def update_users_me(
        user_update: schemas.UserUpdate,
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    update_data = user_update.model_dump(exclude_unset=True)

    # Обновляем поля
    for key, value in update_data.items():
        setattr(current_user, key, value)

    # Вычисляем возраст, если указана дата рождения
    if current_user.birth_date:
        today = date.today()
        current_user.age = today.year - current_user.birth_date.year - (
                (today.month, today.day) < (current_user.birth_date.month, current_user.birth_date.day)
        )

    db.commit()
    db.refresh(current_user)
    return current_user

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_users_me(
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    db.delete(current_user)
    db.commit()
    return

@router.get("/{user_id}", response_model=schemas.UserResponse)
async def get_public_user_profile(
        user_id: str,
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_active_user) # Любой авторизованный может смотреть
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Проверяем, публичный ли профиль или это сам пользователь или админ
    if not user.is_public and current_user.id != user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Profile is private")
    return user