# backend/app/config.py
"""Конфигурация приложения"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    """Настройки приложения"""
    
    database_url: str = "postgresql://dev:password@localhost:5434/budget_forecasting"
    
    api_title: str = "Budget Forecasting API"
    api_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"
    
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    upload_dir: str = "data/uploads"
    max_upload_size: int = 10485760  # 10 MB
    allowed_file_extensions: list[str] = ["xlsx", "csv"]
    
    models_storage_path: str = "data/models"

    class Config:
        env_file = ".env"
        case_sensitive = False
        
        json_file = None
    
    log_level: str = "INFO"

@lru_cache()
def get_settings() -> Settings:
    """Получить настройки (кеширует один раз)"""
    return Settings()
