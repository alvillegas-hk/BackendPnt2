from dataclasses import dataclass
from typing import Optional
from enum import Enum


class Role(Enum):
    JUGADOR = "jugador"
    MODERADOR = "moderador"
    ADMIN = "admin"


@dataclass
class User:
    id: str
    nombre: str
    apellido: str
    email: str
    password_hash: str
    role: Role
    is_active: bool
    createdAt: int
    updatedAt: int
    lastLogin: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "email": self.email,
            "role": self.role.value,
            "is_active": self.is_active,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            "lastLogin": self.lastLogin
        }


@dataclass
class Score:
    id: str
    user_id: str
    puntos: int
    juego: str
    fecha: int
    createdAt: int

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "puntos": self.puntos,
            "juego": self.juego,
            "fecha": self.fecha,
            "createdAt": self.createdAt
        }
