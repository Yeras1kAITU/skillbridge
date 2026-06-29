import os
import re
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID

# Получаем DATABASE_URL из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")

# Если DATABASE_URL не задан, используем SQLite для локальной разработки
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./skillbridge.db"
    print(" DATABASE_URL не найден, используем SQLite")

# Для Supabase Pooler заменяем postgres:// на postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Добавляем sslmode если его нет в URL
if "postgresql" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"
    else:
        DATABASE_URL += "?sslmode=require"

# Безопасный вывод URL в логах (скрываем пароль)
if '@' in DATABASE_URL:
    masked_url = re.sub(r':[^:@]*@', ':***@', DATABASE_URL)
    print(f" Подключение к БД: {masked_url}")
else:
    print(f" Подключение к БД: {DATABASE_URL}")

# Создаем engine с настройками для Supabase
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
    echo=False,
    connect_args={
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    } if "postgresql" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        print(f" Ошибка БД: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print(" Таблицы созданы/проверены")
    except Exception as e:
        print(f" Ошибка создания таблиц: {e}")
        raise