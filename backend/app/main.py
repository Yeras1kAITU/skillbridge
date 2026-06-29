from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from . import models, schemas, auth
from .database import engine, SessionLocal
from .routers import users, portfolio, analysis, specialists, jobs
import os
import asyncio
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание таблиц в БД
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SkillBridge Kazakhstan API",
    version="1.0",
    description="Цифровая платформа для анализа навыков молодежи Казахстана"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(users.router)
app.include_router(portfolio.router)
app.include_router(analysis.router)
app.include_router(specialists.router)
app.include_router(jobs.router)

# === АВТОРИЗАЦИЯ ===
@app.post("/auth/register", response_model=schemas.UserResponse)
async def register(user: schemas.UserCreate, db: Session = Depends(auth.get_db)):
    """Регистрация нового пользователя"""
    # Проверяем, существует ли пользователь
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    
    # Хешируем пароль и создаем пользователя
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        full_name=user.full_name,
        email=user.email,
        hashed_password=hashed_password,
        phone=user.phone,
        birth_date=user.birth_date,
        gender=user.gender,
        city=user.city,
        role="user"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/auth/login", response_model=schemas.Token)
async def login(user: schemas.UserLogin, db: Session = Depends(auth.get_db)):
    """Вход в систему"""
    db_user = auth.authenticate_user(db, user.email, user.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/logout")
async def logout():
    """Выход из системы"""
    return {"detail": "Успешный выход из системы"}

@app.post("/auth/forgot-password")
async def forgot_password(email: str, db: Session = Depends(auth.get_db)):
    """Восстановление пароля (заглушка)"""
    # Проверяем, существует ли пользователь
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # В реальном проекте здесь отправляется email со ссылкой для сброса пароля
    return {"detail": "Инструкции по восстановлению пароля отправлены на ваш email"}

@app.post("/auth/reset-password")
async def reset_password():
    """Сброс пароля (заглушка)"""
    return {"detail": "Пароль успешно сброшен"}

# === НАСТРОЙКА ФРОНТЕНДА ===
# Определяем пути к статическим файлам
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")

# Создаем папки, если их нет
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Путь к index.html
INDEX_PATH = os.path.join(TEMPLATES_DIR, "index.html")

# Монтируем статику
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root():
    """Главная страница"""
    if os.path.exists(INDEX_PATH):
        return FileResponse(INDEX_PATH)
    
    # Если index.html не найден, показываем диагностическую страницу
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SkillBridge Kazakhstan</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f4f6f9; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #16213e; }}
            .btn {{ background: #e94560; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            .btn:hover {{ background: #c73652; }}
            code {{ background: #f1f1f1; padding: 2px 6px; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 SkillBridge Kazakhstan</h1>
            <p>Платформа для анализа цифровых навыков молодежи Казахстана.</p>
            <p>Документация API: <a href="/docs">/docs</a></p>
            <p>Health Check: <a href="/health">/health</a></p>
            <p>Файл index.html не найден по пути: <code>{INDEX_PATH}</code></p>
            <button class="btn" onclick="window.location.href='/docs'">📚 Открыть API</button>
        </div>
    </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """Проверка состояния сервера"""
    return {
        "status": "ok",
        "message": "SkillBridge Kazakhstan is running!",
        "version": "1.0",
        "index_exists": os.path.exists(INDEX_PATH)
    }

@app.get("/api-status")
async def api_status(db: Session = Depends(auth.get_db)):
    """Статус API и базы данных"""
    try:
        # Проверяем подключение к БД
        user_count = db.query(models.User).count()
        job_count = db.query(models.Job).count()
        portfolio_count = db.query(models.Portfolio).count()
        
        return {
            "status": "ok",
            "database": "connected",
            "stats": {
                "users": user_count,
                "jobs": job_count,
                "portfolio_items": portfolio_count
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e)
        }

# === ОБРАБОТКА 404 ===
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>404 - Страница не найдена</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f4f6f9; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #16213e; font-size: 72px; margin: 0; }
            .btn { background: #e94560; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
            .btn:hover { background: #c73652; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>404</h1>
            <h2>Страница не найдена</h2>
            <p>Извините, запрошенная страница не существует.</p>
            <br>
            <a href="/" class="btn">🏠 Вернуться на главную</a>
        </div>
    </body>
    </html>
    """, status_code=404)

# === ФОНОВЫЕ ЗАДАЧИ ===
@app.on_event("startup")
async def startup_event():
    """Запуск фоновых задач при старте приложения"""
    logger.info("🚀 SkillBridge Kazakhstan запускается...")
    logger.info(f"📁 Frontend директория: {FRONTEND_DIR}")
    logger.info(f"📁 Templates директория: {TEMPLATES_DIR}")
    
    # Запускаем начальную синхронизацию вакансий в фоновом режиме
    async def background_sync():
        try:
            from .database import SessionLocal
            from .services.hh_parser import fetch_hh_vacancies
            
            # Ждем 10 секунд после запуска сервера для полной инициализации
            await asyncio.sleep(10)
            
            db = SessionLocal()
            try:
                # Проверяем, есть ли вакансии в базе
                count = db.query(models.Job).count()
                if count < 10:
                    logger.info("📊 База вакансий пуста, запускаем начальную синхронизацию с HeadHunter...")
                    result = await fetch_hh_vacancies(db)
                    logger.info(f"✅ Начальная синхронизация завершена: {result}")
                else:
                    logger.info(f"📊 В базе уже есть {count} вакансий, пропускаем начальную синхронизацию")
            except Exception as e:
                logger.error(f"❌ Ошибка начальной синхронизации: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"❌ Критическая ошибка фоновой задачи: {e}")
    
    # Запускаем фоновую задачу
    asyncio.create_task(background_sync())
    logger.info("✅ Сервер успешно запущен!")

@app.on_event("shutdown")
async def shutdown_event():
    """Действия при остановке сервера"""
    logger.info("🛑 SkillBridge Kazakhstan останавливается...")