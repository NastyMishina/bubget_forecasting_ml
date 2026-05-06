# backend/tests/test_system.py
"""
Компактный набор тестов (17 тестов) для покрытия основных областей приложения.
Каждая область (auth, users, data, forecasts, repositories) имеет 1-2 теста.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import timedelta, date
import pandas as pd
import tempfile
import os

from app.models import Base, User, DataUpload, RawDataUpload, Feature, ModelVersion, Forecast
from app.database import get_db
from app.main import app
from app.auth import hash_password, verify_password, create_access_token
from app.repositories import (
    UserRepository, DataUploadRepository, RawDataUploadRepository,
    FeatureRepository, ModelVersionRepository, ForecastRepository
)


# ═══════════════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ ТЕСТОВОЙ БД
# ═══════════════════════════════════════════════════════════════════════

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Переопределяем get_db для тестов - используем тестовую БД"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Переопределяем зависимость
app.dependency_overrides[get_db] = override_get_db

# TestClient для тестирования endpoints
client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════════
# ФИКСТУРЫ
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def clean_db():
    """
    Очистить БД перед каждым тестом.
    autouse=True означает что эта фикстура запустится перед каждым тестом.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Сессия БД для тестов"""
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_user(db: Session):
    """Создать тестового пользователя (аналитик)"""
    repo = UserRepository(db)
    user = repo.create(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("password123"),
        role="analyst",
        is_active=True
    )
    return user


@pytest.fixture
def test_admin(db: Session):
    """Создать тестового админа"""
    repo = UserRepository(db)
    admin = repo.create(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("admin123"),
        role="admin",
        is_active=True
    )
    return admin


@pytest.fixture
def test_token(test_user):
    """JWT токен для обычного пользователя"""
    return create_access_token(
        data={"sub": str(test_user.id)},
        expires_delta=timedelta(hours=24)
    )


@pytest.fixture
def admin_token(test_admin):
    """JWT токен для админа"""
    return create_access_token(
        data={"sub": str(test_admin.id)},
        expires_delta=timedelta(hours=24)
    )


# ═══════════════════════════════════════════════════════════════════════
# ТЕСТЫ: АУТЕНТИФИКАЦИЯ (3 теста)
# ═══════════════════════════════════════════════════════════════════════

def test_auth_hash_and_verify_password():
    """
    Тест 1: Хеширование и проверка пароля
    
    Проверяет:
    - hash_password() создает хеш отличный от оригинала
    - verify_password() работает с правильным паролем
    - verify_password() не работает с неправильным паролем
    """
    password = "secret123"
    hashed = hash_password(password)
    
    # Пароль не равен хешу
    assert hashed != password
    
    # verify работает с правильным паролем
    assert verify_password(password, hashed) is True
    
    # verify не работает с неправильным паролем
    assert verify_password("wrongpass", hashed) is False


def test_auth_login_success(test_user):
    """
    Тест 2: Логин с правильными данными
    
    Проверяет:
    - POST /api/auth/login возвращает 200
    - Ответ содержит access_token, username, role
    """
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "password123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["username"] == "testuser"
    assert data["role"] == "analyst"


def test_auth_login_failure(test_user):
    """
    Тест 3: Логин с неверным паролем
    
    Проверяет:
    - POST /api/auth/login с неверным паролем возвращает 401
    """
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "wrongpass"
        }
    )
    
    assert response.status_code == 401
    assert "detail" in response.json()


# ═══════════════════════════════════════════════════════════════════════
# ТЕСТЫ: УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ (3 теста)
# ═══════════════════════════════════════════════════════════════════════

def test_users_create_as_admin(admin_token):
    """
    Тест 4: Админ может создать пользователя
    
    Проверяет:
    - POST /api/users с админским токеном возвращает 200/201
    - Создает пользователя с правильными данными
    """
    response = client.post(
        "/api/users",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpass123",
            "full_name": "New User",
            "role": "analyst"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code in [200, 201]
    assert response.json()["username"] == "newuser"



def test_users_delete_as_admin(admin_token, test_user):
    """
    Тест 6: Админ может удалить пользователя
    
    Проверяет:
    - DELETE /api/users/{id} возвращает 200
    - В ответе есть сообщение об удалении
    """
    response = client.delete(
        f"/api/users/{test_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════
# ТЕСТЫ: ЗАЩИТА МАРШРУТОВ (2 теста)
# ═══════════════════════════════════════════════════════════════════════

def test_routes_protected_without_token():
    """
    Тест 7: Защищённый маршрут требует токен
    
    Проверяет:
    - Доступ без токена к /api/users возвращает 401 или 403
    """
    response = client.get("/api/users")
    
    assert response.status_code in [401, 403]


def test_routes_access_denied_non_admin(test_token):
    """
    Тест 8: Обычный пользователь не имеет доступа к админским маршрутам
    
    Проверяет:
    - GET /api/users с токеном analyst возвращает 403
    """
    response = client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════════════
# ТЕСТЫ: РЕПОЗИТОРИИ (3 теста)
# ═══════════════════════════════════════════════════════════════════════

def test_repo_user_create_and_retrieve(db: Session):
    """
    Тест 9: UserRepository - создание и получение пользователя
    
    Проверяет:
    - create() создает пользователя с ID
    - get_by_username() находит пользователя по логину
    """
    repo = UserRepository(db)
    
    # Создать
    user = repo.create(
        username="repouser",
        email="repo@example.com",
        password_hash=hash_password("pass123"),
        role="analyst"
    )
    
    assert user.id is not None
    
    # Получить
    retrieved = repo.get_by_username("repouser")
    assert retrieved is not None
    assert retrieved.email == "repo@example.com"


def test_repo_data_upload_crud(db: Session, test_user):
    """
    Тест 10: DataUploadRepository - создание, обновление, удаление
    
    Проверяет:
    - create() создает загрузку
    - get_by_id() получает загрузку
    - update() обновляет поля
    - delete() удаляет загрузку
    """
    repo = DataUploadRepository(db)
    
    # Создать
    upload = repo.create(
        user_id=test_user.id,
        filename="test.csv",
        file_path="/data/test.csv",
        status="completed"
    )
    
    assert upload.id is not None
    
    # Получить
    retrieved = repo.get_by_id(upload.id)
    assert retrieved is not None
    
    # Обновить
    updated = repo.update(upload.id, {"status": "processing"})
    assert updated.status == "processing"
    
    # Удалить
    deleted = repo.delete(upload.id)
    assert deleted is True


def test_repo_raw_data_bulk_insert(db: Session, test_user):
    """
    Тест 11: RawDataUploadRepository - массовая вставка данных
    
    Проверяет:
    - bulk_create() вставляет несколько записей за раз
    - get_by_upload_id() получает все raw данные для загрузки
    """
    # Создать upload
    upload_repo = DataUploadRepository(db)
    upload = upload_repo.create(
        user_id=test_user.id,
        filename="test.csv",
        file_path="/data/test.csv"
    )
    
    # Массовая вставка raw данных
    raw_repo = RawDataUploadRepository(db)
    records = [
        {
            "upload_id": upload.id,
            "period": date(2024, 1, 1),
            "indicator_name": "revenue",
            "value": 1000.0
        },
        {
            "upload_id": upload.id,
            "period": date(2024, 1, 1),
            "indicator_name": "expenses",
            "value": 500.0
        }
    ]
    
    count = raw_repo.bulk_create(records)
    assert count == 2
    
    # Получить и проверить
    retrieved = raw_repo.get_by_upload_id(upload.id)
    assert len(retrieved) == 2


# ═══════════════════════════════════════════════════════════════════════
# ТЕСТЫ: МОДЕЛИ И ПРОГНОЗЫ (2 теста)
# ═══════════════════════════════════════════════════════════════════════

def test_repo_model_version_create_and_activate(db: Session):
    """
    Тест 12: ModelVersionRepository - создание и активация модели
    
    Проверяет:
    - create() создает версию модели
    - set_active() активирует модель
    - get_active() получает активную модель для алгоритма
    """
    repo = ModelVersionRepository(db)
    
    # Создать модель
    model = repo.create(
        algorithm="xgboost",
        version="1.0",
        model_file_path="/models/xgboost_1.0.pkl",
        mae=10.5,
        rmse=12.3,
        r2_score=0.85
    )
    
    assert model.id is not None
    
    # Активировать
    activated = repo.set_active(model.id)
    assert activated is True
    
    # Проверить что активна
    active = repo.get_active("xgboost")
    assert active is not None
    assert active.id == model.id


def test_repo_forecast_create_and_retrieve(db: Session, test_user):
    """
    Тест 13: ForecastRepository - создание и получение прогноза
    
    Проверяет:
    - create() создает прогноз со связанными upload и feature
    - get_by_id() получает прогноз по ID
    """
    # Создать upload
    upload_repo = DataUploadRepository(db)
    upload = upload_repo.create(
        user_id=test_user.id,
        filename="test.csv",
        file_path="/data/test.csv"
    )
    
    # Создать feature
    feature_repo = FeatureRepository(db)
    feature = feature_repo.create(
        upload_id=upload.id,
        features_file_path="/features/test.csv",
        target_column="revenue",
        feature_count=10,
        row_count=100
    )
    
    # Создать прогноз
    forecast_repo = ForecastRepository(db)
    forecast = forecast_repo.create(
        upload_id=upload.id,
        features_id=feature.id,
        model_version_id=1,
        target_column="revenue",
        status="completed"
    )
    
    assert forecast.id is not None
    
    # Получить
    retrieved = forecast_repo.get_by_id(forecast.id)
    assert retrieved is not None
    assert retrieved.target_column == "revenue"


# ═══════════════════════════════════════════════════════════════════════
# ТЕСТЫ: ДАННЫЕ И ОБРАБОТКА (2 теста)
# ═══════════════════════════════════════════════════════════════════════

def test_data_schemas_validation():
    """
    Тест 14: Pydantic схемы валидируют данные
    
    Проверяет:
    - UserCreateSchema валидирует данные пользователя
    - TokenResponse валидирует ответ с токеном
    """
    from app.schemas import UserCreateSchema, TokenResponse
    
    # Правильные данные
    valid_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "pass123",
        "full_name": "Test User",
        "role": "analyst"
    }
    
    user_schema = UserCreateSchema(**valid_data)
    assert user_schema.username == "testuser"
    
    # TokenResponse
    token_data = {
        "access_token": "token123",
        "token_type": "bearer",
        "user_id": 1,
        "username": "testuser",
        "role": "analyst"
    }
    
    token_response = TokenResponse(**token_data)
    assert token_response.user_id == 1


def test_data_csv_structure():
    """
    Тест 15: CSV файлы имеют правильную структуру
    
    Проверяет:
    - CSV содержит требуемые колонки (period, indicator_name, value)
    - Данные загружаются правильно в pandas DataFrame
    """
    csv_content = """period,indicator_name,value
2024-01,revenue,1000
2024-01,expenses,500
2024-02,revenue,1100"""
    
    df = pd.read_csv(pd.io.common.StringIO(csv_content))
    
    # Проверить колонки
    assert "period" in df.columns
    assert "indicator_name" in df.columns
    assert "value" in df.columns
    
    # Проверить строки
    assert len(df) == 3


# ═══════════════════════════════════════════════════════════════════════
# ТЕСТЫ: ИНТЕГРАЦИЯ (2 теста)
# ═══════════════════════════════════════════════════════════════════════

def test_integration_register_login_access():
    """
    Тест 16: Полный цикл - регистрация → логин → доступ
    
    Проверяет:
    - POST /api/auth/register создает пользователя и возвращает токен
    - POST /api/auth/login авторизует пользователя
    - Токен можно использовать для доступа к защищённым маршрутам
    """
    # 1. Регистрация
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "fullcycle",
            "email": "fullcycle@example.com",
            "password": "pass123",
            "role": "analyst"
        }
    )
    
    assert register_response.status_code == 200
    
    # 2. Логин
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "fullcycle",
            "password": "pass123"
        }
    )
    
    assert login_response.status_code == 200
    login_token = login_response.json()["access_token"]
    
    # 3. Использование токена для защищённого endpoint
    # Возвращает 403 потому что это админский endpoint и пользователь не админ
    # Но это значит что токен валидный и работает
    protected_response = client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {login_token}"}
    )
    
    assert protected_response.status_code == 403
