from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


class User(Base):
    """Пользователи системы"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default='analyst')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    # Отношения
    data_uploads = relationship("DataUpload", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class DataUpload(Base):
    """Загруженные файлы - метаданные загрузки"""
    __tablename__ = "data_uploads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    filename = Column(String(500), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    
    period_from = Column(Date)
    period_to = Column(Date)
    
    status = Column(String(50), default='pending', index=True) 
    validation_errors = Column(JSONB, default={})
    
    upload_date = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="data_uploads")
    raw_data = relationship("RawDataUpload", back_populates="upload", cascade="all, delete-orphan")
    features = relationship("Feature", back_populates="upload", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="upload", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DataUpload(id={self.id}, filename='{self.filename}')>"


class RawDataUpload(Base):
    """Исходные данные из CSV (нормализованные)"""
    __tablename__ = "raw_data_uploads"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("data_uploads.id"), nullable=False, index=True)
    
    period = Column(Date, nullable=False, index=True)
    indicator_name = Column(String(255), nullable=False, index=True)
    value = Column(Float)
    
    source_row = Column(Integer)
    is_duplicate = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.now)

    upload = relationship("DataUpload", back_populates="raw_data")

    def __repr__(self):
        return f"<RawDataUpload(upload_id={self.upload_id}, period={self.period}, indicator='{self.indicator_name}')>"


class Feature(Base):
    """Признаки для ML (метаданные о файле)"""
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("data_uploads.id"), nullable=False, index=True)
    
    features_file_path = Column(String(500), nullable=False)
    
    target_column = Column(String(255))
    
    feature_count = Column(Integer)
    row_count = Column(Integer)
    
    status = Column(String(50), default='completed') 
    
    created_at = Column(DateTime, default=datetime.now)

    upload = relationship("DataUpload", back_populates="features")
    forecasts = relationship("Forecast", back_populates="features", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Feature(id={self.id}, upload_id={self.upload_id}, target='{self.target_column}')>"


class ModelVersion(Base):
    """Версии ML моделей (предобученные)"""
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    
    algorithm = Column(String(100), nullable=False, index=True) 
    version = Column(String(50), nullable=False)
    model_file_path = Column(String(500), nullable=False)
    
    mae = Column(Float)
    rmse = Column(Float)
    r2_score = Column(Float)
    
    is_active = Column(Boolean, default=False, index=True)
    
    created_at = Column(DateTime, default=datetime.now)

    forecasts = relationship("Forecast", back_populates="model_version")

    def __repr__(self):
        return f"<ModelVersion(id={self.id}, algorithm='{self.algorithm}', version='{self.version}')>"


class Forecast(Base):
    """Результаты прогнозирования"""
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("data_uploads.id"), nullable=False, index=True)
    features_id = Column(Integer, ForeignKey("features.id"), nullable=False, index=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=False, index=True)
    
    target_column = Column(String(255), nullable=False)
    
    base_forecast_path = Column(String(500))
    optimistic_forecast_path = Column(String(500))
    pessimistic_forecast_path = Column(String(500))
    
    status = Column(String(50), default='completed')
    
    created_at = Column(DateTime, default=datetime.now)

    upload = relationship("DataUpload", back_populates="forecasts")
    features = relationship("Feature", back_populates="forecasts")
    model_version = relationship("ModelVersion", back_populates="forecasts")

    def __repr__(self):
        return f"<Forecast(id={self.id}, upload_id={self.upload_id}, model_version_id={self.model_version_id})>"


class AuditLog(Base):
    """Логи аудита"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    action = Column(String(255))
    resource_type = Column(String(100))
    resource_id = Column(Integer)

    description = Column(String(1000))
    old_values = Column(JSONB, default={})
    new_values = Column(JSONB, default={})
    
    status = Column(String(50))
    error_message = Column(String(1000))
    
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', resource_type='{self.resource_type}')>"
