from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date

# --- Auth ---
class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: Optional[str] = Field(None, max_length=20)
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- User ---
class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    education_level: Optional[str] = Field(None, max_length=50)
    education_institution: Optional[str] = Field(None, max_length=255)
    education_specialty: Optional[str] = Field(None, max_length=255)
    graduation_year: Optional[int] = Field(None, ge=1900, le=2100)
    experience_years: Optional[float] = Field(None, ge=0)
    current_employer: Optional[str] = Field(None, max_length=255)
    current_position: Optional[str] = Field(None, max_length=255)
    about: Optional[str] = Field(None, max_length=1000)
    experience_level: Optional[str] = None
    is_public: Optional[bool] = None
    linkedin: Optional[str] = Field(None, max_length=255)
    github: Optional[str] = Field(None, max_length=255)
    behance: Optional[str] = Field(None, max_length=255)
    telegram: Optional[str] = Field(None, max_length=255)
    instagram: Optional[str] = Field(None, max_length=255)
    personal_website: Optional[str] = Field(None, max_length=255)
    language_preference: Optional[str] = Field(None, max_length=10)
    email_notifications: Optional[bool] = None

class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    phone: Optional[str]
    birth_date: Optional[date]
    age: Optional[int]
    gender: Optional[str]
    city: Optional[str]
    address: Optional[str]
    education_level: Optional[str]
    education_institution: Optional[str]
    education_specialty: Optional[str]
    graduation_year: Optional[int]
    experience_years: Optional[float]
    current_employer: Optional[str]
    current_position: Optional[str]
    about: Optional[str]
    experience_level: Optional[str]
    role: str
    is_public: bool
    linkedin: Optional[str]
    github: Optional[str]
    behance: Optional[str]
    telegram: Optional[str]
    instagram: Optional[str]
    personal_website: Optional[str]
    language_preference: str
    email_notifications: bool
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)

# --- Portfolio ---
class PortfolioItemCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    is_public: bool = False

class PortfolioItemUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    is_public: Optional[bool] = None

class PortfolioItemResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: Optional[str]
    file_path: str
    category: Optional[str]
    is_public: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Skills ---
class SkillCreate(BaseModel):
    skill_name: str = Field(..., max_length=100)
    level: Optional[str] = Field(None, max_length=50)
    source: Optional[str] = "manual"

class SkillResponse(BaseModel):
    id: UUID
    user_id: UUID
    skill_name: str
    level: Optional[str]
    source: str
    model_config = ConfigDict(from_attributes=True)

# --- AI Analysis ---
class AIAnalysisResponse(BaseModel):
    id: UUID
    user_id: UUID
    strengths: Optional[List[str]]
    weaknesses: Optional[List[str]]
    recommendations: Optional[List[str]]
    suggested_services: Optional[List[str]]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Jobs ---
class JobResponse(BaseModel):
    id: UUID
    title: str
    company: Optional[str]
    description: Optional[str]
    link: Optional[str]
    source: Optional[str]
    location: Optional[str]
    category: Optional[str]
    employment_type: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Recommendations ---
class RecommendationResponse(BaseModel):
    id: UUID
    user_id: UUID
    job_id: UUID
    job: JobResponse
    relevance_score: Optional[float]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)