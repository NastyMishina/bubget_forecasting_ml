# backend/app/api/routes/forecasts.py
"""API эндпоинты для прогнозирования с предобученными моделями."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Forecast
from app.repositories import (
    DataUploadRepository, FeatureRepository, 
    ModelVersionRepository, ForecastRepository
)
from app.services.ml_service import MLService
from app.services.data_processing import DataProcessingService
from app.services.decomposition_service import TimeSeriesDecompositionService
from app.schemas import ForecastResponseSchema


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])


@router.post("/predict/{upload_id}")
async def predict(
    upload_id: int,
    target_column: str = "target_kommerskie_rashody",
    db: Session = Depends(get_db),
):
    """
    Сделать прогноз  на загруженных данных.
    
    Процесс:
    1. Загрузить CSV
    2. Загрузить сохраненный список top 10 признаков
    3. Фильтровать CSV - оставить только top 10
    4. Загрузить обученную модель
    5. Сделать прогноз
    6. Создать 3 сценария
    7. Сохранить результаты
    
    Query параметры:
    - target_column: Используется только для названия (тек данные БЕЗ этого столбца!)
    
    Пример:
    POST /api/forecasts/predict/1?target_column=target_kommerskie_rashody
    """
    try:
        logger.info(f"predict: начало (новые данные БЕЗ target)")
        logger.info(f"upload_id={upload_id}")
        logger.info(f"target_column={target_column} (для референции)")

        upload_repo = DataUploadRepository(db)
        upload = upload_repo.get_by_id(upload_id)
        
        if not upload:
            logger.error(f"Upload не найден")
            raise HTTPException(status_code=404, detail="Upload not found")
        
        logger.debug(f"Upload найден: {upload.filename}")
        
        feature_repo = FeatureRepository(db)
        features = feature_repo.get_by_upload_id(upload_id)
        
        if not features:
            logger.error(f"Features не найдены")
            raise HTTPException(status_code=400, detail="Features not found")
        
        logger.debug(f"Features найдены")
        
        try:
            features_df = pd.read_csv(features.features_file_path)
            logger.info(f"   Shape: {features_df.shape}")
            logger.debug(f"   Колонки: {list(features_df.columns)}")
        except Exception as e:
            logger.error(f"Ошибка загрузки CSV: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to load features: {str(e)}")
        
        if 'period' not in features_df.columns:
            logger.error(f"Колонка 'period' не найдена в CSV")
            raise HTTPException(status_code=400, detail="Column 'period' not found in data")
        
        try:
            periods = features_df['period'].astype(str).tolist()
            logger.info(f"Периоды загружены из CSV: {len(periods)} значений")
            logger.debug(f"   Примеры: {periods[:3]}")
        except Exception as e:
            logger.error(f"Ошибка извлечения периодов: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to extract periods: {str(e)}")
        
        ml_service = MLService()
        
        try:
            top_features = ml_service.load_top_features("top_10_features.json")
            logger.info(f"Top 10 признаков загружены")
            logger.debug(f"   {top_features}")
        except Exception as e:
            logger.error(f"Ошибка загрузки признаков: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to load features list: {str(e)}")
        
        logger.info(f"Фильтрация CSV по top 10...")
        try:
            filtered_features_df = ml_service.filter_by_top_features(features_df, top_features)
            logger.info(f"CSV отфильтрован")
        except Exception as e:
            logger.error(f"Ошибка фильтрации: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to filter features: {str(e)}")
        
        logger.info(f"Загрузка обученной модели")
        try:
            model = ml_service.load_final_model("final_model.pkl")
            logger.info(f"Модель загружена")
            logger.info(f"   Тип: {type(model).__name__}")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to load model: {str(e)}")
        
        logger.info(f"Расчет прогноза")
        try:
            predictions = ml_service.predict(model, filtered_features_df)
            logger.info(f"Прогноз получен: {len(predictions)} значений")
        except Exception as e:
            logger.error(f"Ошибка прогноза: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to predict: {str(e)}")
        
        logger.info(f"Создаются сценарии...")
        try:
            base, optimistic, pessimistic = ml_service.generate_scenarios(predictions)
            logger.info(f"Сценарии созданы")
        except Exception as e:
            logger.error(f"Ошибка сценариев: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to generate scenarios: {str(e)}")
        
        logger.info(f"Сохранить прогнозы в CSV.")
        try:
            path_base, path_opt, path_pes = ml_service.save_forecast_csv(
                periods, base, optimistic, pessimistic, upload_id
            )
            logger.info(f"Прогнозы сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to save forecasts: {str(e)}")
        
        logger.info(f"Сохраняю в БД...")
        try:
            forecast_repo = ForecastRepository(db)
            forecast = forecast_repo.create(
                upload_id=upload_id,
                features_id=features.id,
                model_version_id=1,
                target_column=target_column,
                base_forecast_path=path_base,
                optimistic_forecast_path=path_opt,
                pessimistic_forecast_path=path_pes,
                status="completed"
            )
            logger.info(f"Forecast сохранен в БД")
        except Exception as e:
            logger.error(f"Ошибка сохранения в БД: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to save to DB: {str(e)}")
                
        return {
            "forecast_id": forecast.id,
            "upload_id": upload_id,
            "target_column": target_column,
            "periods": periods, 
            "model_info": {
                "type": "Обученная модель (XGBoost или Ridge)",
                "features_used": 10,
                "top_10_features": top_features
            },
            "predictions": {
                "base": base.tolist(),
                "optimistic": optimistic.tolist(),
                "pessimistic": pessimistic.tolist(),
            },
            "forecast_paths": {
                "base": path_base,
                "optimistic": path_opt,
                "pessimistic": path_pes,
            },
            "status": "completed"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/forecasts/{forecast_id}")
async def get_forecast(forecast_id: int, db: Session = Depends(get_db)):
    """Получить информацию о прогнозе"""
    repo = ForecastRepository(db)
    forecast = repo.get_by_id(forecast_id)
    
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    return {
        "id": forecast.id,
        "upload_id": forecast.upload_id,
        "features_id": forecast.features_id,
        "model_version_id": forecast.model_version_id,
        "target_column": forecast.target_column,
        "forecast_paths": {
            "base": forecast.base_forecast_path,
            "optimistic": forecast.optimistic_forecast_path,
            "pessimistic": forecast.pessimistic_forecast_path,
        },
        "created_at": forecast.created_at,
    }



@router.get("/")
async def list_forecasts(
    upload_id: Optional[int] = Query(None, description="Фильтр по upload_id"),
    db: Session = Depends(get_db),
):
    """Получить список прогнозов, опционально фильтруя по upload_id."""
    q = db.query(Forecast)
    if upload_id is not None:
        q = q.filter(Forecast.data_upload_id == upload_id)
    forecasts = q.order_by(Forecast.created_at.desc()).all()

    return [
        {
            "forecast_id": f.id,
            "upload_id": f.data_upload_id,
            "algorithm": f.selected_algorithm,
            "target_column": f.target_column,
            "mae": f.mae,
            "rmse": f.rmse,
            "r2_score": f.r2_score,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in forecasts
    ]


@router.get("/{forecast_id}/chart-data")
async def get_chart_data(forecast_id: int, db: Session = Depends(get_db)):
    """Получить данные для графика трёх сценариев.

    Returns:
        JSON с ключами periods, base, optimistic, pessimistic.
    """
    forecast = db.query(Forecast).filter(Forecast.id == forecast_id).first()
    if not forecast:
        raise HTTPException(status_code=404, detail=f"Прогноз {forecast_id} не найден")

    results_by_scenario: dict[str, Forecast] = {
        r.scenario_type: r for r in forecast.results
    }

    required = ("base", "optimistic", "pessimistic")
    missing = [s for s in required if s not in results_by_scenario]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Отсутствуют сценарии: {missing}",
        )
    chart: dict[str, list] = {
        "periods": [], 
        "base": [], 
        "optimistic": [], 
        "pessimistic": []
    }

    base_path = results_by_scenario["base"].forecast_file_path
    if base_path:
        try:
            base_df = pd.read_csv(base_path, sep=';')
            
            chart["periods"] = base_df["period"].astype(str).tolist()
            
            logger.info(f"Периоды загружены: {chart['periods'][:3]}")
        except Exception as e:
            logger.error(f"Ошибка загрузки периодов: {e}")
            chart["periods"] = []

    for scenario in required:
        result = results_by_scenario[scenario]
        if result.forecast_file_path:
            try:
                df = pd.read_csv(result.forecast_file_path, sep=';')
                

                chart[scenario] = df["prediction"].tolist()
                
                logger.info(f"Сценарий '{scenario}' загружен: {len(df)} значений")
            except Exception as e:
                logger.error(f"Ошибка загрузки {scenario}: {e}")

                try:
                    chart[scenario] = json.loads(result.prediction_data)
                except Exception:
                    chart[scenario] = []
        else:
            try:
                chart[scenario] = json.loads(result.prediction_data)
            except Exception:
                chart[scenario] = []

    return chart



@router.post("/decompose/{upload_id}")
async def decompose_data(
    upload_id: int,
    period: int = 4,
    model: str = "additive",
    db: Session = Depends(get_db),
):
    """
    Декомпозиция временных рядов для всех чистых признаков загрузки.

    Загружает CSV с признаками (из таблицы features), отбирает
    «чистые» колонки (без lag/roll/diff), выполняет seasonal_decompose
    и сохраняет PNG-графики (4 подграфика: Observed, Trend, Seasonal, Residual).

    Args:
        upload_id: ID загрузки данных.
        period: период сезонности (default=4, квартальный).
        model: модель разложения (default='additive').

    Returns:
        JSON с upload_id, количеством разложенных признаков и путями к PNG.
    """
    import time
    start_time = time.time()

    logger.info(
        "decompose_data: upload_id=%d, period=%d, model=%s",
        upload_id, period, model,
    )

    upload_repo = DataUploadRepository(db)
    upload = upload_repo.get_by_id(upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail=f"Загрузка {upload_id} не найдена")

    feature_repo = FeatureRepository(db)
    features_list = feature_repo.get_by_upload_id(upload_id)
    if not features_list:
        raise HTTPException(
            status_code=400,
            detail=(
                "Признаки не сгенерированы. "
                "Сначала вызовите POST /api/data/process/{upload_id}"
            ),
        )

    feature_record = features_list[-1]
    features_path: str = feature_record.features_file_path

    try:
        features_df = pd.read_csv(features_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Файл признаков не найден: {features_path}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка чтения файла признаков: {exc}",
        )

    if features_df.empty:
        raise HTTPException(status_code=400, detail="Файл признаков пустой")
    
    svc = TimeSeriesDecompositionService()
    try:
        result = svc.decompose_raw_features(
            df=features_df,
            upload_id=upload_id,
            period=period,
            model=model,
        )
    except Exception as exc:
        logger.error("decompose_data: ошибка декомпозиции: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка декомпозиции: {exc}")

    elapsed = round(time.time() - start_time, 2)
    logger.info(
        "decompose_data: завершено за %.2f сек, признаков=%d",
        elapsed,
        result["features_decomposed"],
    )

    return {
        "upload_id": upload_id,
        "features_source": features_path,
        "period": period,
        "model": model,
        "processing_time": elapsed,
        "decomposition": {
            "features_decomposed": result["features_decomposed"],
            "plot_paths": result["plot_paths"],
            "errors": result["errors"],
        },
    }