import aiohttp
import asyncio
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from .. import models

class HeadHunterParser:
    """Парсер вакансий с HeadHunter API"""

    BASE_URL = "https://api.hh.ru"

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def search_vacancies(
            self,
            text: str = "",
            area: int = 160,  # Казахстан
            per_page: int = 20,
            page: int = 0,
            currency: str = "KZT"
    ) -> List[Dict[str, Any]]:
        """
        Поиск вакансий на HeadHunter

        Параметры:
        - text: ключевые слова для поиска
        - area: регион (160 - Казахстан)
        - per_page: количество на странице
        - page: номер страницы
        """
        url = f"{self.BASE_URL}/vacancies"

        params = {
            "text": text,
            "area": area,
            "per_page": per_page,
            "page": page,
            "currency": currency
        }

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_vacancies(data.get("items", []))
                else:
                    print(f"Ошибка HeadHunter API: {response.status}")
                    return []
        except Exception as e:
            print(f"Ошибка при запросе к HeadHunter: {e}")
            return []

    def _parse_vacancies(self, items: List[Dict]) -> List[Dict[str, Any]]:
        """Парсинг данных о вакансиях"""
        parsed = []
        for item in items:
            # Извлекаем зарплату
            salary = item.get("salary")
            salary_text = ""
            if salary:
                salary_text = f"{salary.get('from', '')} {salary.get('to', '')} {salary.get('currency', '')}"

            # Извлекаем город
            city = "Не указан"
            if item.get("area"):
                city = item["area"].get("name", "Не указан")

            # Извлекаем требования
            requirements = []
            if item.get("snippet"):
                requirements.append(item["snippet"].get("requirement", ""))

            parsed.append({
                "title": item.get("name", "Без названия"),
                "company": item.get("employer", {}).get("name", "Не указана"),
                "description": f"{item.get('description', '')} {' '.join(requirements)}",
                "link": item.get("alternate_url", ""),
                "source": "HeadHunter",
                "location": city,
                "category": self._detect_category(item.get("name", ""), item.get("description", "")),
                "employment_type": self._detect_employment_type(item),
                "salary": salary_text,
                "created_at": datetime.now().isoformat()
            })

        return parsed

    def _detect_category(self, title: str, description: str) -> str:
        """Определение категории вакансии"""
        text = f"{title} {description}".lower()

        categories = {
            "development": ["разработчик", "developer", "программист", "backend", "frontend", "fullstack", "python", "java"],
            "design": ["дизайнер", "designer", "ui", "ux", "графический", "веб-дизайн"],
            "smm": ["smm", "маркетолог", "маркетинг", "social media", "таргетолог"],
            "video": ["видео", "video", "монтаж", "оператор", "режиссер"],
            "copywriting": ["копирайтер", "copywriter", "редактор", "журналист", "контент"],
            "analytics": ["аналитик", "analyst", "data", "big data"]
        }

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text:
                    return category

        return "other"

    def _detect_employment_type(self, item: Dict) -> str:
        """Определение типа занятости"""
        employment = item.get("employment", {})
        if employment:
            name = employment.get("name", "").lower()
            if "полный" in name or "full" in name:
                return "full_time"
            elif "частич" in name or "part" in name:
                return "part_time"
            elif "проект" in name or "project" in name:
                return "project"

        return "full_time"


async def fetch_hh_vacancies(db: Session, keywords: List[str] = None) -> int:
    """
    Получение и сохранение вакансий с HeadHunter

    Возвращает количество сохраненных вакансий
    """
    if keywords is None:
        keywords = ["разработчик", "дизайнер", "smm", "маркетолог", "аналитик"]

    async with HeadHunterParser() as parser:
        all_vacancies = []

        for keyword in keywords:
            vacancies = await parser.search_vacancies(text=keyword, per_page=20)
            all_vacancies.extend(vacancies)

        # Сохраняем в БД
        count = 0
        for vacancy_data in all_vacancies:
            # Проверяем, есть ли уже такая вакансия
            existing = db.query(models.Job).filter(
                models.Job.title == vacancy_data["title"],
                models.Job.company == vacancy_data["company"]
            ).first()

            if not existing:
                job = models.Job(
                    title=vacancy_data["title"][:255],
                    company=vacancy_data["company"][:255],
                    description=vacancy_data["description"],
                    link=vacancy_data["link"],
                    source=vacancy_data["source"],
                    location=vacancy_data["location"],
                    category=vacancy_data["category"],
                    employment_type=vacancy_data["employment_type"]
                )
                db.add(job)
                count += 1

        db.commit()
        return count