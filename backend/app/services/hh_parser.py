import aiohttp
import asyncio
import uuid
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from .. import models
import logging
import random

logger = logging.getLogger(__name__)

class HeadHunterParser:
    """Парсер вакансий с HeadHunter API"""
    
    BASE_URL = "https://api.hh.ru"
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        user_agent = random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "SkillBridge-Kazakhstan/1.0 (contact@skillbridge.kz)"
        ])
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://hh.kz/"
        }
        self.session = aiohttp.ClientSession(headers=headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_vacancies(
        self,
        text: str = "",
        area: int = 160,
        per_page: int = 50,
        page: int = 0
    ) -> List[Dict[str, Any]]:
        """Поиск вакансий на HeadHunter"""
        url = f"{self.BASE_URL}/vacancies"
        
        # Все параметры должны быть str, int или float
        params = {}
        if text and isinstance(text, str):
            params["text"] = text
        if area and isinstance(area, (int, float)):
            params["area"] = int(area)
        if per_page and isinstance(per_page, (int, float)):
            params["per_page"] = int(per_page)
        if page is not None and isinstance(page, (int, float)):
            params["page"] = int(page)
        # Убираем только_with_salary - он вызывает ошибку с булевым значением
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_vacancies(data.get("items", []))
                elif response.status == 403:
                    logger.error(f"❌ HeadHunter 403: Запрос заблокирован")
                    return []
                else:
                    logger.error(f"HeadHunter API ошибка: {response.status}")
                    return []
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети: {e}")
            return []
        except Exception as e:
            logger.error(f"Ошибка запроса: {e}")
            return []
    
    async def search_all_pages(self, text: str, max_pages: int = 2) -> List[Dict[str, Any]]:
        """Поиск по всем страницам"""
        all_vacancies = []
        for page in range(max_pages):
            vacancies = await self.search_vacancies(text=text, page=page)
            if not vacancies:
                break
            all_vacancies.extend(vacancies)
            await asyncio.sleep(random.uniform(0.3, 0.8))
        return all_vacancies
    
    def _parse_vacancies(self, items: List[Dict]) -> List[Dict[str, Any]]:
        """Парсинг данных о вакансиях"""
        parsed = []
        for item in items:
            salary = item.get("salary")
            city = "Не указан"
            if item.get("area"):
                city = item["area"].get("name", "Не указан")
            
            title = item.get("name", "")
            description = item.get("description", "")
            category = self._detect_category(title, description)
            employment_type = self._detect_employment_type(item)
            
            parsed.append({
                "title": title[:255] if title else "Без названия",
                "company": item.get("employer", {}).get("name", "Не указана")[:255],
                "description": description[:5000] if description else "Нет описания",
                "link": item.get("alternate_url", ""),
                "source": "HeadHunter",
                "location": city,
                "category": category,
                "employment_type": employment_type,
                "salary_from": salary.get("from") if salary else None,
                "salary_to": salary.get("to") if salary else None,
                "salary_currency": salary.get("currency") if salary else None,
                "experience": item.get("experience", {}).get("name", "Не указан"),
                "created_at": datetime.now()
            })
        
        return parsed
    
    def _detect_category(self, title: str, description: str) -> str:
        """Определение категории вакансии"""
        text = f"{title} {description}".lower()
        
        categories = {
            "development": ["разработчик", "developer", "программист", "backend", "frontend", "fullstack", "python", "java", "php", "javascript", "react", "vue", "angular"],
            "design": ["дизайнер", "designer", "ui", "ux", "графический", "веб-дизайн", "figma", "photoshop", "illustrator"],
            "smm": ["smm", "маркетолог", "маркетинг", "social media", "таргетолог", "instagram", "facebook", "telegram"],
            "video": ["видео", "video", "монтаж", "оператор", "режиссер", "premiere", "after effects", "final cut"],
            "copywriting": ["копирайтер", "copywriter", "редактор", "журналист", "контент", "текст", "статья"],
            "analytics": ["аналитик", "analyst", "data", "big data", "sql", "tableau", "power bi", "excel"],
            "project_management": ["менеджер проектов", "project manager", "scrum", "agile", "product owner", "pm"],
            "quality_assurance": ["qa", "тестировщик", "tester", "quality assurance", "selenium", "pytest"],
            "devops": ["devops", "sysadmin", "системный администратор", "docker", "kubernetes", "aws", "linux"],
            "hr": ["hr", "рекрутер", "recruiter", "кадровый", "personnel", "talent acquisition"],
            "finance": ["финансы", "finance", "accounting", "бухгалтер", "economist", "экономист"],
            "sales": ["продажи", "sales", "менеджер по продажам", "business development", "account manager"],
            "legal": ["юрист", "lawyer", "legal", "адвокат", "юридический", "contract"]
        }
        
        scores = {cat: 0 for cat in categories}
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text:
                    scores[category] += 1
        
        best_category = max(scores, key=scores.get)
        return best_category if scores[best_category] > 0 else "other"
    
    def _detect_employment_type(self, item: Dict) -> str:
        """Определение типа занятости"""
        employment = item.get("employment", {})
        if employment:
            name = employment.get("name", "").lower()
            if "полный" in name:
                return "full_time"
            elif "частич" in name:
                return "part_time"
            elif "проект" in name:
                return "project"
            elif "стажировка" in name:
                return "internship"
        return "full_time"


async def fetch_hh_vacancies(db: Session, keywords: List[str] = None) -> Dict[str, Any]:
    """Получение и сохранение вакансий с HeadHunter"""
    if keywords is None:
        keywords = [
            "разработчик", "дизайнер", "smm", "маркетолог", "аналитик",
            "видеомонтаж", "копирайтер", "менеджер проектов", "qa", "devops"
        ]
    
    async with HeadHunterParser() as parser:
        all_vacancies = []
        for keyword in keywords:
            vacancies = await parser.search_all_pages(text=keyword, max_pages=2)
            all_vacancies.extend(vacancies)
            logger.info(f"Загружено {len(vacancies)} вакансий по ключевому слову '{keyword}'")
    
    new_count = 0
    for vacancy_data in all_vacancies:
        existing = db.query(models.Job).filter(
            models.Job.title == vacancy_data["title"],
            models.Job.company == vacancy_data["company"]
        ).first()
        
        if not existing:
            job = models.Job(
                id=str(uuid.uuid4()),
                title=vacancy_data["title"],
                company=vacancy_data["company"],
                description=vacancy_data["description"],
                link=vacancy_data["link"],
                source=vacancy_data["source"],
                location=vacancy_data["location"],
                category=vacancy_data["category"],
                employment_type=vacancy_data["employment_type"]
            )
            db.add(job)
            new_count += 1
    
    db.commit()
    
    return {
        "total_fetched": len(all_vacancies),
        "new_jobs": new_count,
        "updated_jobs": 0,
        "keywords_used": keywords
    }