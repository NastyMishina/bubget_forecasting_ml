import logging
import os
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.repositories import RawDataUploadRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_DEFAULT_LAGS = [1, 2, 4]
_DEFAULT_WINDOWS = [2, 4]


class DataProcessingService:
    """
    Обработкв данных:

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
    
    def add_lags(self, df: pd.DataFrame, columns: list = None, lags: list = None) -> pd.DataFrame:
        """Добавить лаговые признаки"""
        if lags is None:
            lags = _DEFAULT_LAGS
        
        if df.empty:
            return df.copy()
        
        result = df.copy()
        
        if columns is None:
            numeric_cols = df.select_dtypes(include='number').columns.tolist()
            numeric_cols = [c for c in numeric_cols if c != 'period']
            columns = numeric_cols
        
        for col in columns:
            if col not in result.columns:
                continue
            
            for lag in lags:
                result[f"{col}_lag{lag}"] = result[col].shift(lag)
        
        logger.info(f"add_lags: добавлено {len(columns) * len(lags)} лаговых признаков")
        return result
    
    def add_rolling(self, df: pd.DataFrame, columns: list = None, windows: list = None) -> pd.DataFrame:
        """Добавить скользящие средние"""
        if windows is None:
            windows = _DEFAULT_WINDOWS
        
        if df.empty:
            return df.copy()
        
        result = df.copy()
        
        if columns is None:
            numeric_cols = df.select_dtypes(include='number').columns.tolist()
            numeric_cols = [c for c in numeric_cols if '_lag' not in c and c != 'period']
            columns = numeric_cols
        
        for col in columns:
            if col not in result.columns:
                continue
            
            for w in windows:
                result[f"{col}_roll{w}"] = result[col].rolling(w, min_periods=1).mean()
        
        logger.info(f"add_rolling: добавлено {len(columns) * len(windows)} rolling признаков")
        return result
    
    def add_diff(self, df: pd.DataFrame, columns: list = None, diffs: list = None) -> pd.DataFrame:
        """Добавить разницу между периодами"""
        if diffs is None:
            diffs = [1]
        
        if df.empty:
            return df.copy()
        
        result = df.copy()
        
        if columns is None:
            numeric_cols = df.select_dtypes(include='number').columns.tolist()
            numeric_cols = [c for c in numeric_cols if '_lag' not in c and c != 'period']
            columns = numeric_cols
        
        for col in columns:
            if col not in result.columns:
                continue
            
            for d in diffs:
                result[f"{col}_diff{d}"] = result[col].diff(d)
        
        logger.info(f"add_diff: добавлено {len(columns) * len(diffs)} diff признаков")
        return result
    
    def build_features(self, upload_id: int) -> pd.DataFrame:
        """
        Создание признаков
        
        
        Returns:
            DataFrame с признаками, готовыми для ML модели
        """
        try:
            logger.info(f"build_features: начало для upload_id={upload_id}")
            
        
            raw = self.load_from_db(upload_id)
            
            if raw.empty:
                logger.warning(f"build_features: нет данных для upload_id={upload_id}")
                return raw
            
     
            pivoted = self.pivot_to_wide(raw)
            
          
            indicator_cols = [c for c in pivoted.columns if c != 'period' and c != 'indicator']
            
    
            with_lags = self.add_lags(pivoted, columns=indicator_cols)
            with_rolling = self.add_rolling(with_lags, columns=indicator_cols)
            with_diff = self.add_diff(with_rolling, columns=indicator_cols)
            
            logger.debug(f"build_features: ДО dropna shape={with_diff.shape}")
            
            threshold = int(len(with_diff.columns) * 0.8)  
            final_df = with_diff.dropna(thresh=threshold).reset_index(drop=True)
            
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