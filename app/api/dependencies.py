from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.requests import Request
from sqlalchemy.orm import Session
from app.infrastructure.database.database import get_db
from app.infrastructure.config.settings import get_settings
from app.infrastructure.security.jwt_handler import decode_token
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from app.application.services.auth_service import AuthService
from app.application.services.user_service import UserService


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
