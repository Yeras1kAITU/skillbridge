import aiohttp
import asyncio
import uuid
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from .. import models
import logging

logger = logging.getLogger(__name__)

class HeadHunterParser:
    """Парсер вакансий с HeadHunter API"""
    
    BASE_URL = "https://api.hh.ru"
    HEADERS = {
        "User-Agent": "SkillBridge-Kazakhstan/1.0 (contact@skillbridge.kz)"  # <-- ОБЯЗАТЕЛЬНО
    }
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.HEADERS)  # <-- ПЕРЕДАЁМ HEADERS
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_vacancies(
        self,
        text: str = "",
        area: int = 160,  # Казахстан
        per_page: int = 50,
        page: int = 0
    ) -> List[Dict[str, Any]]:
        """Поиск вакансий на HeadHunter с пагинацией"""
        url = f"{self.BASE_URL}/vacancies"
        
        params = {
            "text": text,
            "area": area,
            "per_page": per_page,
            "page": page
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_vacancies(data.get("items", []))
                else:
                    logger.error(f"HeadHunter API ошибка: {response.status}")
                    if response.status == 403:
                        logger.error("❌ HeadHunter запрос заблокирован. Проверьте User-Agent и IP.")
                    return []
        except Exception as e:
            logger.error(f"Ошибка запроса к HeadHunter: {e}")
            return []
    
    async def search_all_pages(self, text: str, max_pages: int = 3) -> List[Dict[str, Any]]:
        """Поиск по всем страницам"""
        all_vacancies = []
        for page in range(max_pages):
            vacancies = await self.search_vacancies(text=text, page=page)
            if not vacancies:
                break
            all_vacancies.extend(vacancies)
            await asyncio.sleep(0.3)  # Защита от rate limiting
        return all_vacancies
    
    def _parse_vacancies(self, items: List[Dict]) -> List[Dict[str, Any]]:
        """Парсинг данных о вакансиях"""
        parsed = []
        for item in items:
            # Извлекаем зарплату
            salary = item.get("salary")
            salary_from = salary.get("from") if salary else None
            salary_to = salary.get("to") if salary else None
            salary_currency = salary.get("currency") if salary else None
            
            # Извлекаем город
            city = "Не указан"
            if item.get("area"):
                city = item["area"].get("name", "Не указан")
            
            # Извлекаем требования и обязанности
            requirements = []
            if item.get("snippet"):
                req = item["snippet"].get("requirement", "")
                if req:
                    requirements.append(req)
            
            # Определяем категорию
            title = item.get("name", "")
            description = item.get("description", "")
            category = self._detect_category(title, description)
            
            # Определяем тип занятости
            employment_type = self._detect_employment_type(item)
            
            parsed.append({
                "title": title[:255] if title else "Без названия",
                "company": item.get("employer", {}).get("name", "Не указана")[:255],
                "description": f"{description} {' '.join(requirements)}"[:5000],
                "link": item.get("alternate_url", ""),
                "source": "HeadHunter",
                "location": city,
                "category": category,
                "employment_type": employment_type,
                "salary_from": salary_from,
                "salary_to": salary_to,
                "salary_currency": salary_currency,
                "experience": item.get("experience", {}).get("name", "Не указан"),
                "schedule": item.get("schedule", {}).get("name", "Не указан"),
                "created_at": datetime.now()
            })
        
        return parsed
    
    def _detect_category(self, title: str, description: str) -> str:
        """Определение категории вакансии"""
        text = f"{title} {description}".lower()
        
        categories = {
            "development": ["разработчик", "developer", "программист", "backend", "frontend", "fullstack", 
                           "python", "java", "php", "c++", "c#", "javascript", "react", "vue", "angular",
                           "node.js", "django", "flask", "spring", "laravel", "symfony", "ruby", "golang",
                           "rust", "scala", "kotlin", "swift", "flutter", "react native", "typescript",
                           "web developer", "software engineer", "code", "programming"],
            "design": ["дизайнер", "designer", "ui", "ux", "графический", "веб-дизайн", "web design",
                       "figma", "photoshop", "illustrator", "after effects", "sketch", "adobe xd",
                       "прототип", "макет", "логотип", "брендинг", "полиграфия", "интерфейс"],
            "smm": ["smm", "маркетолог", "маркетинг", "social media", "таргетолог", "instagram",
                    "facebook", "telegram", "youtube", "tiktok", "twitter", "linkedin", "контент-менеджер",
                    "content manager", "community manager", "блогер", "influencer", "продвижение"],
            "video": ["видео", "video", "монтаж", "оператор", "режиссер", "видеограф", "video editor",
                      "premiere pro", "final cut", "davinci resolve", "sony vegas", "capcut",
                      "кинематограф", "съемка", "клип", "ролик", "рекламный ролик"],
            "copywriting": ["копирайтер", "copywriter", "редактор", "журналист", "контент", "writer",
                            "author", "blogger", "scenarist", "scriptwriter", "content writer",
                            "seo copywriter", "текст", "статья", "пост", "сценарий"],
            "analytics": ["аналитик", "analyst", "data", "big data", "data scientist", "data engineer",
                          "data analyst", "business analyst", "system analyst", "sql", "tableau",
                          "power bi", "excel", "python analyst", "исследование", "отчет"],
            "project_management": ["менеджер проектов", "project manager", "pm", "scrum master", "agile",
                                   "product owner", "team lead", "project lead", "project coordinator",
                                   "project administrator", "управление проектами"],
            "quality_assurance": ["qa", "тестировщик", "tester", "quality assurance", "test engineer",
                                  "automation", "manual testing", "selenium", "pytest", "junit",
                                  "test plan", "test case", "bug report", "тестирование"],
            "devops": ["devops", "sysadmin", "системный администратор", "сисадмин",
                       "system administrator", "linux", "windows", "network", "server",
                       "docker", "kubernetes", "aws", "azure", "gcp", "cloud", "ci/cd"],
            "hr": ["hr", "human resources", "рекрутер", "recruiter", "кадровый",
                   "personnel", "кадровик", "talent acquisition", "hr manager",
                   "hr specialist", "recruitment", "staffing", "персонал"],
            "finance": ["финансы", "finance", "accounting", "бухгалтер", "economist",
                        "экономист", "финансист", "audit", "auditor", "налоговый", "tax",
                        "payroll", "budgeting", "financial analyst"],
            "sales": ["продажи", "sales", "менеджер по продажам", "sales manager",
                      "business development", "bd", "account manager", "sales representative",
                      "торговый представитель", "ключевые клиенты", "переговоры"],
            "legal": ["юрист", "lawyer", "legal", "адвокат", "attorney", "правовой",
                      "юридический", "contract", "договор", "суд", "арбитраж", "право"]
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
            if "полный" in name or "full" in name:
                return "full_time"
            elif "частич" in name or "part" in name:
                return "part_time"
            elif "проект" in name or "project" in name:
                return "project"
            elif "стажировка" in name or "internship" in name:
                return "internship"
            elif "волонтер" in name or "volunteer" in name:
                return "volunteer"
        return "full_time"


async def fetch_hh_vacancies(db: Session, keywords: List[str] = None) -> Dict[str, Any]:
    """
    Получение и сохранение вакансий с HeadHunter
    
    Возвращает статистику синхронизации
    """
    if keywords is None:
        keywords = [
            "разработчик", "дизайнер", "smm", "маркетолог", "аналитик",
            "видеомонтаж", "копирайтер", "менеджер проектов", "qa", "devops",
            "программист", "frontend", "backend", "fullstack", "ui/ux",
            "контент-менеджер", "product manager", "data analyst"
        ]
    
    async with HeadHunterParser() as parser:
        all_vacancies = []
        
        for keyword in keywords:
            vacancies = await parser.search_all_pages(text=keyword, max_pages=2)
            all_vacancies.extend(vacancies)
            logger.info(f"Загружено {len(vacancies)} вакансий по ключевому слову '{keyword}'")
    
    # Сохраняем в БД
    new_count = 0
    updated_count = 0
    
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
        else:
            if existing.description != vacancy_data["description"]:
                existing.description = vacancy_data["description"]
                existing.link = vacancy_data["link"]
                existing.category = vacancy_data["category"]
                existing.employment_type = vacancy_data["employment_type"]
                updated_count += 1
    
    db.commit()
    
    return {
        "total_fetched": len(all_vacancies),
        "new_jobs": new_count,
        "updated_jobs": updated_count,
        "keywords_used": keywords
    }