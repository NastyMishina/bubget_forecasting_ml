# backend/app/services/__init__.py
"""Сервисы для бизнес-логики"""

import pandas as pd
import json
import datetime
import os
import logging
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile

logger = logging.getLogger(__name__)


class FileService:
    """Сервис для работы с файлами"""
    
    def __init__(self):
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.upload_dir = os.path.join(BASE_DIR, "data", "uploads")
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def save_upload(self, file: UploadFile, user_id: int) -> Tuple[str, int]:
        """
        Сохранить загруженный файл на сервер
        
        ИСПРАВЛЕНО: Теперь возвращает (file_path, file_size) кортеж!
        
        Args:
            file: UploadFile объект
            user_id: ID пользователя
        
        Returns:
            (file_path, file_size) - кортеж пути и размера файла
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_user_{user_id}_{file.filename}"
        file_path = os.path.join(self.upload_dir, filename)
        
        # Прочитать содержимое файла
        content = await file.read()
        
        # Сохранить на диск
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Получить размер
        file_size = len(content)
        
        logger.info(f"save_upload: файл сохранен {file_path} ({file_size} bytes)")
        
        # Возвращаем оба значения
        return file_path, file_size
    
    def validate_file(self, file_path: str) -> dict:
        """
        Валидировать CSV/XLSX файл
        
        ИСПРАВЛЕНО: Теперь проверяет правильный формат (ДЛИННЫЙ)!
        
        Входной CSV должен быть в ДЛИННОМ формате:
        период, наименование_показателя, значение
        2024-01, доход, 1000
        2024-01, расход, 500
        
        Returns:
            {
                "is_valid": bool,
                "row_count": int,
                "columns": list,
                "errors": list[str]
            }
        """
        errors = []
        row_count = 0
        columns = []
        
        try:
            # Загрузить файл
            if file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8', sep=';')
            else:
                errors.append("Неподдерживаемый формат файла (только .xlsx и .csv)")
                return {
                    "is_valid": False,
                    "row_count": 0,
                    "columns": [],
                    "errors": errors,
                }
            
            row_count = len(df)
            columns = df.columns.tolist()
            
            logger.info(f"validate_file: загружен файл shape={df.shape}")
            
            # Проверяем что CSV в длинном формате
            # Должны быть 3 колонки: период, indicator_name, value
            
            if len(columns) < 3:
                errors.append(f"Файл должен содержать минимум 3 колонки (период, наименование, значение), найдено {len(columns)}")
            
            # Проверить что первая колонка - период/дата
            first_col_lower = str(columns[0]).lower() if columns else ""
            if 'period' not in first_col_lower and 'дата' not in first_col_lower and 'date' not in first_col_lower:
                errors.append(f"Первая колонка должна быть датой/периодом, найдена '{columns[0] if columns else 'N/A'}'")
            
            # Проверить минимальное количество строк
            if row_count < 2:
                errors.append("Файл должен содержать минимум 2 строки данных")
            
            # Проверить пропуски
            missing_count = df.isnull().sum().sum()
            if missing_count > 0:
                logger.warning(f"validate_file: найдено {missing_count} пропусков")
            
            # Проверить дубликаты
            duplicate_count = df.duplicated().sum()
            if duplicate_count > 0:
                logger.warning(f"validate_file: найдено {duplicate_count} дубликатов")
            
            is_valid = len(errors) == 0
            
            logger.info(f"validate_file: {'✓ валидация успешна' if is_valid else '✗ валидация не прошла'}")
            
            return {
                "is_valid": is_valid,
                "row_count": row_count,
                "columns": columns,
                "errors": errors,
            }
        
        except Exception as e:
            logger.error(f"validate_file error: {str(e)}")
            return {
                "is_valid": False,
                "row_count": 0,
                "columns": [],
                "errors": [f"Ошибка при чтении файла: {str(e)}"],
            }
    
    def load_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        Загрузить данные из файла в DataFrame
        
        Args:
            file_path: Путь к файлу
        
        Returns:
            DataFrame или None если ошибка
        """
        try:
            if file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path)
                logger.info(f"load_data: загружены данные из XLSX shape={df.shape}")
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8', sep=';')
                logger.info(f"load_data: загружены данные из CSV shape={df.shape}")
            else:
                raise ValueError(f"Неподдерживаемый формат: {file_path}")
            
            return df
        
        except Exception as e:
            logger.error(f"load_data error: {str(e)}")
            return None
    
    def get_file_info(self, file_path: str) -> dict:
        """
        Получить информацию о файле
        
        Args:
            file_path: Путь к файлу
        
        Returns:
            Словарь с информацией о файле
        """
        try:
            if not os.path.exists(file_path):
                return {"error": f"Файл не найден: {file_path}"}
            
            file_size = os.path.getsize(file_path)
            df = self.load_data(file_path)
            
            if df is None:
                return {"error": "Не удалось загрузить файл"}
            
            return {
                "file_size": file_size,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
            }
        
        except Exception as e:
            logger.error(f"get_file_info error: {str(e)}")
            return {"error": str(e)}
    
    def delete_file(self, file_path: str) -> bool:
        """
        Удалить файл
        
        Args:
            file_path: Путь к файлу
        
        Returns:
            True если успешно, False если ошибка
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"delete_file: файл удален {file_path}")
                return True
            logger.warning(f"delete_file: файл не найден {file_path}")
            return False
        
        except Exception as e:
            logger.error(f"delete_file error: {str(e)}")
            return False


try:
    from app.services.data_processing import DataProcessingService
    logger.info("DataProcessingService загружена успешно")
except ImportError as e:
    logger.error(f"Ошибка при импорте DataProcessingService: {e}")
    DataProcessingService = None

__all__ = ['FileService', 'DataProcessingService']