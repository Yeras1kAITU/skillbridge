import os
import json
from groq import Groq
from sqlalchemy.orm import Session
from .. import models

# Настройка клиента Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def analyze_portfolio_with_groq(user_id: str, db: Session):
    """
    Анализ портфолио с использованием Groq API (бесплатно, быстро)
    """
    # Получаем портфолио пользователя
    portfolio_items = db.query(models.Portfolio).filter(
        models.Portfolio.user_id == user_id
    ).all()

    if not portfolio_items:
        return {
            "strengths": ["Загрузите материалы для анализа"],
            "weaknesses": ["Нет материалов в портфолио"],
            "recommendations": ["Загрузите хотя бы одну работу, чтобы получить анализ."],
            "suggested_services": []
        }

    # Формируем текст портфолио для анализа
    portfolio_text = "Вот портфолио пользователя:\n"
    for item in portfolio_items:
        portfolio_text += f"- Название: {item.title}\n"
        portfolio_text += f"  Описание: {item.description or 'Нет описания'}\n"
        portfolio_text += f"  Категория: {item.category or 'Не указана'}\n\n"

    # Промпт для Groq
    prompt = f"""
    Ты — опытный карьерный консультант и аналитик портфолио.
    Проанализируй следующее портфолио пользователя:

    {portfolio_text}

    На основе этого анализа, предоставь ответ строго в формате JSON с четырьмя ключами:
    1. "strengths": Список сильных сторон пользователя (3-5 пунктов). 
       Будь конкретным: какие навыки явно видны из работ?
    2. "weaknesses": Список слабых сторон или пробелов в портфолио (2-3 пункта).
       Что можно улучшить? Каких работ не хватает?
    3. "recommendations": Список конкретных рекомендаций по улучшению портфолио и развитию навыков (3-4 пункта).
       Дай практические советы.
    4. "suggested_services": Список услуг, которые пользователь может предлагать на рынке (3-4 пункта).
       Исходя из его текущих навыков.

    Ответ должен содержать только JSON, без дополнительного текста.
    """

    try:
        # Отправляем запрос к Groq
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Бесплатная и быстрая модель
            # Альтернативы: "llama3-70b-8192", "gemma2-9b-it", "llama-3.1-70b-versatile"
            messages=[
                {"role": "system", "content": "Ты эксперт по анализу портфолио. Отвечай только JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1024,
            response_format={"type": "json_object"}  # Гарантирует JSON ответ
        )

        result_text = response.choices[0].message.content

        # Парсим JSON
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            # Если JSON не распарсился, пробуем найти JSON в тексте
            start_idx = result_text.find('{')
            end_idx = result_text.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = result_text[start_idx:end_idx]
                result = json.loads(json_str)
            else:
                raise ValueError("Модель вернула ответ не в формате JSON")

        # Сохраняем в БД
        analysis = models.AIAnalysis(
            user_id=user_id,
            strengths=result.get("strengths", []),
            weaknesses=result.get("weaknesses", []),
            recommendations=result.get("recommendations", []),
            suggested_services=result.get("suggested_services", [])
        )
        db.add(analysis)

        # Сохраняем навыки в таблицу Skills
        all_skills = result.get("strengths", []) + result.get("weaknesses", [])
        for skill_text in all_skills:
            # Извлекаем название навыка
            skill_name = skill_text.split(':')[0].split(',')[0].strip()
            if len(skill_name) > 3 and len(skill_name) < 100:
                existing = db.query(models.Skill).filter(
                    models.Skill.user_id == user_id,
                    models.Skill.skill_name == skill_name,
                    models.Skill.source == "ai_analysis"
                ).first()
                if not existing:
                    new_skill = models.Skill(
                        user_id=user_id,
                        skill_name=skill_name[:100],
                        level="Средний",
                        source="ai_analysis"
                    )
                    db.add(new_skill)

        db.commit()
        return result

    except Exception as e:
        print(f"Ошибка при работе с Groq API: {e}")
        # В случае ошибки возвращаем базовый анализ
        return {
            "strengths": ["Не удалось выполнить анализ. Проверьте API ключ и интернет."],
            "weaknesses": ["Попробуйте позже."],
            "recommendations": ["Убедитесь, что API-ключ верный и портфолио содержит описания."],
            "suggested_services": []
        }