from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Query
from typing import List
import logging
from sqlalchemy.orm import Session
from app.models import User
from app.repositories import UserRepository
from app.schemas import UserResponse, UserCreateSchema
from app.auth import hash_password, get_current_user
from app.database import get_db
logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["user"])


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Проверка что пользователь админ.
    Используется для защиты endpoints которые доступны только админам.
    """
    if current_user.role != "admin":
        logger.warning(f"require_admin: доступ запрещен для {current_user.username} (роль: {current_user.role})")
        raise HTTPException(
            status_code=403,
            detail="Требуется роль администратора"
        )
    return current_user


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreateSchema,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Создать нового пользователя (только для администратора).
    
    POST /api/users
    
    Required role: admin
    
    Request body:
    {
        "username": "ivan_ivanov",
        "email": "ivan@example.com",
        "password": "secure_password_123",
        "full_name": "Иван Иванов",
        "role": "analyst"
    }
    
    Returns:
        UserResponse с данными созданного пользователя
    """
    try:
        logger.info(f"create_user: админ {current_user.username} создаёт пользователя {user_data.username}")
        
        user_repo = UserRepository(db)
        existing_user = user_repo.get_by_username(user_data.username)
        
        if existing_user:
            logger.warning(f"create_user: пользователь уже существует: {user_data.username}")
            raise HTTPException(status_code=400, detail="Username already taken")
        
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            logger.warning(f"create_user: email уже зарегистрирован: {user_data.email}")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        password_hash = hash_password(user_data.password)
        logger.info(f"create_user: пароль захеширован для {user_data.username}")

        new_user = user_repo.create(
            username=user_data.username,
            password_hash=password_hash,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            is_active=True
        )
        
        logger.info(f"create_user: успешно создан пользователь id={new_user.id}, username={new_user.username}")
        
        
        return new_user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"create_user error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Получить всех пользователей (только для администратора).
    
    GET /api/users
    """
    try:
        logger.info(f"get_all_users: админ {current_user.username} запросил список пользователей")
        
        users = db.query(User).all()
        
        logger.info(f"get_all_users: найдено {len(users)} пользователей")
        
        return users
    
    except Exception as e:
        logger.error(f"get_all_users error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}", response_model=dict)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Удалить пользователя (только для администратора).
    Администратор не может удалить сам себя.
    
    DELETE /api/users/3
    """
    try:
        logger.info(f"delete_user: админ {current_user.username} пытается удалить пользователя {user_id}")
        
        user_repo = UserRepository(db)
        user_to_delete = user_repo.get_by_id(user_id)
        
        if not user_to_delete:
            logger.warning(f"delete_user: пользователь {user_id} не найден")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user_to_delete.id == current_user.id:
            logger.warning(f"delete_user: админ {current_user.username} пытался удалить сам себя")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
        
        user_repo.delete(user_id)
        
        logger.info(f"delete_user: пользователь {user_to_delete.username} (id={user_id}) удален админом {current_user.username}")
        
        return {
            "detail": f"User {user_to_delete.username} deleted successfully",
            "user_id": user_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"delete_user error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    