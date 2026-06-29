from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import uuid

# Функция для генерации UUID в качестве первичного ключа
def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Личные данные
    phone = Column(String(20), nullable=True)
    birth_date = Column(Date, nullable=True)  # Дата рождения
    age = Column(Integer, nullable=True)  # Возраст (вычисляется)
    gender = Column(String(20), nullable=True)  # Пол
    city = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)  # Адрес

    # Образование
    education_level = Column(String(50), nullable=True)  # Высшее, Среднее, и т.д.
    education_institution = Column(String(255), nullable=True)  # Учебное заведение
    education_specialty = Column(String(255), nullable=True)  # Специальность
    graduation_year = Column(Integer, nullable=True)  # Год выпуска

    # Опыт работы
    experience_years = Column(Float, nullable=True)  # Лет опыта
    current_employer = Column(String(255), nullable=True)  # Текущее место работы
    current_position = Column(String(255), nullable=True)  # Текущая должность

    # Профессиональные данные
    about = Column(Text, nullable=True)
    experience_level = Column(String(50), nullable=True)
    role = Column(String(50), default="user")
    is_public = Column(Boolean, default=False)

    # Социальные сети
    linkedin = Column(String(255), nullable=True)
    github = Column(String(255), nullable=True)
    behance = Column(String(255), nullable=True)
    telegram = Column(String(255), nullable=True)
    instagram = Column(String(255), nullable=True)
    personal_website = Column(String(255), nullable=True)

    # Настройки
    language_preference = Column(String(10), default="ru")  # ru, kk, en
    email_notifications = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Portfolio(Base):
    __tablename__ = "portfolio"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=False)  # Путь к файлу или ссылка
    category = Column(String(100), nullable=True)  # "design", "development", "video", etc.
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="portfolio_items")

class Skill(Base):
    __tablename__ = "skills"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    skill_name = Column(String(100), nullable=False)
    level = Column(String(50), nullable=True) # "Начальный", "Средний", "Высокий"
    source = Column(String(50), default="manual") # "manual", "ai_analysis"

    owner = relationship("User", back_populates="skills")

class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    strengths = Column(JSON, nullable=True)  # ["сильная сторона 1", "сильная сторона 2"]
    weaknesses = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True) # ["рекомендация 1", "рекомендация 2"]
    suggested_services = Column(JSON, nullable=True) # ["Услуга 1", "Услуга 2"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="ai_analyses")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    link = Column(String(500), nullable=True)
    source = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    employment_type = Column(String(50), nullable=True) # "project", "full_time", "part_time"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи для рекомендаций
    recommendations = relationship("Recommendation", back_populates="job")

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    relevance_score = Column(Float, nullable=True) # 0-1
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="recommendations")
    job = relationship("Job", back_populates="recommendations")