# ═══════════════════════════════════════════════════════════════════════
# УПРАВЛЕНИЕ МОДЕЛЯМИ (только для админа)
# ═══════════════════════════════════════════════════════════════════════
''' 
@router.post("/models")
async def add_model(
    algorithm: str = Form(...),
    version: str = Form(...),
    model_file: UploadFile = File(...),
    mae: float = Form(default=0.0),
    rmse: float = Form(default=0.0),
    r2_score: float = Form(default=0.0),
    current_user: User = Depends(require_admin),  # ← Проверка админа
    db: Session = Depends(get_db),
):
    """
    Добавить новую ML модель (только для администратора).
    
    POST /api/models
    
    Required role: admin
    
    Form data:
        - algorithm: str (ridge, xgboost, random_forest)
        - version: str (1.0, 2.0, etc)
        - model_file: UploadFile (*.pkl файл)
        - mae: float (опционально)
        - rmse: float (опционально)
        - r2_score: float (опционально)
    """
    logger.info(f"add_model: админ {current_user.username} загружает модель {algorithm} v{version}")
    
    try:
        # Создать директорию для моделей
        base_dir = Path(__file__).resolve().parent.parent.parent
        model_dir = base_dir / "data" / "models"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Сохранить файл модели с уникальным именем
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_algorithm = algorithm.replace('/', '_').replace('\\', '_')
        safe_version = version.replace('/', '_').replace('\\', '_')
        filename = f"model_{safe_algorithm}_v{safe_version}_{timestamp}.pkl"
        filepath = model_dir / filename
        
        # Читаем и сохраняем файл
        content = await model_file.read()
        
        # Проверяем что файл не пустой
        if not content:
            logger.error(f"add_model: файл модели пуст для {algorithm}")
            raise HTTPException(status_code=400, detail="Файл модели пуст")
        
        with open(filepath, "wb") as f:
            f.write(content)
        
        logger.info(f"add_model: файл сохранён {filepath} ({len(content)} bytes)")
        
        # Создаём запись в БД
        new_model = ModelVersion(
            algorithm=algorithm,
            version=version,
            model_file_path=str(filepath),
            mae=mae,
            rmse=rmse,
            r2_score=r2_score,
            is_active=False,  # По умолчанию модель неактивна
        )
        
        db.add(new_model)
        db.commit()
        db.refresh(new_model)
        
        logger.info(f"add_model: модель успешно добавлена, ID={new_model.id}, путь={filepath}")
        
        return {
            "id": new_model.id,
            "algorithm": new_model.algorithm,
            "version": new_model.version,
            "model_file_path": str(new_model.model_file_path),
            "mae": new_model.mae,
            "rmse": new_model.rmse,
            "r2_score": new_model.r2_score,
            "is_active": new_model.is_active,
            "created_at": str(new_model.created_at),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"add_model error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при добавлении модели: {str(e)}"
        )
        '''