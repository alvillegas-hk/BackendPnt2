from fastapi import APIRouter, Depends, HTTPException, status
from app.api.schemas.auth import RegisterRequest, LoginRequest, RefreshTokenRequest, AuthResponse, RegisterResponse
from app.application.services.auth_service import AuthService
from app.api.dependencies import get_auth_service
from app.application.dtos.user_dto import RegisterUserDTO
from app.domain.exceptions.exceptions import EmailAlreadyExistsError, InvalidCredentialsError
from app.application.exceptions.exceptions import RateLimitError, AuthenticationError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED, summary="Registrar nuevo usuario")
async def register(request: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)):
    try:
        dto = RegisterUserDTO(
            nombre=request.nombre,
            apellido=request.apellido,
            email=request.email,
            password=request.password
        )
        return auth_service.register(dto)
    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))


@router.post("/login", response_model=AuthResponse, summary="Iniciar sesión")
async def login(request: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    try:
        return auth_service.login(request.email, request.password)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except RateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))


@router.post("/refresh", response_model=AuthResponse, summary="Refrescar token de acceso")
async def refresh(request: RefreshTokenRequest, auth_service: AuthService = Depends(get_auth_service)):
    try:
        return auth_service.refresh_access_token(request.refresh_token)
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
