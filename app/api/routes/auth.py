from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from app.api.schemas.auth import RegisterRequest, LoginRequest, RefreshTokenRequest, AuthResponse, RegisterResponse
from app.application.services.auth_service import AuthService
from app.api.dependencies import get_auth_service
from app.application.dtos.user_dto import RegisterUserDTO
from app.domain.exceptions.exceptions import EmailAlreadyExistsError, InvalidCredentialsError
from app.application.exceptions.exceptions import RateLimitError, AuthenticationError
from app.infrastructure.config.cookies import (
    COOKIE_CONFIG,
    ACCESS_TOKEN_EXPIRE,
    REFRESH_TOKEN_EXPIRE,
    IS_PRODUCTION
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED, summary="Registrar nuevo usuario", description="⭐ Core | Registra un nuevo usuario en el sistema")
async def register(request: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)):
    try:
        dto = RegisterUserDTO(
            nombre=request.nombre,
            apellido=request.apellido,
            email=request.email,
            password=request.password
        )
        tokens = auth_service.register(dto)

        # Crear response con cookies HttpOnly
        response = JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "token_type": "bearer",
                "mensaje": "Usuario registrado exitosamente"
            }
        )

        # Setear cookies HttpOnly
        response.set_cookie(
            key="access_token",
            value=tokens["access_token"],
            max_age=ACCESS_TOKEN_EXPIRE,
            **COOKIE_CONFIG
        )

        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            max_age=REFRESH_TOKEN_EXPIRE,
            **COOKIE_CONFIG
        )

        logger.info(f"Usuario registrado: {request.email}")
        return response

    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))


@router.post("/login", response_model=AuthResponse, summary="Iniciar sesión", description="⭐ Core | Genera token JWT para autenticarse")
async def login(request: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    try:
        tokens = auth_service.login(request.email, request.password)

        # Crear response con cookies HttpOnly
        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "token_type": "bearer",
                "mensaje": "Inicio de sesión exitoso"
            }
        )

        # Setear cookies HttpOnly
        response.set_cookie(
            key="access_token",
            value=tokens["access_token"],
            max_age=ACCESS_TOKEN_EXPIRE,
            **COOKIE_CONFIG
        )

        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            max_age=REFRESH_TOKEN_EXPIRE,
            **COOKIE_CONFIG
        )

        logger.info(f"Usuario autenticado: {request.email}")
        return response

    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except RateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))


@router.post("/refresh", response_model=AuthResponse, summary="Refrescar token de acceso", description="🔐 Protegido | Renueva el token JWT expirado")
async def refresh(request: RefreshTokenRequest, auth_service: AuthService = Depends(get_auth_service)):
    try:
        tokens = auth_service.refresh_access_token(request.refresh_token)

        # Crear response con cookies HttpOnly
        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "token_type": "bearer",
                "mensaje": "Token refrescado exitosamente"
            }
        )

        # Actualizar cookies HttpOnly
        response.set_cookie(
            key="access_token",
            value=tokens["access_token"],
            max_age=ACCESS_TOKEN_EXPIRE,
            **COOKIE_CONFIG
        )

        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            max_age=REFRESH_TOKEN_EXPIRE,
            **COOKIE_CONFIG
        )

        logger.info("Token refrescado exitosamente")
        return response

    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
