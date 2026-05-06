# backend/app/services/model_loader.py
"""ModelLoader — управление загруженными предобученными моделями в памяти."""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.repositories import ModelVersionRepository
from app.services.ml_service import MLService

logger = logging.getLogger(__name__)


class ModelLoader:
    """Кэш предобученных ML-моделей.

    Загружает модели по запросу из .pkl файлов и хранит в памяти.
    Повторные вызовы возвращают уже загруженную копию без чтения диска.

    Пример использования:
        loader = ModelLoader()
        model = loader.load_active_model(db, "ridge")
        predictions = model.predict(X)
    """

    def __init__(self) -> None:
        self._models: dict[str, Any] = {}  
        self._ml_service = MLService()


    def get_model(self, algorithm: str) -> Optional[Any]:
        """Вернуть модель из кэша без обращения к БД/диску.

        Args:
            algorithm: 'ridge' или 'xgboost'.

        Returns:
            Объект модели или None, если не загружена.
        """
        return self._models.get(algorithm)

    def load_active_model(self, db: Session, algorithm: str) -> Any:
        """Получить активную модель: из кэша или загрузить из файла.

        Args:
            db: SQLAlchemy Session для запроса к model_versions.
            algorithm: 'ridge' или 'xgboost'.

        Returns:
            Объект модели с методом .predict().

        Raises:
            ValueError: если активная модель не найдена в БД.
            FileNotFoundError: если .pkl файл отсутствует.
        """
        cached = self._models.get(algorithm)
        if cached is not None:
            logger.debug("load_active_model: возврат из кэша для '%s'", algorithm)
            return cached

        return self.load_model_from_db(db, algorithm)

    def load_model_from_db(self, db: Session, algorithm: str) -> Any:
        """Загрузить активную модель по информации из БД и закэшировать.

        Args:
            db: SQLAlchemy Session.
            algorithm: 'ridge' или 'xgboost'.

        Returns:
            Объект модели.

        Raises:
            ValueError: если активная запись в model_versions не найдена.
            FileNotFoundError: если файл модели не существует.
        """
        repo = ModelVersionRepository(db)
        version = repo.get_active(algorithm)

        if version is None:
            raise ValueError(
                f"Активная модель для алгоритма '{algorithm}' не найдена в БД. "
                "Добавьте запись в таблицу model_versions с is_active=True."
            )

        logger.info(
            "load_model_from_db: загружаем %s %s из %s",
            algorithm,
            version.version,
            version.model_file_path,
        )

        model = self._ml_service.load_model(version.model_file_path)
        self._models[algorithm] = model
        return model

    def initialize(self, db: Session) -> None:
        """Предзагрузить все активные модели из БД при старте приложения.

        Args:
            db: SQLAlchemy Session.
        """
        repo = ModelVersionRepository(db)
        active_versions = repo.list_active()

        if not active_versions:
            logger.warning("initialize: активных моделей не найдено в БД")
            return

        for version in active_versions:
            try:
                model = self._ml_service.load_model(version.model_file_path)
                self._models[version.algorithm] = model
                logger.info(
                    "initialize: загружена модель '%s' %s",
                    version.algorithm,
                    version.version,
                )
            except (FileNotFoundError, ValueError) as exc:
                logger.error(
                    "initialize: не удалось загрузить модель '%s': %s",
                    version.algorithm,
                    exc,
                )

        logger.info("initialize: загружено %d моделей", len(self._models))

    def clear_cache(self) -> None:
        """Очистить кэш моделей (для тестирования и hot-reload)."""
        self._models.clear()
        logger.info("clear_cache: кэш очищен")

    @property
    def loaded_algorithms(self) -> list[str]:
        """Список алгоритмов, чьи модели сейчас в кэше."""
        return list(self._models.keys())
