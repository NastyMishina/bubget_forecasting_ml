import logging
import os
import numpy as np
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.repositories import RawDataUploadRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataProcessingService:
    """
    Обработка данных и создание признаков для ML моделей
    """

    def __init__(self, db: Session):
        self.db = db
        self._raw_data_repo = RawDataUploadRepository(db)
    
    def save_raw_data_from_csv(
        self,
        csv_file_path: str,
        upload_id: int
    ) -> int:
        """
        Загрузить CSV в длинном формате и сохранить в raw_data_uploads
    
        
        Args:
            csv_file_path: Путь к загруженному CSV файлу
            upload_id: ID из таблицы data_uploads
        
        Returns:
            Количество сохраненных записей
        """
        try:
            df = pd.read_csv(csv_file_path, encoding='utf-8', sep=';')
            logger.info(f"save_raw_data_from_csv: загружен CSV shape={df.shape}")
            
            if df.empty:
                raise ValueError("CSV файл пуст")
            

            period_col = df.columns[0]
            indicator_col = df.columns[1]
            value_col = df.columns[2]
            
            logger.info(f"save_raw_data_from_csv: колонки = '{period_col}', '{indicator_col}', '{value_col}'")
            
            df[period_col] = pd.to_datetime(df[period_col], errors='coerce')
            
            if df[period_col].isna().any():
                raise ValueError(f"Невалидные даты в колонке '{period_col}'")
            
  
            df[value_col] = pd.to_numeric(df[value_col], errors='coerce')

            df = (
                        df
                        .groupby([period_col, indicator_col], as_index=False)
                        .agg({value_col: "max"})
                    )
            
            records_inserted = 0
            
            for idx, row in df.iterrows():
                period = row[period_col].date() if pd.notna(row[period_col]) else None
                indicator_name = str(row[indicator_col]).strip()
                value = float(row[value_col]) if pd.notna(row[value_col]) else None
                
         
                if period is None or not indicator_name or value is None:
                    logger.warning(f"save_raw_data_from_csv: пропуск строки {idx} (невалидные данные)")
                    continue
                
                is_duplicate = self._check_duplicate(upload_id, period, indicator_name)


                sql = """
                INSERT INTO raw_data_uploads 
                (upload_id, period, indicator_name, value, source_row, is_duplicate, created_at)
                VALUES (:upload_id, :period, :indicator_name, :value, :source_row, :is_duplicate, NOW())
                """
                
                self.db.execute(text(sql), {
                    'upload_id': upload_id,
                    'period': period,
                    'indicator_name': indicator_name,
                    'value': value,
                    'source_row': idx + 2,
                    'is_duplicate': is_duplicate
                })
                
                records_inserted += 1
            
            self.db.commit()
            logger.info(f"save_raw_data_from_csv: сохранено {records_inserted} записей в БД")
            return records_inserted
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"save_raw_data_from_csv error: {str(e)}")
            raise
    
    def _check_duplicate(self, upload_id: int, period, indicator_name: str) -> bool:
        """Проверить есть ли дубликат в raw_data_uploads"""
        try:
            sql = """
            SELECT COUNT(*) FROM raw_data_uploads
            WHERE upload_id = :upload_id AND period = :period AND indicator_name = :indicator_name
            """
            result = self.db.execute(text(sql), {
                'upload_id': upload_id,
                'period': period,
                'indicator_name': indicator_name
            }).scalar()
            
            return result > 0
        except Exception as e:
            logger.error(f"_check_duplicate error: {str(e)}")
            return False
    
    def load_from_db(self, upload_id: int) -> pd.DataFrame:
        """
        Загрузить raw данные из raw_data_uploads
        
        Returns:
            DataFrame с колонками: period, indicator_name, value
        """
        try:
            rows = self._raw_data_repo.get_by_upload_id(upload_id)
            
            if not rows:
                logger.warning(f"load_from_db: нет данных для upload_id={upload_id}")
                return pd.DataFrame(columns=["period", "indicator_name", "value"])
            
            df = pd.DataFrame([
                {
                    "period": r.period,
                    "indicator_name": r.indicator_name,
                    "value": r.value,
                }
                for r in rows
            ])
            
            df["period"] = pd.to_datetime(df["period"])
            logger.info(f"load_from_db: загружено {len(df)} строк для upload_id={upload_id}")
            return df
        
        except Exception as e:
            logger.error(f"load_from_db error: {str(e)}")
            raise
    
    def pivot_to_wide(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Преобразовать из длинного в широкий формат для создания признаков
        """
        try:
            if df.empty:
                return df.copy()
            
            pivoted = df.pivot_table(
                index="period",
                columns="indicator_name",
                values="value",
                aggfunc="mean"
            )
            pivoted.columns.name = None
            pivoted = pivoted.reset_index().sort_values("period")
            pivoted = pivoted.reset_index(drop=True)
            
            logger.info(f"pivot_to_wide: {len(pivoted)} строк × {len(pivoted.columns)} колонок")
            return pivoted
        
        except Exception as e:
            logger.error(f"pivot_to_wide error: {str(e)}")
            raise

    def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавить лаговые признаки для выбранных колонок с лагами 1 и 4
        
        Обрабатывает:
        - consolidated_revenue, revenue_metals, fx, receivables, inventories (лаги 1, 4)
        - comercil_expenses (лаги 1, 4)
        """
        result = df.copy()
        
        lag_features = [
            "consolidated_revenue",
            "revenue_metals",
            "fx",
            "receivables",
            "inventories"
        ]
        
        for col in lag_features:
            if col in result.columns:
                result[f"{col}_lag_1"] = result[col].shift(1)
                result[f"{col}_lag_4"] = result[col].shift(4)
                logger.debug(f"_add_lag_features: добавлены лаги для {col}")
        
        if "comercil_expenses" in result.columns:
            result["commercial_expenses_lag_4"] = result["comercil_expenses"].shift(4)
            logger.debug(f"_add_lag_features: добавлены лаги для comercil_expenses")
        
        return result

    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавить временные признаки (квартал, год)
        """
        result = df.copy()
        
        if "period" in result.columns:
            result["quarter"] = result["period"].dt.quarter
            result["year"] = result["period"].dt.year
            logger.debug(f"_add_temporal_features: добавлены quarter и year")
        
        return result

    def _add_rolling_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавить скользящие статистики для comercil_expenses
        
        Вычисляет скользящее среднее и стандартное отклонение
        после сдвига на 1 период (lag=1)
        """
        result = df.copy()
        
        if "comercil_expenses" in result.columns:
            shifted = result["comercil_expenses"].shift(1)
            result["rolling_mean_4"] = shifted.rolling(window=4).mean()
            result["rolling_std_4"] = shifted.rolling(window=4).std()
            logger.debug(f"_add_rolling_stats: добавлены rolling mean и std для comercil_expenses")
        
        return result

    def _add_yoy_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавить Year-over-Year (YoY) признаки
        
        YoY = lag_1 / lag_4 (текущий квартал относительно аналога год назад)
        """
        result = df.copy()
        
        # Revenue YoY
        if "revenue_metals_lag_1" in result.columns and "revenue_metals_lag_4" in result.columns:
            result["revenue_yoy"] = result["revenue_metals_lag_1"] / result["revenue_metals_lag_4"]
            logger.debug(f"_add_yoy_features: добавлен revenue_yoy")
        
        # FX YoY
        if "fx_lag_1" in result.columns and "fx_lag_4" in result.columns:
            result["fx_yoy"] = result["fx_lag_1"] / result["fx_lag_4"]
            logger.debug(f"_add_yoy_features: добавлен fx_yoy")
        
        return result

    def _add_log_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавить логарифмические признаки
        
        Логарифмы от: revenue_metals_lag_1, fx_lag_1
        """
        result = df.copy()
        
        if "revenue_metals_lag_1" in result.columns:
            result["log_revenue"] = np.log(result["revenue_metals_lag_1"])
            logger.debug(f"_add_log_features: добавлен log_revenue")
        
        if "fx_lag_1" in result.columns:
            result["log_fx"] = np.log(result["fx_lag_1"])
            logger.debug(f"_add_log_features: добавлен log_fx")
        
        return result

    def _add_growth_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавить признаки роста и изменений
        
        - growth_log_revenue: дифференциация log_revenue
        - growth_fx: отношение текущего к предыдущему периоду (темп роста)
        """
        result = df.copy()
        
        if "log_revenue" in result.columns:
            result["growth_log_revenue"] = result["log_revenue"].diff()
            logger.debug(f"_add_growth_features: добавлен growth_log_revenue")
        
        if "fx_lag_1" in result.columns:
            result["growth_fx"] = result["fx_lag_1"] / result["fx_lag_1"].shift(1)
            logger.debug(f"_add_growth_features: добавлен growth_fx")
        
        return result

    def _clean_infinite_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Заменить бесконечные значения на NaN
        
        Возникают при делении на ноль или логарифме отрицательных чисел
        """
        result = df.copy()
        result.replace([np.inf, -np.inf], np.nan, inplace=True)
        logger.debug(f"_clean_infinite_values: заменены бесконечные значения")
        return result
    
    def _add_forecast_row(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавить строку для прогноза
        
        Создает новую строку, используя последние доступные значения
        для создания лагов.
        
        Args:
            df: DataFrame в широком формате с историческими данными
        
        Returns:
            DataFrame с добавленной строкой для прогноза
        """
        try:
            if df.empty:
                logger.warning("_add_forecast_row: DataFrame пуст, добавление пропущено")
                return df
            
            df["period"] = pd.to_datetime(df["period"], dayfirst=True)

            last_period = df["period"].max()

            next_period = last_period + pd.offsets.QuarterEnd()
            
            forecast_row = pd.DataFrame({
                col: [0] if col != 'period' else next_period
                for col in df.columns
            })
            
            result = pd.concat([df, forecast_row], ignore_index=True)
            
            logger.info(f"_add_forecast_row: добавлена строка для 31.03.2024, новый shape={result.shape}")
            return result
        
        except Exception as e:
            logger.error(f"_add_forecast_row error: {str(e)}")
            raise

    def build_features(self, upload_id: int, include_forecast: bool = True) -> pd.DataFrame:
        """
        Создание признаков для ML моделей
        
        Этапы:
        1. Загрузить raw данные
        2. Преобразовать в широкий формат и добавить строку для реального предсказания
        3. Добавить лаговые признаки
        4. Добавить временные признаки
        5. Добавить скользящие статистики
        6. Добавить YoY признаки
        7. Добавить логарифмические признаки
        8. Добавить признаки роста
        9. Очистить бесконечные значения
        10. Удалить строки с пропусками
        
        Returns:
            DataFrame с признаками, готовыми для ML модели
        """
        try:
            logger.info(f"build_features: начало для upload_id={upload_id}")
            
            # 1. Загрузить raw данные
            raw = self.load_from_db(upload_id)
            
            if raw.empty:
                logger.warning(f"build_features: нет данных для upload_id={upload_id}")
                return raw
            
            # 2. Преобразовать в широкий формат
            df = self.pivot_to_wide(raw)
            logger.debug(f"build_features: после pivot shape={df.shape}")

            if include_forecast:
                df = self._add_forecast_row(df)
                logger.debug(f"build_features: после добавления прогноза shape={df.shape}")
            
            # 3. Добавить лаговые признаки
            df = self._add_lag_features(df)
            logger.debug(f"build_features: после лагов shape={df.shape}")
            
            # 4. Добавить временные признаки
            df = self._add_temporal_features(df)
            
            # 5. Добавить скользящие статистики
            df = self._add_rolling_stats(df)
            logger.debug(f"build_features: после rolling shape={df.shape}")
            
            # 6. Добавить YoY признаки
            df = self._add_yoy_features(df)
            
            # 7. Добавить логарифмические признаки
            df = self._add_log_features(df)
            
            # 8. Добавить признаки роста
            df = self._add_growth_features(df)
            logger.debug(f"build_features: после growth features shape={df.shape}")
            
            # 9. Очистить бесконечные значения
            df = self._clean_infinite_values(df)
            
            # 10. Удалить строки с пропусками
            logger.debug(f"build_features: ДО dropna shape={df.shape}")
            final_df = df.dropna().reset_index(drop=True)
            
            
            logger.info(f"build_features: итоговый датасет {len(final_df)} строк × {len(final_df.columns)} колонок")
            
            return final_df
        
        except Exception as e:
            logger.error(f"build_features error: {str(e)}")
            raise
    
    def save_features_csv(self, df: pd.DataFrame, upload_id: int) -> str:
        """
        Сохранить файл с признаками на сервер
        
        Args:
            df: DataFrame с признаками
            upload_id: ID загрузки (для имени файла)
        
        Returns:
            Путь к сохраненному файлу (относительно data/features/)
        """
        try:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            FEATURES_DIR = os.path.join(BASE_DIR, "data", "features")
            os.makedirs(FEATURES_DIR, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"features_{timestamp}_upload_{upload_id}.csv"
            filepath = os.path.join(FEATURES_DIR, filename)
            
            df.to_csv(filepath, index=False)
            logger.info(f"save_features_csv: сохранено в {filepath}")
            
            return filepath
        
        except Exception as e:
            logger.error(f"save_features_csv error: {str(e)}")
            raise
    
    def create_and_save_features(self, upload_id: int) -> str:
        """
        КОМБО ФУНКЦИЯ:
        1. Построить признаки (build_features)
        2. Сохранить на сервер (save_features_csv)
        
        Returns:
            Полный путь к файлу признаков
        """
        try:
            logger.info(f"create_and_save_features: начало для upload_id={upload_id}")
            
            features_df = self.build_features(upload_id)
            
            if features_df.empty:
                raise ValueError(f"Не удалось создать признаки для upload_id={upload_id}")
            
            features_path = self.save_features_csv(features_df, upload_id)
            
            logger.info(f"create_and_save_features: успешно для upload_id={upload_id}")
            return features_path
        
        except Exception as e:
            logger.error(f"create_and_save_features error: {str(e)}")
            raise
    
    def get_upload_stats(self, upload_id: int) -> dict:
        """Получить статистику по загруженным данным"""
        try:
            sql = """
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT indicator_name) as unique_indicators,
                COUNT(DISTINCT period) as unique_periods,
                MIN(period) as period_from,
                MAX(period) as period_to,
                COUNT(CASE WHEN value IS NULL THEN 1 END) as null_values
            FROM raw_data_uploads
            WHERE upload_id = :upload_id
            """
            
            result = self.db.execute(
                text(sql),
                {'upload_id': upload_id}
            ).fetchone()
            
            if result:
                return {
                    'total_records': result[0],
                    'unique_indicators': result[1],
                    'unique_periods': result[2],
                    'period_from': str(result[3]) if result[3] else None,
                    'period_to': str(result[4]) if result[4] else None,
                    'null_values': result[5],
                }
            else:
                return {}
        
        except Exception as e:
            logger.error(f"get_upload_stats error: {str(e)}")
            return {}
