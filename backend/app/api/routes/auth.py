from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.repositories import UserRepository
from app.schemas import UserLogin, UserRegister, TokenResponse
from app.auth import hash_password, verify_password, create_access_token
from datetime import timedelta
import logging


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя
    
    POST /api/auth/register
    {
        "username": "testuser",
        "password": "password123",
        "email": "test@example.com"
    }
    """
    try:
        logger.info(f"register: начало для username={user_data.username}")
        
        user_repo = UserRepository(db)
        existing = user_repo.get_by_username(user_data.username)
        
        if existing:
            logger.error(f"Пользователь уже существует: {user_data.username}")
            raise HTTPException(status_code=400, detail="Username already taken")
        
        password_hash = hash_password(user_data.password)
        
        user = user_repo.create(
            username=user_data.username,
            password_hash=password_hash,
            email=user_data.email,
            role=user_data.role
        )
        
        logger.info(f"Пользователь создан: id={user.id}")
        
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(hours=24)
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            username=user.username,
            role=user.role
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"register error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Авторизация пользователя
    
    POST /api/auth/login
    {
        "username": "testuser",
        "password": "password123",
        "role" : "admin"
    }
    """
    try:
        logger.info(f"login: начало для username={user_data.username}")
        
        user_repo = UserRepository(db)
        user = user_repo.get_by_username(user_data.username)
        
        if not user:
            logger.warning(f"login: пользователь не найден: {user_data.username}")
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        if not verify_password(user_data.password, user.password_hash):
            logger.warning(f"login: неверный пароль для: {user_data.username}")
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        if not user.is_active:
            logger.warning(f"login: пользователь {user_data.username} неактивен")
            raise HTTPException(status_code=403, detail="User is inactive")
        
        logger.info(f"login: успешная авторизация id={user.id}, username={user.username}, role={user.role}")
        
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(hours=24)
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            username=user.username,
            role=user.role
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"login error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))