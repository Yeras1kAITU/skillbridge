from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas, auth
from ..services.job_aggregator import get_aggregated_jobs
from ..services.hh_parser import fetch_hh_vacancies
import uuid  # <-- ДОБАВЬТЕ ЭТОТ ИМПОРТ
import asyncio

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Заглушка для агрегатора (оставляем для обратной совместимости)
def aggregate_jobs_from_sources():
    # В реальном проекте здесь был бы парсинг API
    return [
        {
            "title": "Frontend-разработчик (React)",
            "company": "TechCorp KZ",
            "description": "Разработка интерфейсов для веб-приложений. Требуется знание React, TypeScript.",
            "link": "https://example.com/job/1",
            "source": "HeadHunter",
            "location": "Алматы",
            "category": "development",
            "employment_type": "full_time"
        },
        {
            "title": "UI/UX Дизайнер",
            "company": "Design Studio",
            "description": "Создание макетов для мобильных приложений. Опыт работы с Figma обязателен.",
            "link": "https://example.com/job/2",
            "source": "Astana Hub",
            "location": "Астана",
            "category": "design",
            "employment_type": "project"
        },
        {
            "title": "SMM-менеджер",
            "company": "Local Business",
            "description": "Ведение социальных сетей, создание контента, настройка таргета.",
            "link": "https://example.com/job/3",
            "source": "Ручное добавление",
            "location": "Актау",
            "category": "smm",
            "employment_type": "part_time"
        },
        {
            "title": "Backend-разработчик (Python)",
            "company": "Startup Hub",
            "description": "Разработка API на Django/FastAPI. Опыт работы с PostgreSQL.",
            "link": "https://example.com/job/4",
            "source": "Astana Hub",
            "location": "Астана",
            "category": "development",
            "employment_type": "full_time"
        },
        {
            "title": "Графический дизайнер",
            "company": "Branding Agency",
            "description": "Разработка логотипов, брендбуков, полиграфии. Знание Adobe Illustrator.",
            "link": "https://example.com/job/5",
            "source": "Ручное добавление",
            "location": "Актау",
            "category": "design",
            "employment_type": "project"
        },
        {
            "title": "Motion-дизайнер",
            "company": "Video Production",
            "description": "Создание анимации и моушн-графики для рекламных роликов.",
            "link": "https://example.com/job/6",
            "source": "Партнерская площадка",
            "location": "Астана",
            "category": "video",
            "employment_type": "project"
        },
        {
            "title": "Специалист по контекстной рекламе",
            "company": "Digital Marketing",
            "description": "Настройка и ведение рекламных кампаний в Яндекс.Директ и Google Ads.",
            "link": "https://example.com/job/7",
            "source": "HeadHunter",
            "location": "Удаленно",
            "category": "smm",
            "employment_type": "full_time"
        },
        {
            "title": "Fullstack-разработчик",
            "company": "IT Company",
            "description": "Разработка веб-приложений на React + Node.js. Полный цикл разработки.",
            "link": "https://example.com/job/8",
            "source": "Astana Hub",
            "location": "Алматы",
            "category": "development",
            "employment_type": "full_time"
        }
    ]


@router.get("/", response_model=List[schemas.JobResponse])
async def get_jobs(
        db: Session = Depends(auth.get_db),
        category: Optional[str] = Query(None, description="Фильтр по категории"),
        location: Optional[str] = Query(None, description="Фильтр по городу"),
        employment_type: Optional[str] = Query(None, description="Тип занятости"),
        search: Optional[str] = Query(None, description="Поиск по ключевым словам"),
        source: Optional[str] = Query(None, description="Источник вакансии"),
        limit: int = Query(100, ge=1, le=200, description="Количество результатов"),
        skip: int = Query(0, ge=0, description="Смещение для пагинации"),
        current_user: Optional[models.User] = Depends(auth.get_current_active_user)
):
    """
    Получение списка вакансий с фильтрацией и пагинацией
    """
    # 1. Получаем агрегированные вакансии из внешних источников (только если база пустая)
    db_count = db.query(models.Job).count()
    if db_count < 10:
        external_jobs = aggregate_jobs_from_sources()
        for job_data in external_jobs:
            existing_job = db.query(models.Job).filter(
                models.Job.title == job_data["title"],
                models.Job.company == job_data.get("company")
            ).first()
            if not existing_job:
                # ЯВНО СОЗДАЁМ ОБЪЕКТ С UUID
                new_job = models.Job(
                    id=str(uuid.uuid4()),  # <-- ЯВНО ГЕНЕРИРУЕМ UUID
                    title=job_data["title"],
                    company=job_data.get("company"),
                    description=job_data.get("description"),
                    link=job_data.get("link"),
                    source=job_data.get("source"),
                    location=job_data.get("location"),
                    category=job_data.get("category"),
                    employment_type=job_data.get("employment_type")
                )
                db.add(new_job)
        db.commit()

    # 2. Строим запрос с фильтрацией
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

    # 3. Пагинация
    jobs = query.offset(skip).limit(limit).all()
    return jobs


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


@router.get("/recommended", response_model=List[schemas.RecommendationResponse])
async def get_recommended_jobs(
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_active_user),
        limit: int = Query(20, ge=1, le=50)
):
    """
    Получение рекомендованных вакансий на основе навыков пользователя
    """
    # 1. Получаем навыки пользователя (из AI-анализа и ручных)
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

    # 2. Ищем вакансии, которые соответствуют навыкам
    recommended_jobs = []
    scored_jobs = {}

    for skill in skill_names:
        # Разбиваем навык на ключевые слова
        keywords = skill.split()
        for keyword in keywords:
            if len(keyword) < 3:
                continue

            jobs = db.query(models.Job).filter(
                models.Job.title.ilike(f"%{keyword}%") |
                models.Job.description.ilike(f"%{keyword}%") |
                models.Job.company.ilike(f"%{keyword}%")
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

    # 3. Сортируем по релевантности
    sorted_jobs = sorted(
        scored_jobs.values(),
        key=lambda x: x["score"],
        reverse=True
    )[:limit]

    # 4. Создаем рекомендации
    for item in sorted_jobs:
        job = item["job"]
        score = min(item["score"], 1.0)  # Нормализуем до 1.0

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
            recommended_jobs.append(rec)

    db.commit()

    # 5. Возвращаем список рекомендаций
    recommendations = db.query(models.Recommendation).filter(
        models.Recommendation.user_id == current_user.id
    ).order_by(
        models.Recommendation.relevance_score.desc()
    ).limit(limit).all()

    return recommendations


@router.get("/categories", response_model=List[str])
async def get_categories(
        db: Session = Depends(auth.get_db)
):
    """
    Получение списка всех категорий вакансий
    """
    categories = db.query(models.Job.category).distinct().all()
    return [cat[0] for cat in categories if cat[0]]


@router.get("/locations", response_model=List[str])
async def get_locations(
        db: Session = Depends(auth.get_db)
):
    """
    Получение списка всех городов
    """
    locations = db.query(models.Job.location).distinct().all()
    return [loc[0] for loc in locations if loc[0]]


@router.post("/sync-hh")
async def sync_headhunter_vacancies(
        background_tasks: BackgroundTasks,
        keywords: Optional[str] = Query(None, description="Ключевые слова для поиска (через запятую)"),
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_admin_user)
):
    """
    Синхронизация вакансий с HeadHunter (только для администраторов)
    """
    if keywords:
        keywords_list = [k.strip() for k in keywords.split(",")]
    else:
        keywords_list = ["разработчик", "дизайнер", "smm", "маркетолог", "аналитик", "видеомонтаж"]

    background_tasks.add_task(fetch_hh_vacancies, db, keywords_list)

    return {
        "message": "Синхронизация с HeadHunter запущена",
        "keywords": keywords_list,
        "status": "processing"
    }


@router.get("/sync-status")
async def get_sync_status(
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_admin_user)
):
    """
    Статус вакансий в базе (только для администраторов)
    """
    total_jobs = db.query(models.Job).count()
    hh_jobs = db.query(models.Job).filter(models.Job.source == "HeadHunter").count()
    astana_hub_jobs = db.query(models.Job).filter(models.Job.source == "Astana Hub").count()
    manual_jobs = db.query(models.Job).filter(models.Job.source == "Ручное добавление").count()

    categories = db.query(models.Job.category, db.func.count(models.Job.id)).group_by(models.Job.category).all()

    return {
        "total_jobs": total_jobs,
        "by_source": {
            "HeadHunter": hh_jobs,
            "Astana Hub": astana_hub_jobs,
            "Manual": manual_jobs
        },
        "by_category": {cat[0]: cat[1] for cat in categories if cat[0]},
        "last_sync": "Автоматически при запросе"
    }