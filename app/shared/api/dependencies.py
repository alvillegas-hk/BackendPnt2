from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.requests import Request
from sqlalchemy.orm import Session
from app.shared.infrastructure.database.database import get_db
from app.infrastructure.config.settings import get_settings
from app.infrastructure.security.jwt_handler import decode_token
from app.authentication_context.domain.repositories.user_repository import UserRepository
from app.authentication_context.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from app.authentication_context.application.services.auth_service import AuthService
from app.authentication_context.application.services.user_service import UserService
from app.shared.infrastructure.database.models import UserModel


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepositoryImpl(db)


def get_auth_service(repo: UserRepository = Depends(get_user_repository)) -> AuthService:
    return AuthService(repo)


def get_user_service(repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repo)


async def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación faltante",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = auth_header[7:]
    payload = decode_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")
    role = payload.get("role")

    return {
        "user_id": user_id,
        "role": role,
        "email": payload.get("email")
    }


async def get_current_user_model(
    request: Request,
    db: Session = Depends(get_db)
) -> UserModel:
    """
    Obtiene el modelo de usuario actual desde el token JWT.
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación faltante",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = auth_header[7:]
    payload = decode_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")
    user = db.query(UserModel).filter(UserModel.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


async def get_admin_or_moderator(
    current_user: UserModel = Depends(get_current_user_model)
) -> UserModel:
    """
    Valida que el usuario sea admin o moderador.
    Lanza excepción si no tiene permisos suficientes.
    """
    if current_user.role not in ["admin", "moderador"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Solo admins y moderadores pueden ver esto."
        )

    return current_user
