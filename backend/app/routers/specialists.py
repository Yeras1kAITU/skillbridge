from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas, auth

router = APIRouter(prefix="/specialists", tags=["specialists"])

@router.get("/", response_model=List[schemas.UserResponse])
async def get_specialists(
        db: Session = Depends(auth.get_db),
        category: Optional[str] = Query(None, description="Фильтр по категории навыков"),
        city: Optional[str] = Query(None, description="Фильтр по городу"),
        experience_level: Optional[str] = Query(None, description="Фильтр по уровню опыта"),
        current_user: Optional[models.User] = Depends(auth.get_current_active_user) # Авторизация не обязательна, но если есть, то хорошо
):
    query = db.query(models.User).filter(models.User.is_public == True)

    if city:
        query = query.filter(models.User.city == city)
    if experience_level:
        query = query.filter(models.User.experience_level == experience_level)

    # Сложная фильтрация по категориям навыков (через связь)
    if category:
        # Находим пользователей, у которых есть навык с этой категорией (упрощенно)
        # Для реального поиска нужно JOIN с таблицей Skills
        # В MVP делаем упрощенный вариант: фильтруем по about или по названию навыка через подзапрос
        subquery = db.query(models.Skill.user_id).filter(models.Skill.skill_name.ilike(f"%{category}%"))
        query = query.filter(models.User.id.in_(subquery))

    users = query.limit(50).all()
    return users

@router.get("/{user_id}", response_model=schemas.UserResponse)
async def get_specialist_profile(
        user_id: str,
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.is_public == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="Specialist not found or profile is private")
    return user

@router.post("/publish", response_model=schemas.UserResponse)
async def publish_profile(
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    current_user.is_public = True
    db.commit()
    db.refresh(current_user)
    return current_user