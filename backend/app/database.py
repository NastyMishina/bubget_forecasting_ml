# backend/app/database.py
"""Управление подключением к базе данных"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import get_settings

settings = get_settings()

# Создаём engine
#engine = create_engine(
  #  settings.database_url,
   # echo=settings.debug,
   # pool_size=10,
   # max_overflow=20,
#)
engine = create_engine("postgresql://postgres:root@localhost:5434/budget_forecasting")

# Создаём SessionLocal
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

def get_db() -> Session:
    """
    Зависимость для получения сессии БД в эндпоинтах
    
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Инициализировать базу данных (создать таблицы)"""
    from app.models import Base
    Base.metadata.create_all(bind=engine)
