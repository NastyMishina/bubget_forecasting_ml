from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date


class UserSchema(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserCreateSchema(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str = "analyst"
    
    class Config:
        schema_extra = {
            "example": {
                "username": "ivan_ivanov",
                "email": "ivan@example.com",
                "password": "secure_password_123",
                "full_name": "Иван Иванов",
                "role": "analyst"
            }
        }

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    role: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str = None
    role: str = "analyst"
 
    class Config:
        schema_extra = {
            "example": {
                "username": "ivan_ivanov",
                "email": "ivan@example.com",
                "password": "secure_password_123",
                "full_name": "Иван Иванов",
                "role": "analyst"
            }
        }

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    role: str


class DataUploadSchema(BaseModel):
    id: int
    user_id: int
    filename: str
    status: str
    period_from: Optional[date]
    period_to: Optional[date]
    created_at: datetime
    
    class Config:
        from_attributes = True


class RawDataUploadSchema(BaseModel):
    id: int
    upload_id: int
    period: date
    indicator_name: str
    value: Optional[float]
    
    class Config:
        from_attributes = True


class FeatureSchema(BaseModel):
    id: int
    upload_id: int
    features_file_path: str
    target_column: str
    feature_count: Optional[int]
    row_count: Optional[int]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ModelVersionSchema(BaseModel):
    id: int
    algorithm: str
    version: str
    ml_file_path: str
    mae: Optional[float]
    rmse: Optional[float]
    r2_score: Optional[float]
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        protected_namespaces=() 
    )


class ForecastSchema(BaseModel):
    id: int
    upload_id: int
    features_id: int
    ml_version_id: int
    target_column: str
    base_forecast_path: Optional[str]
    optimistic_forecast_path: Optional[str]
    pessimistic_forecast_path: Optional[str]
    status: str
    created_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        protected_namespaces=() 
    )

class ForecastResponseSchema(BaseModel):
    """Ответ при создании прогноза"""
    forecast_id: int
    upload_id: int
    algorithm: str
    ml_version: str
    forecast_paths: dict
    status: str

class DataUploadResponse(BaseModel):
    """Ответ при получении информации о загрузке"""
    id: int
    user_id: int
    filename: str
    file_path: str
    file_size: int
    period_from: Optional[datetime] = None
    period_to: Optional[datetime] = None
    status: str
    validation_errors: Optional[dict] = None
    upload_date: datetime
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """Статус работы приложения"""
    status: str = "ok"
    version: str
    environment: str
