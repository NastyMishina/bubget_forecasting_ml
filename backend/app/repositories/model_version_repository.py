# backend/app/repositories/model_version_repository.py
"""ModelVersionRepository — read-only доступ к таблице model_versions."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models import ModelVersion


class ModelVersionRepository:
    """Read-only репозиторий для model_versions.

    Таблица заполняется вручную или через admin-панель.
    Этот репозиторий предназначен только для чтения.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_active(self, algorithm: str) -> Optional[ModelVersion]:
        """Получить активную (is_active=True) версию модели для алгоритма.

        Args:
            algorithm: 'ridge' или 'xgboost'

        Returns:
            ModelVersion или None, если активная модель не найдена.
        """
        return (
            self.db.query(ModelVersion)
            .filter(
                and_(
                    ModelVersion.algorithm == algorithm,
                    ModelVersion.is_active == True,  # noqa: E712
                )
            )
            .first()
        )

    def get_by_id(self, model_id: int) -> Optional[ModelVersion]:
        """Получить версию модели по ID.

        Args:
            model_id: первичный ключ записи.

        Returns:
            ModelVersion или None.
        """
        return (
            self.db.query(ModelVersion)
            .filter(ModelVersion.id == model_id)
            .first()
        )

    def list_all(self) -> list[ModelVersion]:
        """Список всех версий моделей (от новых к старым)."""
        return (
            self.db.query(ModelVersion)
            .order_by(ModelVersion.created_at.desc())
            .all()
        )

    def list_active(self) -> list[ModelVersion]:
        """Список всех активных версий моделей."""
        return (
            self.db.query(ModelVersion)
            .filter(ModelVersion.is_active == True) 
            .order_by(ModelVersion.algorithm)
            .all()
        )
