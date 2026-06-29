import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Получаем DATABASE_URL из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")

# Если DATABASE_URL не задан, используем SQLite для локальной разработки
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./skillbridge.db"
    print("⚠️ DATABASE_URL не найден, используем SQLite")

# Для Supabase Pooler заменяем postgres:// на postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Добавляем sslmode если его нет в URL
if "postgresql" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    # Проверяем, есть ли уже параметры в URL
    if "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"
    else:
        DATABASE_URL += "?sslmode=require"

print(f"🔗 Подключение к БД: {DATABASE_URL.replace(/:[^:@]*@/, ':***@') if '@' in DATABASE_URL else DATABASE_URL}")

# Создаем engine с настройками для Supabase
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Проверка соединения перед использованием
    pool_recycle=300,        # Переподключение каждые 5 минут
    pool_size=5,             # Максимум соединений в пуле
    max_overflow=10,         # Дополнительные соединения при необходимости
    echo=False,              # Отключаем логи SQL (для продакшена)
    connect_args={
        "connect_timeout": 10,  # Таймаут подключения
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    } if "postgresql" in DATABASE_URL else {}
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()

# Функция для получения сессии БД (используется в эндпоинтах)
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# Функция для инициализации БД (создание таблиц)
def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print(" Таблицы созданы/проверены")
    except Exception as e:
        print(f" Ошибка создания таблиц: {e}")
        raise