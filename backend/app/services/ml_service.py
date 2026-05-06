import logging
import pickle
import os
import numpy as np
import pandas as pd
import json
from typing import Tuple, List
from sqlalchemy.orm import Session
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor
from sklearn.linear_model import Ridge

logger = logging.getLogger(__name__)


class MLService:
    """Сервис для использования предобученных ML моделей"""
    
    def __init__(self, models_dir: str = None):
        if models_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            models_dir = os.path.join(base_dir, "data", "models")
        self.models_dir = models_dir


    def load_top_features(self, features_json: str = "top_10_features.json") -> List[str]:
        """
        Загрузить список top 10 сохраненных признаков.
        
        Args:
            features_json: Название JSON файла со списком признаков
        
        Returns:
            Список top 10 признаков
        """
        try:
            logger.info(f"load_top_features: загрузка из {features_json}")
            
            filepath = os.path.join(self.models_dir, features_json)
            
            if not os.path.exists(filepath):
                logger.error(f"Файл не найден: {filepath}")
                raise FileNotFoundError(f"Features file not found: {filepath}")
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            top_features = data.get("top_10_features", [])
            
            logger.info(f"load_top_features: загружено {len(top_features)} признаков")
            logger.debug(f"   {top_features}")
            
            return top_features
        
        except Exception as e:
            logger.error(f"load_top_features error: {str(e)}", exc_info=True)
            raise
    
    def load_final_model(self, model_pkl: str = "final_model.pkl"):
        """
        Загрузить обученную модель из pickle файла.
        
        Args:
            model_pkl: Название pickle файла с моделью
        
        Returns:
            Загруженная модель (XGBoost или Ridge)
        """
        try:
            logger.info(f"load_final_model: загрузка из {model_pkl}")
            
            filepath = os.path.join(self.models_dir, model_pkl)
            
            if not os.path.exists(filepath):
                logger.error(f"Файл не найден: {filepath}")
                raise FileNotFoundError(f"Model file not found: {filepath}")
            
            with open(filepath, 'rb') as f:
                model = pickle.load(f)
            
            logger.info(f"load_final_model: модель загружена")
            logger.info(f"   Тип: {type(model).__name__}")
            
            return model
        
        except Exception as e:
            logger.error(f"load_final_model error: {str(e)}", exc_info=True)
            raise

    def filter_by_top_features(
        self,
        features_df: pd.DataFrame,
        top_features: List[str]
    ) -> pd.DataFrame:
        """
        Фильтровать DataFrame - оставить только top признаки.
        
        Args:
            features_df: Исходный DataFrame
            top_features: Список selected признаков
        
        Returns:
            Отфильтрованный DataFrame
        """
        try:
            logger.info(f"filter_by_top_features: фильтрация до {len(top_features)} признаков")
            logger.debug(f"Ожидаемые признаки: {top_features}")
            logger.debug(f"Доступные признаки в DataFrame: {features_df.columns.tolist()}")
            
            cols_to_keep = ['period'] + top_features
            missing_features = [c for c in top_features if c not in features_df.columns]
        
            if missing_features:
                logger.error(f"Отсутствуют следующие признаки: {missing_features}")
                raise ValueError(f"Missing required features: {missing_features}")
            
            cols_to_keep = [c for c in cols_to_keep if c in features_df.columns]
            
            filtered_df = features_df[cols_to_keep].copy()
            
            logger.info(f"filter_by_top_features завершена")
            logger.info(f"   Было: {features_df.shape}")
            logger.info(f"   Стало: {filtered_df.shape}")

            if filtered_df.shape[1] - 1 != len(top_features):
                logger.warning(f"Ожидалось {len(top_features)} признаков, получено {filtered_df.shape[1] - 1}")
            
            return filtered_df
        
        except Exception as e:
            logger.error(f"filter_by_top_features error: {str(e)}", exc_info=True)
            raise

    
    def predict(
        self,
        model,
        features_df: pd.DataFrame
    ) -> np.ndarray:
        """
        Сделать прогноз с помощью загруженной модели.
        
        Args:
            model: Загруженная обученная модель
            features_df: DataFrame с признаками (только top 10!)
        
        Returns:
            Массив с прогнозами
        """
        try:
            logger.info(f"predict: прогноз на {features_df.shape[0]} образцов")
            
            X = features_df.drop(columns=['period'], errors='ignore').values
            
            predictions = model.predict(X)
            predictions = np.clip(predictions, 25.035, None)

            logger.info(f"predict: получено {len(predictions)} прогнозов")
            logger.debug(f"Примеры: {predictions[:5]}")
            
            return predictions
        
        except Exception as e:
            logger.error(f"predict error: {str(e)}", exc_info=True)
            raise
    
    def generate_scenarios(
        self,
        base_predictions: np.ndarray,
        optimistic_percent: float = 10.0,
        pessimistic_percent: float = -10.0,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Создать 3 сценария из одного прогноза"""
        optimistic = base_predictions * (1 + optimistic_percent / 100)
        pessimistic = base_predictions * (1 + pessimistic_percent / 100)
        
        logger.info("generate_scenarios: создано 3 сценария")
        return base_predictions, optimistic, pessimistic
    
    
    def save_forecast_csv(
        self,
        periods: list,
        base: np.ndarray,
        optimistic: np.ndarray,
        pessimistic: np.ndarray,
        upload_id: int,
    ) -> Tuple[str, str, str]:
        """
        Сохранить 3 сценария в отдельные CSV файлы с форматированием.
        
        Формат файла:
        period;prediction
        30.06.2022;56.036
        """
        from datetime import datetime
        
        try:
            logger.info("save_forecast_csv: начало сохранения")
            
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            DATA_DIR = os.path.join(BASE_DIR, "data")
            FORECAST_DIR = os.path.join(DATA_DIR, "forecasts")
            os.makedirs(FORECAST_DIR, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Форматировать периоды в DD.MM.YYYY
            formatted_periods = self._format_periods(periods)
            logger.info(f"Периоды отформатированы: {formatted_periods[:3]}")
            
            # Базовый прогноз
            df_base = pd.DataFrame({
                'period': formatted_periods,
                'prediction': base
            })
            path_base = os.path.join(
                FORECAST_DIR,
                f"forecast_{timestamp}_upload_{upload_id}_base.csv"
            )
            df_base.to_csv(path_base, index=False, sep=';')
            logger.info(f"Базовый прогноз сохранен: {path_base}")
            
            # Оптимистичный прогноз
            df_opt = pd.DataFrame({
                'period': formatted_periods,
                'prediction': optimistic
            })
            path_opt = os.path.join(
                FORECAST_DIR,
                f"forecast_{timestamp}_upload_{upload_id}_optimistic.csv"
            )
            df_opt.to_csv(path_opt, index=False, sep=';')
            logger.info(f"Оптимистичный прогноз сохранен: {path_opt}")
            
            # Пессимистичный прогноз
            df_pes = pd.DataFrame({
                'period': formatted_periods,
                'prediction': pessimistic
            })
            path_pes = os.path.join(
                FORECAST_DIR,
                f"forecast_{timestamp}_upload_{upload_id}_pessimistic.csv"
            )
            df_pes.to_csv(path_pes, index=False, sep=';')
            logger.info(f"Пессимистичный прогноз сохранен: {path_pes}")
            
            logger.info("save_forecast_csv: все файлы успешно сохранены")
            return path_base, path_opt, path_pes
        
        except Exception as e:
            logger.error(f"save_forecast_csv error: {str(e)}", exc_info=True)
            raise


    def _format_periods(self, periods: list) -> list:
        """
        Преобразовать периоды в формат DD.MM.YYYY
        
        Args:
            periods: Список периодов (строки в любом формате или объекты Timestamp)
        
        Returns:
            Список периодов в формате DD.MM.YYYY
        """
        formatted = []
        
        for period in periods:
            try:
                if isinstance(period, str):
                    date_obj = None
                    
                    try:
                        date_obj = pd.to_datetime(period, format='%Y-%m-%d')
                    except:
                        pass
                    if date_obj is None:
                        try:
                            date_obj = pd.to_datetime(period, format='%Y-%m')
                        except:
                            pass
                    if date_obj is None:
                        date_obj = pd.to_datetime(period)
                else:

                    date_obj = pd.to_datetime(period)
                formatted_date = date_obj.strftime('%d.%m.%Y')
                formatted.append(formatted_date)
            
            except Exception as e:
                logger.warning(f"Не удалось отформатировать период '{period}': {e}")
                formatted.append(str(period))
        
        return formatted