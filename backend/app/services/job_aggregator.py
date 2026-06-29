# backend/app/services/job_aggregator.py
from typing import List, Dict, Any
import random

def get_aggregated_jobs() -> List[Dict[str, Any]]:
    """
    Заглушка для агрегатора вакансий.
    В реальном проекте здесь будет парсинг API HeadHunter, Astana Hub и др.
    """
    # Базовый список вакансий
    jobs = [
        {
            "title": "Frontend-разработчик (React)",
            "company": "TechCorp KZ",
            "description": "Разработка интерфейсов для веб-приложений. Требуется знание React, TypeScript, CSS.",
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
            "title": "Видеомонтажер",
            "company": "Media Production",
            "description": "Монтаж видео для YouTube и социальных сетей. Знание Adobe Premiere Pro.",
            "link": "https://example.com/job/4",
            "source": "Партнерская площадка",
            "location": "Удаленно",
            "category": "video",
            "employment_type": "project"
        },
        {
            "title": "Копирайтер",
            "company": "Content Agency",
            "description": "Написание статей и постов для социальных сетей. Грамотность и креативность.",
            "link": "https://example.com/job/5",
            "source": "HeadHunter",
            "location": "Алматы",
            "category": "copywriting",
            "employment_type": "part_time"
        },
        {
            "title": "Backend-разработчик (Python)",
            "company": "Startup Hub",
            "description": "Разработка API на Django/FastAPI. Опыт работы с PostgreSQL.",
            "link": "https://example.com/job/6",
            "source": "Astana Hub",
            "location": "Астана",
            "category": "development",
            "employment_type": "full_time"
        },
        {
            "title": "Графический дизайнер",
            "company": "Branding Agency",
            "description": "Разработка логотипов, брендбуков, полиграфии. Знание Adobe Illustrator.",
            "link": "https://example.com/job/7",
            "source": "Ручное добавление",
            "location": "Актау",
            "category": "design",
            "employment_type": "project"
        },
        {
            "title": "Специалист по контекстной рекламе",
            "company": "Digital Marketing",
            "description": "Настройка и ведение рекламных кампаний в Яндекс.Директ и Google Ads.",
            "link": "https://example.com/job/8",
            "source": "HeadHunter",
            "location": "Удаленно",
            "category": "smm",
            "employment_type": "full_time"
        },
        {
            "title": "Fullstack-разработчик",
            "company": "IT Company",
            "description": "Разработка веб-приложений на React + Node.js. Полный цикл разработки.",
            "link": "https://example.com/job/9",
            "source": "Astana Hub",
            "location": "Алматы",
            "category": "development",
            "employment_type": "full_time"
        },
        {
            "title": "Motion-дизайнер",
            "company": "Video Production",
            "description": "Создание анимации и моушн-графики для рекламных роликов.",
            "link": "https://example.com/job/10",
            "source": "Партнерская площадка",
            "location": "Астана",
            "category": "video",
            "employment_type": "project"
        }
    ]

    # Добавляем немного разнообразия (перемешиваем)
    random.shuffle(jobs)
    return jobs[:20]  # Возвращаем до 20 вакансий


def fetch_jobs_from_api(api_name: str) -> List[Dict[str, Any]]:
    """
    Заглушка для получения вакансий из конкретного API.
    В реальности здесь будут запросы к внешним API.
    """
    # Имитация получения данных из разных источников
    if api_name == "headhunter":
        return [
            {
                "title": "Python Developer",
                "company": "Tech Company",
                "description": "Разработка бэкенда на Python",
                "link": "https://hh.kz/vacancy/123",
                "source": "HeadHunter",
                "location": "Алматы",
                "category": "development",
                "employment_type": "full_time"
            }
        ]
    elif api_name == "astana_hub":
        return [
            {
                "title": "UX Researcher",
                "company": "Astana Hub",
                "description": "Исследование пользовательского опыта",
                "link": "https://astanahub.com/job/456",
                "source": "Astana Hub",
                "location": "Астана",
                "category": "design",
                "employment_type": "project"
            }
        ]
    return []


def get_jobs_by_category(category: str) -> List[Dict[str, Any]]:
    """Получить вакансии по категории"""
    all_jobs = get_aggregated_jobs()
    return [job for job in all_jobs if job.get('category') == category]


def get_jobs_by_location(location: str) -> List[Dict[str, Any]]:
    """Получить вакансии по городу"""
    all_jobs = get_aggregated_jobs()
    return [job for job in all_jobs if job.get('location') == location]


def search_jobs(query: str) -> List[Dict[str, Any]]:
    """Поиск вакансий по ключевым словам"""
    all_jobs = get_aggregated_jobs()
    query_lower = query.lower()
    results = []
    for job in all_jobs:
        if (query_lower in job.get('title', '').lower() or
                query_lower in job.get('description', '').lower() or
                query_lower in job.get('company', '').lower()):
            results.append(job)
    return results