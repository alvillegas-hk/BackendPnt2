from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.api.schemas.user import UserResponse, ChangePasswordRequest, UpdateUserRequest, ResetPasswordResponse, PaginatedUsersResponse, MessageResponse
from app.application.services.user_service import UserService
from app.api.dependencies import get_user_service, get_current_user
from app.application.dtos.user_dto import ChangePasswordDTO, UpdateUserDTO
from app.application.exceptions.exceptions import UserNotFoundError, AuthorizationError

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse, summary="Obtener perfil del usuario actual", description="🔐 Protegido | Retorna los datos del usuario autenticado")
async def get_profile(current_user: dict = Depends(get_current_user), user_service: UserService = Depends(get_user_service)):
    try:
        return user_service.get_user_profile(current_user["user_id"])
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/me/password", response_model=MessageResponse, summary="Cambiar contraseña del usuario actual", description="🔐 Protegido | Actualiza la contraseña del usuario autenticado")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    try:
        dto = ChangePasswordDTO(
            current_password=request.current_password,
            new_password=request.new_password
        )
        return user_service.change_password(current_user["user_id"], dto)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=PaginatedUsersResponse, summary="Listar usuarios (moderadores y admins)", description="🔐 Protegido | Solo mods/admins - Lista de usuarios del sistema")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    role: str = Query(None, description="Filtrar por rol"),
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    try:
        result = user_service.list_users(page, per_page, current_user["role"], role)
        return {
            "items": result.items,
            "total": result.total,
            "page": result.page,
            "per_page": result.per_page,
            "pages": result.pages
        }
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse, summary="Obtener datos de un usuario", description="🔐 Protegido | Retorna información pública de un usuario específico")
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    try:
        return user_service.get_user_by_id(user_id, current_user["user_id"], current_user["role"])
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch("/{user_id}", response_model=UserResponse, summary="Actualizar datos de un usuario (solo admins)")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    try:
        dto = UpdateUserDTO(
            nombre=request.nombre,
            apellido=request.apellido,
            role=request.role,
            is_active=request.is_active
        )
        return user_service.update_user(user_id, dto, current_user["role"])
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse, summary="Resetear contraseña de un usuario (solo admins)")
async def reset_password(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    try:
        return user_service.reset_password(user_id, current_user["role"])
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
