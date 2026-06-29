from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func  # <-- ДОБАВЬТЕ ЭТОТ ИМПОРТ
from typing import List, Optional
from .. import models, schemas, auth
from ..services.hh_parser import fetch_hh_vacancies
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])

# Кэш для статуса синхронизации
_sync_status = {
    "last_sync": None,
    "total_jobs": 0,
    "is_syncing": False
}


# ==================== СПЕЦИФИЧЕСКИЕ РОУТЫ ====================

@router.get("/sync-status")
async def get_sync_status(
    db: Session = Depends(auth.get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_active_user)
):
    """
    Статус вакансий в базе
    """
    total_jobs = db.query(models.Job).count()
    
    # Получаем количество по источникам
    hh_jobs = db.query(models.Job).filter(models.Job.source == "HeadHunter").count()
    manual_jobs = db.query(models.Job).filter(models.Job.source == "Ручное добавление").count()
    
    # Получаем количество по категориям - ИСПРАВЛЕНО
    categories = db.query(
        models.Job.category, 
        func.count(models.Job.id)  # <-- ИСПОЛЬЗУЕМ func ИЗ sqlalchemy
    ).group_by(models.Job.category).all()
    
    # Получаем последние 5 добавленных вакансий
    recent_jobs = db.query(models.Job).order_by(
        models.Job.created_at.desc()
    ).limit(5).all()
    
    return {
        "total_jobs": total_jobs,
        "by_source": {
            "HeadHunter": hh_jobs,
            "Manual": manual_jobs
        },
        "by_category": {cat[0]: cat[1] for cat in categories if cat[0]},
        "last_sync": _sync_status["last_sync"],
        "is_syncing": _sync_status["is_syncing"],
        "recent_jobs": [
            {
                "title": job.title,
                "company": job.company,
                "source": job.source,
                "created_at": job.created_at
            }
            for job in recent_jobs
        ]
    }


@router.post("/sync-hh")
async def sync_headhunter_vacancies(
    background_tasks: BackgroundTasks,
    keywords: Optional[str] = Query(None, description="Ключевые слова для поиска (через запятую)"),
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    """
    Ручная синхронизация вакансий с HeadHunter (только для администраторов)
    """
    if _sync_status["is_syncing"]:
        raise HTTPException(status_code=409, detail="Синхронизация уже выполняется")
    
    if keywords:
        keywords_list = [k.strip() for k in keywords.split(",")]
    else:
        keywords_list = [
            "разработчик", "дизайнер", "smm", "маркетолог", "аналитик",
            "видеомонтаж", "копирайтер", "менеджер проектов", "qa", "devops",
            "программист", "frontend", "backend", "fullstack", "ui/ux",
            "контент-менеджер", "product manager", "data analyst"
        ]
    
    _sync_status["is_syncing"] = True
    
    async def run_sync():
        try:
            result = await fetch_hh_vacancies(db, keywords_list)
            _sync_status["last_sync"] = datetime.now()
            _sync_status["total_jobs"] = db.query(models.Job).count()
            logger.info(f"Ручная синхронизация завершена: {result}")
        except Exception as e:
            logger.error(f"Ошибка синхронизации: {e}")
        finally:
            _sync_status["is_syncing"] = False
    
    background_tasks.add_task(run_sync)
    
    return {
        "message": "Синхронизация с HeadHunter запущена",
        "keywords": keywords_list,
        "status": "processing",
        "total_jobs": db.query(models.Job).count()
    }


@router.get("/categories", response_model=List[str])
async def get_categories(
    db: Session = Depends(auth.get_db)
):
    """
    Получение списка всех категорий вакансий
    """
    categories = db.query(models.Job.category).distinct().all()
    return [cat[0] for cat in categories if cat[0] if cat[0]]


@router.get("/locations", response_model=List[str])
async def get_locations(
    db: Session = Depends(auth.get_db)
):
    """
    Получение списка всех городов
    """
    locations = db.query(models.Job.location).distinct().all()
    return [loc[0] for loc in locations if loc[0] if loc[0]]


@router.post("/add-manual")
async def add_manual_job(
    job_data: dict,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    """
    Ручное добавление вакансии администратором
    """
    required_fields = ["title", "company", "description"]
    for field in required_fields:
        if field not in job_data:
            raise HTTPException(status_code=400, detail=f"Поле '{field}' обязательно")
    
    job = models.Job(
        id=str(uuid.uuid4()),
        title=job_data["title"][:255],
        company=job_data["company"][:255],
        description=job_data["description"],
        link=job_data.get("link"),
        source="Ручное добавление",
        location=job_data.get("location", "Не указан"),
        category=job_data.get("category", "other"),
        employment_type=job_data.get("employment_type", "full_time")
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return {
        "message": "Вакансия добавлена",
        "job": job
    }


@router.get("/stats/quick")
async def get_quick_stats(
    db: Session = Depends(auth.get_db)
):
    """
    Быстрая статистика для виджета на главной
    """
    total_jobs = db.query(models.Job).count()
    total_categories = db.query(models.Job.category).distinct().count()
    
    # Топ-3 категории по количеству вакансий - ИСПРАВЛЕНО
    top_categories = db.query(
        models.Job.category,
        func.count(models.Job.id).label("count")  # <-- ИСПОЛЬЗУЕМ func ИЗ sqlalchemy
    ).group_by(models.Job.category).order_by(
        func.count(models.Job.id).desc()  # <-- ИСПОЛЬЗУЕМ func ИЗ sqlalchemy
    ).limit(3).all()
    
    return {
        "total_jobs": total_jobs,
        "total_categories": total_categories,
        "top_categories": [
            {"category": cat[0] or "other", "count": cat[1]}
            for cat in top_categories
        ]
    }


# ==================== ДИНАМИЧЕСКИЕ РОУТЫ ====================

@router.get("/", response_model=List[schemas.JobResponse])
async def get_jobs(
    db: Session = Depends(auth.get_db),
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    location: Optional[str] = Query(None, description="Фильтр по городу"),
    employment_type: Optional[str] = Query(None, description="Тип занятости"),
    search: Optional[str] = Query(None, description="Поиск по ключевым словам"),
    source: Optional[str] = Query(None, description="Источник вакансии"),
    limit: int = Query(50, ge=1, le=200, description="Количество результатов"),
    skip: int = Query(0, ge=0, description="Смещение для пагинации"),
    current_user: Optional[models.User] = Depends(auth.get_current_active_user)
):
    """
    Получение списка вакансий с фильтрацией и пагинацией
    """
    # Автоматически синхронизируем, если база пустая или старая (> 24 часа)
    db_count = db.query(models.Job).count()
    
    # Если вакансий меньше 20 или последняя синхронизация была > 24 часа назад
    if db_count < 20 or (_sync_status["last_sync"] and 
        (datetime.now() - _sync_status["last_sync"]).total_seconds() > 86400):
        
        if not _sync_status["is_syncing"]:
            logger.info("Запуск автоматической синхронизации вакансий")
            _sync_status["is_syncing"] = True
            try:
                # Запускаем синхронизацию в фоновом режиме
                result = await fetch_hh_vacancies(db)
                _sync_status["last_sync"] = datetime.now()
                _sync_status["total_jobs"] = db.query(models.Job).count()
                logger.info(f"Синхронизация завершена: {result}")
            except Exception as e:
                logger.error(f"Ошибка синхронизации: {e}")
            finally:
                _sync_status["is_syncing"] = False

    # Строим запрос с фильтрацией
    query = db.query(models.Job)
    
    if category:
        query = query.filter(models.Job.category == category)
    if location:
        query = query.filter(models.Job.location.ilike(f"%{location}%"))
    if employment_type:
        query = query.filter(models.Job.employment_type == employment_type)
    if source:
        query = query.filter(models.Job.source == source)
    if search:
        query = query.filter(
            models.Job.title.ilike(f"%{search}%") |
            models.Job.description.ilike(f"%{search}%") |
            models.Job.company.ilike(f"%{search}%")
        )
    
    # Пагинация
    jobs = query.offset(skip).limit(limit).all()
    return jobs


@router.get("/recommended", response_model=List[schemas.RecommendationResponse])
async def get_recommended_jobs(
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Получение рекомендованных вакансий на основе навыков пользователя
    """
    # Получаем навыки пользователя
    user_skills = db.query(models.Skill).filter(
        models.Skill.user_id == current_user.id
    ).all()
    
    skill_names = [skill.skill_name.lower() for skill in user_skills]
    
    # Если навыков нет, возвращаем популярные вакансии
    if not skill_names:
        popular_jobs = db.query(models.Job).limit(limit).all()
        recommendations = []
        for job in popular_jobs:
            rec = models.Recommendation(
                user_id=current_user.id,
                job_id=job.id,
                relevance_score=0.5
            )
            db.add(rec)
            recommendations.append(rec)
        db.commit()
        return recommendations
    
    # Ищем вакансии, которые соответствуют навыкам
    scored_jobs = {}
    
    for skill in skill_names:
        keywords = skill.split()
        for keyword in keywords:
            if len(keyword) < 3:
                continue
            
            jobs = db.query(models.Job).filter(
                models.Job.title.ilike(f"%{keyword}%") |
                models.Job.description.ilike(f"%{keyword}%")
            ).all()
            
            for job in jobs:
                if job.id not in scored_jobs:
                    scored_jobs[job.id] = {
                        "job": job,
                        "score": 0,
                        "matched_skills": []
                    }
                scored_jobs[job.id]["score"] += 0.3
                scored_jobs[job.id]["matched_skills"].append(keyword)
    
    # Сортируем по релевантности
    sorted_jobs = sorted(
        scored_jobs.values(),
        key=lambda x: x["score"],
        reverse=True
    )[:limit]
    
    # Создаем рекомендации
    for item in sorted_jobs:
        job = item["job"]
        score = min(item["score"], 1.0)
        
        existing_rec = db.query(models.Recommendation).filter(
            models.Recommendation.user_id == current_user.id,
            models.Recommendation.job_id == job.id
        ).first()
        
        if not existing_rec:
            rec = models.Recommendation(
                user_id=current_user.id,
                job_id=job.id,
                relevance_score=score
            )
            db.add(rec)
    
    db.commit()
    
    recommendations = db.query(models.Recommendation).filter(
        models.Recommendation.user_id == current_user.id
    ).order_by(
        models.Recommendation.relevance_score.desc()
    ).limit(limit).all()
    
    return recommendations


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    """
    Удаление вакансии администратором
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")
    
    db.delete(job)
    db.commit()
    
    return {"message": "Вакансия удалена"}


@router.get("/{job_id}", response_model=schemas.JobResponse)
async def get_job(
    job_id: str,
    db: Session = Depends(auth.get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_active_user)
):
    """
    Получение конкретной вакансии по ID
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")
    return job