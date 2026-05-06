# backend/app/main.py
"""Главное FastAPI приложение"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import auth

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.api.routes import router
from app.api.routes.forecasts import router as forecasts_router
from app.api.routes.users import router as users_router
#from app.api.routes.models import router as models_router
from app.schemas import HealthResponse
from app.services.model_loader import ModelLoader


logger = logging.getLogger(__name__)
settings = get_settings()

# Инициализируем БД при старте
init_db()

# Глобальный кэш моделей
model_loader = ModelLoader()

# Создаём приложение
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="API для прогнозирования бюджетных показателей",
    debug=settings.debug,
)

# Прокидываем model_loader в app.state для доступа из эндпоинтов
app.state.model_loader = model_loader


@app.on_event("startup")
async def startup() -> None:
    try:
         logger.info("Приложение запускается...")
    except Exception as exc:
        logger.error(f"Ошибка при старте: {str(exc)}", exc_info=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)
app.include_router(forecasts_router)
app.include_router(auth.router)
app.include_router(users_router)
#app.include_router(models_router)


@app.get("/", response_model=HealthResponse)
async def root():
    """Корневой эндпоинт"""
    return {
        "status": "ok",
        "version": settings.api_version,
        "environment": settings.environment,
    }

@app.get("/health", response_model=HealthResponse)
async def health():
    """Проверка работы приложения"""
    return {
        "status": "ok",
        "version": settings.api_version,
        "environment": settings.environment,
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Обработчик общих ошибок"""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": str(exc) if settings.debug else "Internal Server Error",
        },
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
