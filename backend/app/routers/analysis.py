from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth
from ..services.groq_analyzer import analyze_portfolio_with_groq  # <-- Заменили на groq

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.post("/", response_model=schemas.AIAnalysisResponse)
async def run_analysis(
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    # Проверяем, есть ли портфолио
    portfolio_count = db.query(models.Portfolio).filter(
        models.Portfolio.user_id == current_user.id
    ).count()

    if portfolio_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Загрузите хотя бы один материал в портфолио для анализа."
        )

    # Запускаем анализ через Groq
    result = analyze_portfolio_with_groq(current_user.id, db)

    # Получаем последний сохраненный анализ
    latest_analysis = db.query(models.AIAnalysis).filter(
        models.AIAnalysis.user_id == current_user.id
    ).order_by(models.AIAnalysis.created_at.desc()).first()

    if not latest_analysis:
        raise HTTPException(status_code=500, detail="Не удалось сохранить результаты анализа.")

    return latest_analysis

@router.get("/", response_model=List[schemas.AIAnalysisResponse])
async def get_analysis_results(
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    analyses = db.query(models.AIAnalysis).filter(
        models.AIAnalysis.user_id == current_user.id
    ).order_by(models.AIAnalysis.created_at.desc()).all()
    return analyses

@router.get("/competencies", response_model=schemas.AIAnalysisResponse)
async def get_competency_card(
        db: Session = Depends(auth.get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    latest_analysis = db.query(models.AIAnalysis).filter(
        models.AIAnalysis.user_id == current_user.id
    ).order_by(models.AIAnalysis.created_at.desc()).first()

    if not latest_analysis:
        raise HTTPException(
            status_code=404,
            detail="Анализ не найден. Запустите анализ портфолио."
        )

    return latest_analysis