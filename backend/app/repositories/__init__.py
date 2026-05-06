from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.models import (
    User, DataUpload, RawDataUpload, Feature, 
    ModelVersion, Forecast, AuditLog
)
from datetime import date
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    """Репозиторий для работы с пользователями"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, username: str, email: str, password_hash: str, **kwargs) -> User:
        user = User(username=username, email=email, password_hash=password_hash, **kwargs)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).get(user_id)
    
    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
    
    def get_all(self) -> List[User]:
        """Получить всех пользователей"""
        return self.db.query(User).all()

    def delete(self, user_id: int) -> bool:
        """Удалить пользователя по ID"""
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False


class DataUploadRepository:
    """Репозиторий для работы с загруженными файлами"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, user_id: int, filename: str, file_path: str, **kwargs) -> DataUpload:
        upload = DataUpload(user_id=user_id, filename=filename, file_path=file_path, **kwargs)
        self.db.add(upload)
        self.db.commit()
        self.db.refresh(upload)
        return upload
    
    def get_by_id(self, upload_id: int) -> Optional[DataUpload]:
        return self.db.query(DataUpload).get(upload_id)
    
    def get_by_user_id(self, user_id: int) -> List[DataUpload]:
        return self.db.query(DataUpload).filter(DataUpload.user_id == user_id).all()
    
    def update(self, upload_id: int, data: dict) -> DataUpload:
        upload = self.get_by_id(upload_id)
        if upload:
            for key, value in data.items():
                if hasattr(upload, key):
                    setattr(upload, key, value)
            self.db.commit()
            self.db.refresh(upload)
        return upload
    
    def delete(self, upload_id: int) -> bool:
        upload = self.get_by_id(upload_id)
        if upload:
            self.db.delete(upload)
            self.db.commit()
            return True
        return False


class RawDataUploadRepository:
    """Репозиторий для работы с исходными данными"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def bulk_create(self, records: List[dict]) -> int:
        """Массовая вставка записей"""
        if not records:
            return 0
        
        objects = [RawDataUpload(**r) for r in records]
        self.db.bulk_save_objects(objects)
        self.db.commit()
        return len(objects)
    
    def get_by_upload_id(self, upload_id: int) -> List[RawDataUpload]:
        return self.db.query(RawDataUpload).filter(
            RawDataUpload.upload_id == upload_id
        ).order_by(RawDataUpload.period).all()
    
    def get_by_upload_and_indicator(self, upload_id: int, indicator_name: str) -> List[RawDataUpload]:
        return self.db.query(RawDataUpload).filter(
            and_(
                RawDataUpload.upload_id == upload_id,
                RawDataUpload.indicator_name == indicator_name
            )
        ).order_by(RawDataUpload.period).all()
    
    def delete_by_upload(self, upload_id: int) -> int:
        count = self.db.query(RawDataUpload).filter(
            RawDataUpload.upload_id == upload_id
        ).delete()
        self.db.commit()
        return count
    
    def count_by_upload_id(self, upload_id: int) -> int:
        """Подсчитать строки для upload_id"""
        return self.db.query(RawDataUpload).filter(
            RawDataUpload.upload_id == upload_id
        ).count()
    
    def get_statistics(self, upload_id: int) -> dict:
        """Получить статистику по загрузке"""
        data = self.db.query(RawDataUpload).filter(
            RawDataUpload.upload_id == upload_id
        ).all()
        
        if not data:
            return {"error": "No data found"}
        
        indicators = set(d.indicator_name for d in data)
        periods = set(d.period for d in data)
        
        return {
            "row_count": len(data),
            "unique_indicators": len(indicators),
            "unique_periods": len(periods),
            "period_from": min(periods) if periods else None,
            "period_to": max(periods) if periods else None,
        }


class FeatureRepository:
    """Репозиторий для работы с признаками"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        upload_id: int,
        features_file_path: str,
        target_column: str,
        feature_count: int,
        row_count: int,
        status: str = "completed"
    ) -> Feature:
        """Создать новый набор признаков"""
        existing = self.db.query(Feature).filter(
            Feature.upload_id == upload_id
        ).first()
        
        if existing:
            self.db.delete(existing)
            self.db.commit()
        
        # Создать новый
        feature = Feature(
            upload_id=upload_id,
            features_file_path=features_file_path,
            target_column=target_column,
            feature_count=feature_count,
            row_count=row_count,
            status=status
        )
        self.db.add(feature)
        self.db.commit()
        self.db.refresh(feature)
        return feature
    
    def get_by_upload_id(self, upload_id: int) -> Optional[Feature]:
        """
        Получить ОДИН набор признаков для upload_id.
        
        Returns:
            Feature object или None если не найден
        
        Logic: 1 upload_id = 1 Feature (максимум)
        """
        return self.db.query(Feature).filter(
            Feature.upload_id == upload_id
        ).first() 
    
    def get_by_id(self, feature_id: int) -> Optional[Feature]:
        """Получить признаки по ID"""
        return self.db.query(Feature).filter(
            Feature.id == feature_id
        ).first()
    
    def get_all(self) -> list[Feature]:
        """Получить все признаки"""
        return self.db.query(Feature).all()
    
    def update(
        self,
        feature_id: int,
        **kwargs
    ) -> Optional[Feature]:
        """Обновить признаки"""
        feature = self.get_by_id(feature_id)
        if feature:
            for key, value in kwargs.items():
                setattr(feature, key, value)
            self.db.commit()
            self.db.refresh(feature)
        return feature
    
    def delete(self, feature_id: int) -> bool:
        """Удалить признаки"""
        feature = self.get_by_id(feature_id)
        if feature:
            self.db.delete(feature)
            self.db.commit()
            return True
        return False


class ModelVersionRepository:
    """Репозиторий для работы с версиями моделей"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, algorithm: str, version: str, model_file_path: str, **kwargs) -> ModelVersion:
        model = ModelVersion(
            algorithm=algorithm,
            version=version,
            model_file_path=model_file_path,
            **kwargs
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model
    
    def get_by_id(self, model_id: int) -> Optional[ModelVersion]:
        return self.db.query(ModelVersion).get(model_id)
    
    def get_active(self, algorithm: str) -> Optional[ModelVersion]:
        """Получить активную модель для алгоритма"""
        try:
            model = self.db.query(ModelVersion).filter(
            and_(
                ModelVersion.algorithm == algorithm,
                ModelVersion.is_active == True
            )
        ).first()
            if model:
                    logger.info(f"Активная модель найдена: {algorithm} v{model.version}")
            else:
                    logger.warning(f"Активная модель не найдена для: {algorithm}")
                
            return model
        
        except Exception as e:
            logger.error(f"Ошибка при get_active: {e}")
            return None

    def set_active(self, model_id: int) -> bool:
        """Установить модель активной (и деактивировать остальные для этого алгоритма)"""
        model = self.get_by_id(model_id)
        if not model:
            return False
        
        # Деактивировать все модели этого алгоритма
        self.db.query(ModelVersion).filter(
            and_(
                ModelVersion.algorithm == model.algorithm,
                ModelVersion.is_active == True
            )
        ).update({ModelVersion.is_active: False})
        
        # Активировать эту модель
        model.is_active = True
        self.db.commit()
        return True
    
    def list_all(self) -> List[ModelVersion]:
        return self.db.query(ModelVersion).order_by(desc(ModelVersion.created_at)).all()
    
    def list_by_algorithm(self, algorithm: str) -> List[ModelVersion]:
        return self.db.query(ModelVersion).filter(
            ModelVersion.algorithm == algorithm
        ).order_by(desc(ModelVersion.created_at)).all()


class ForecastRepository:
    """Репозиторий для работы с прогнозами"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, upload_id: int, features_id: int, model_version_id: int, **kwargs) -> Forecast:
        forecast = Forecast(
            upload_id=upload_id,
            features_id=features_id,
            model_version_id=model_version_id,
            **kwargs
        )
        self.db.add(forecast)
        self.db.commit()
        self.db.refresh(forecast)
        return forecast
    
    def get_by_id(self, forecast_id: int) -> Optional[Forecast]:
        return self.db.query(Forecast).get(forecast_id)
    
    def get_by_upload_id(self, upload_id: int) -> List[Forecast]:
        return self.db.query(Forecast).filter(
            Forecast.upload_id == upload_id
        ).order_by(desc(Forecast.created_at)).all()
    
    def get_by_features_id(self, features_id: int) -> List[Forecast]:
        return self.db.query(Forecast).filter(
            Forecast.features_id == features_id
        ).order_by(desc(Forecast.created_at)).all()


class AuditLogRepository:
    """Репозиторий для логирования"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, action: str, resource_type: str, **kwargs) -> AuditLog:
        log = AuditLog(action=action, resource_type=resource_type, **kwargs)
        self.db.add(log)
        self.db.commit()
        return log
    
    def get_by_user_id(self, user_id: int, limit: int = 100) -> List[AuditLog]:
        return self.db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(desc(AuditLog.created_at)).limit(limit).all()