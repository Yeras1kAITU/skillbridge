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

# Создание таблиц в БД
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SkillBridge Kazakhstan API", version="1.0")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем все роутеры
app.include_router(users.router)
app.include_router(portfolio.router)
app.include_router(analysis.router)
app.include_router(specialists.router)
app.include_router(jobs.router)

# === АВТОРИЗАЦИЯ (прямо в main.py) ===
@app.post("/auth/register", response_model=schemas.UserResponse)
async def register(user: schemas.UserCreate, db: Session = Depends(auth.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        full_name=user.full_name,
        email=user.email,
        hashed_password=hashed_password,
        phone=user.phone,
        city=user.city,
        role="user"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/auth/login", response_model=schemas.Token)
async def login(user: schemas.UserLogin, db: Session = Depends(auth.get_db)):
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
    return {"detail": "Успешный выход из системы"}

@app.post("/auth/forgot-password")
async def forgot_password(email: str, db: Session = Depends(auth.get_db)):
    return {"detail": "Инструкции по восстановлению пароля отправлены на ваш email"}

@app.post("/auth/reset-password")
async def reset_password():
    return {"detail": "Пароль успешно сброшен"}

# === НАСТРОЙКА ФРОНТЕНДА ===
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

INDEX_PATH = os.path.join(TEMPLATES_DIR, "index.html")

# Монтируем статику
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# === КОРНЕВОЙ МАРШРУТ ===
@app.get("/")
async def root():
    if os.path.exists(INDEX_PATH):
        return FileResponse(INDEX_PATH)

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head><title>SkillBridge Kazakhstan</title></head>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h1>🚀 SkillBridge Kazakhstan</h1>
        <p>API работает! <a href="/docs">Документация</a></p>
        <p>Файл index.html не найден по пути: {INDEX_PATH}</p>
    </body>
    </html>
    """)

# === HEALTH CHECK ===
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "SkillBridge Kazakhstan is running!"}