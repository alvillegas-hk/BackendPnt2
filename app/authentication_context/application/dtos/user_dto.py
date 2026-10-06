from dataclasses import dataclass
from typing import Optional


@dataclass
class RegisterUserDTO:
    nombre: str
    apellido: str
    email: str
    password: str


@dataclass
class UserResponseDTO:
    id: str
    nombre: str
    apellido: str
    email: str
    role: str
    createdAt: int
    updatedAt: int
    lastLogin: Optional[int] = None


@dataclass
class UpdateUserDTO:
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


@dataclass
class ChangePasswordDTO:
    current_password: str
    new_password: str


@dataclass
class PaginatedUsersDTO:
    items: list
    total: int
    page: int
    per_page: int
    pages: int


@dataclass
class ScoreResponseDTO:
    id: str
    puntos: int
    juego: str
    fecha: int
    createdAt: int
