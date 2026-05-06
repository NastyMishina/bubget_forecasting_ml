# backend/app/api/routes/__init__.py
"""API эндпоинты для загрузки данных и создания признаков"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Query
import logging
import pandas as pd
import datetime
import time
import base64
import os
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import DataUploadRepository, RawDataUploadRepository, FeatureRepository
from app.services import FileService, DataProcessingService
from app.services.decomposition_service import TimeSeriesDecompositionService
from app.models import DataUpload
from app.config import get_settings
from app.auth import get_current_user
from app.models import User

logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("/upload")
async def upload_data(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Загрузить CSV файл в ДЛИННОМ формате
    
    POST /api/data/upload?user_id=1
    
    ВАЖНО: Входной CSV ВСЕГДА в ДЛИННОМ формате!
    Колонки: период, наименование_показателя, значение
    
    Пример:
    период,наименование_показателя,значение
    2024-01,доход,1000
    2024-01,расход,500
    2024-02,доход,1100
    2024-02,расход,550
    
    Шаги:
    1. Сохранить CSV на сервер (data/uploads/)
    2. Валидировать файл
    3. Создать запись в data_uploads
    4. Распарсить и сохранить raw данные в raw_data_uploads
    
    Response:
    {
        "upload_id": 1,
        "filename": "data.csv",
        "file_path": "data/uploads/...",
        "file_size": 2048,
        "records_saved": 100,
        "status": "completed",
        "stats": {
            "total_records": 100,
            "unique_indicators": 5,
            "unique_periods": 20
        }
    }
    """
    try:
        user_id = current_user.id
        logger.info(f"upload_data: начало загрузки от пользователя {user_id}")
        
        if not file.filename.endswith(('.csv', '.xlsx')):
            raise HTTPException(status_code=400, detail="Файл должен быть CSV или XLSX")
        
        settings = get_settings()
        file_service = FileService()
        
        file_path, file_size = await file_service.save_upload(file, user_id)
        logger.info(f"upload_data: CSV сохранен {file_path} ({file_size} bytes)")
        
        validation_result = file_service.validate_file(file_path)
        
        if not validation_result["is_valid"]:
            logger.error(f"upload_data: валидация не прошла: {validation_result['errors']}")
            raise HTTPException(
                status_code=400,
                detail=f"Ошибка валидации: {'; '.join(validation_result['errors'])}"
            )
        
        logger.info(f"upload_data: валидация успешна, {validation_result['row_count']} строк")

        repo = DataUploadRepository(db)
        data_upload = repo.create(
            user_id=user_id,
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            status="processing"
        )
        upload_id = data_upload.id
        logger.info(f"upload_data: создана запись data_uploads upload_id={upload_id}")
        
        df = file_service.load_data(file_path)
        if df is None or df.empty:
            repo.update(upload_id, {"status": "error"})
            raise HTTPException(status_code=400, detail="CSV файл пуст")
        
        logger.info(f"upload_data: CSV загружен shape={df.shape}")
        
        
        processing_service = DataProcessingService(db)
        
        try:
            records_count = processing_service.save_raw_data_from_csv(
                csv_file_path=file_path,
                upload_id=upload_id
            )
            logger.info(f"upload_data: сохранено {records_count} записей в raw_data_uploads")
        except Exception as e:
            logger.error(f"upload_data: ошибка при сохранении raw данных: {str(e)}")
            repo.update(upload_id, {"status": "error"})
            raise HTTPException(status_code=400, detail=f"Ошибка обработки: {str(e)}")
        
        stats = processing_service.get_upload_stats(upload_id)
        
        repo.update(upload_id, {
            "status": "completed",
            "period_from": stats.get("period_from"),
            "period_to": stats.get("period_to"),
        })
        
        logger.info(f"upload_data: успешно завершено upload_id={upload_id}")
        
        return {
            "upload_id": upload_id,
            "filename": file.filename,
            "file_path": file_path,
            "file_size": file_size,
            "records_saved": records_count,
            "status": "completed",
            "stats": stats,
            "message": f"Загружено {records_count} записей из файла '{file.filename}'"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"upload_data error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/uploads/{user_id}")
async def get_user_uploads(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Получить все загрузки пользователя
    
    GET /api/data/uploads/1
    """
    try:
        repo = DataUploadRepository(db)
        uploads = repo.get_by_user_id(user_id)
        
        return {
            "user_id": user_id,
            "count": len(uploads),
            "uploads": [
                {
                    "id": u.id,
                    "filename": u.filename,
                    "status": u.status,
                    "upload_date": str(u.upload_date),
                    "file_size": u.file_size,
                    "period_from": str(u.period_from) if u.period_from else None,
                    "period_to": str(u.period_to) if u.period_to else None,
                }
                for u in uploads
            ]
        }
    
    except Exception as e:
        logger.error(f"get_user_uploads error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uploads")
async def get_all_uploads(
    db: Session = Depends(get_db),
):
    """
    Получить все загрузки (только для администраторов)
    
    GET /api/data/uploads
    """
    try:        
        uploads = db.query(DataUpload).all()
        
        logger.info(f"get_all_uploads: админ запросил {len(uploads)} загрузок")
        
        return {
            "count": len(uploads),
            "uploads": [
                {
                    "id": u.id,
                    "user_id": u.user_id,
                    "user": {
                        "id": u.user.id,
                        "username": u.user.username,
                        "email": u.user.email,
                    } if u.user else None,
                    "filename": u.filename,
                    "file_path": u.file_path,
                    "status": u.status,
                    "created_at": str(u.created_at),
                    "upload_date": str(u.upload_date),
                    "file_size": u.file_size,
                    "period_from": str(u.period_from) if u.period_from else None,
                    "period_to": str(u.period_to) if u.period_to else None,
                }
                for u in uploads
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_all_uploads error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.delete("/uploads/{upload_id}")
async def delete_upload(
    upload_id: int,
    db: Session = Depends(get_db)
):
    """Удалить загруженный файл (может удалять только владелец или админ)"""
    try:
        repo = DataUploadRepository(db)
        upload = repo.get_by_id(upload_id)
        
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload #{upload_id} not found"
            )

        if upload.file_path and os.path.exists(upload.file_path):
            try:
                os.remove(upload.file_path)
                logger.info(f"Deleted file from disk: {upload.file_path}")
            except Exception as e:
                logger.warning(f"Could not delete file from disk: {str(e)}")
        
        repo.delete(upload_id)
        
        
        return {
            "message": f"Upload #{upload_id} deleted successfully",
            "upload_id": upload_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"delete_upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uploads/{upload_id}/info")
async def get_upload_info(
    upload_id: int,
    db: Session = Depends(get_db),
):
    """
    Получить информацию о загрузке и статистику
    
    GET /api/data/uploads/1/info
    """
    try:
        repo = DataUploadRepository(db)
        upload = repo.get_by_id(upload_id)
        
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} не найден"
            )
        
        processing_service = DataProcessingService(db)
        stats = processing_service.get_upload_stats(upload_id)
        
        feature_repo = FeatureRepository(db)
        features_list = feature_repo.get_by_upload_id(upload_id)
        features_info = None
        if features_list:
            f = features_list[-1]
            features_info = {
                "features_id": f.id,
                "features_file_path": f.features_file_path,
                "feature_count": f.feature_count,
                "row_count": f.row_count,
                "status": f.status,
                "created_at": str(f.created_at)
            }
        
        return {
            "upload_id": upload_id,
            "upload": {
                "filename": upload.filename,
                "file_path": upload.file_path,
                "file_size": upload.file_size,
                "status": upload.status,
                "period_from": str(upload.period_from) if upload.period_from else None,
                "period_to": str(upload.period_to) if upload.period_to else None,
                "upload_date": str(upload.upload_date)
            },
            "raw_data_stats": stats,
            "features": features_info
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_upload_info error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process/{upload_id}")
async def process_data(
    upload_id: int,
    db: Session = Depends(get_db),
):
    """
    Создать признаки для ML модели по upload_id
    
    POST /api/data/process/1
    
    Шаги:
    1. Загрузить raw данные из raw_data_uploads
    2. Преобразовать: длинный → широкий (pivot)
    3. Добавить признаки (лаги, rolling, diff)
    4. Сохранить файл на сервер (data/features/)
    5. Записать в features таблицу
    
    Response:
    {
        "upload_id": 1,
        "features_id": 1,
        "features_file_path": "data/features/features_*.csv",
        "feature_count": 25,
        "row_count": 150,
        "processing_time_sec": 2.5
    }
    """
    start_time = time.time()
    logger.info(f"process_data: начало для upload_id={upload_id}")
    
    try:
        repo = DataUploadRepository(db)
        upload = repo.get_by_id(upload_id)
        
        if not upload:
            logger.error(f"Upload не найден: {upload_id}")
            raise HTTPException(status_code=404, detail=f"Upload {upload_id} не найден")
        
        if upload.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Загрузка еще не готова (статус: {upload.status})"
            )
        
        raw_repo = RawDataUploadRepository(db)
        raw_count = raw_repo.count_by_upload_id(upload_id)
        
        if raw_count == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Нет raw данных для upload_id={upload_id}"
            )
        
        logger.info(f"process_data: найдено {raw_count} raw записей")
        
        service = DataProcessingService(db)
        
        try:
            features_path = service.create_and_save_features(upload_id)
            logger.info(f"process_data: признаки созданы {features_path}")
        except Exception as e:
            logger.error(f"process_data: ошибка при создании признаков: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Ошибка обработки: {str(e)}")

        features_df = pd.read_csv(features_path)
        
        feature_repo = FeatureRepository(db)
        feature = feature_repo.create(
            upload_id=upload_id,
            features_file_path=features_path,
            target_column=None,
            feature_count=len(features_df.columns) - 1, 
            row_count=len(features_df),
            status="completed"
        )
        
        elapsed = round(time.time() - start_time, 2)
        logger.info(f"process_data: успешно за {elapsed}сек для upload_id={upload_id}")
        
        return {
            "upload_id": upload_id,
            "features_id": feature.id,
            "features_file_path": features_path,
            "feature_count": feature.feature_count,
            "row_count": feature.row_count,
            "processing_time_sec": elapsed,
            "message": "Признаки успешно созданы и сохранены"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"process_data error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decompose/{upload_id}")
async def decompose_data(
    upload_id: int,
    period: int = Query(default=4),
    model: str = Query(default="additive"),
    db: Session = Depends(get_db),
):
    """
    Декомпозиция временных рядов на основе ИСХОДНЫХ (raw) данных.
    Возвращает PNG-графики как base64 data URIs.

    POST /api/data/decompose/1?period=4&model=additive
    """
    import time
    import base64
    
    start_time = time.time()
    logger.info(f"decompose_data: upload_id={upload_id}, period={period}, model={model}")

    try:
        upload_repo = DataUploadRepository(db)
        upload = upload_repo.get_by_id(upload_id)
        if not upload:
            raise HTTPException(status_code=404, detail=f"Upload {upload_id} не найден")

        raw_repo = RawDataUploadRepository(db)
        raw_records = raw_repo.get_by_upload_id(upload_id)
        
        if not raw_records:
            raise HTTPException(
                status_code=400,
                detail="Нет исходных данных для декомпозиции. Сначала загрузите файл.",
            )
        
        logger.info(f"decompose_data: загружено {len(raw_records)} raw записей из БД")
        
        raw_data = [
            {
                "period": r.period,
                "indicator_name": r.indicator_name,
                "value": r.value,
            }
            for r in raw_records
        ]
        
        raw_df = pd.DataFrame(raw_data)
        logger.info(f"decompose_data: raw_df shape={raw_df.shape}, columns={raw_df.columns.tolist()}")
        
        if raw_df.empty:
            raise HTTPException(status_code=400, detail="Исходные данные пусты")
        

        
        raw_df["period"] = pd.to_datetime(raw_df["period"])
        wide_df = raw_df.pivot_table(
            index="period",
            columns="indicator_name",
            values="value",
            aggfunc="mean"
        )
        
        wide_df.columns.name = None
        wide_df = wide_df.reset_index().sort_values("period").reset_index(drop=True)
        
        logger.info(f"decompose_data: wide_df shape={wide_df.shape}, columns={wide_df.columns.tolist()}")
        
        if wide_df.empty:
            raise HTTPException(status_code=400, detail="Не удалось преобразовать данные в широкий формат")
        
    
        svc = TimeSeriesDecompositionService()
        try:
            result = svc.decompose_raw_features(
                df=wide_df, 
                upload_id=upload_id,
                period=period,
                model=model
            )
            logger.info(f"decompose_data: декомпозиция успешна")
        except Exception as exc:
            logger.error(f"decompose_data error: {exc}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Ошибка декомпозиции: {exc}")

        plot_data = {}
        for fname, path in result["plot_paths"].items():
            try:
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                plot_data[fname] = "data:image/png;base64," + b64
                logger.info(f"decompose_data: закодировано {fname}")
            except Exception as exc:
                logger.warning(f"Could not encode image for '{fname}': {exc}")
                plot_data[fname] = None

        elapsed = round(time.time() - start_time, 2)
        logger.info(f"decompose_data: успешно за {elapsed}сек")

        return {
            "upload_id": upload_id,
            "period": period,
            "model": model,
            "processing_time_sec": elapsed,
            "decomposition": {
                "features_decomposed": result["features_decomposed"],
                "plot_paths": result["plot_paths"],
                "plot_data": plot_data,
                "errors": result["errors"],
            },
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"decompose_data error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))