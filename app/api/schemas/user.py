from pydantic import BaseModel, EmailStr
from typing import Optional, List


class UserResponse(BaseModel):
    id: str
    nombre: str
    apellido: str
    email: str
    role: str
    createdAt: int
    updatedAt: int
    lastLogin: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "nombre": "Juan",
                "apellido": "Pérez",
                "email": "juan@example.com",
                "role": "jugador",
                "createdAt": 1728207600000,
                "updatedAt": 1728207600000,
                "lastLogin": 1728207600000
            }
        }


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "oldPassword123",
                "new_password": "newPassword123"
            }
        }


class UpdateUserRequest(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Juan",
                "apellido": "García",
                "role": "moderador",
                "is_active": True
            }
        }


class ResetPasswordResponse(BaseModel):
    user_id: str
    new_password: str
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "new_password": "aBc123XyZ789",
                "message": "Contraseña reseteada. Guarde la nueva contraseña."
            }
        }


class PaginatedUsersResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                        "nombre": "Juan",
                        "apellido": "Pérez",
                        "email": "juan@example.com",
                        "role": "jugador",
                        "createdAt": 1728207600000,
                        "updatedAt": 1728207600000,
                        "lastLogin": 1728207600000
                    }
                ],
                "total": 100,
                "page": 1,
                "per_page": 20,
                "pages": 5
            }
        }


class MessageResponse(BaseModel):
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Contraseña actualizada exitosamente"
            }
        }


class ScoreResponse(BaseModel):
    id: str
    puntos: int
    juego: str
    fecha: int
    createdAt: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "puntos": 100,
                "juego": "chess",
                "fecha": 1728207600000,
                "createdAt": 1728207600000
            }
        }


class PaginatedScoresResponse(BaseModel):
    items: List[ScoreResponse]
    total: int
    page: int
    per_page: int
    pages: int

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 0,
                "page": 1,
                "per_page": 20,
                "pages": 0
            }
        }
