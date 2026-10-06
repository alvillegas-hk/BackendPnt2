from dataclasses import dataclass
from typing import Optional
from enum import Enum


class SessionState(Enum):
    ACTIVA = "activa"
    TERMINADA = "terminada"


@dataclass
class GameSession:
    id: str
    user_id: str
    puntos_totales: int
    total_intentos: int
    total_aciertos: int
    estado: SessionState
    createdAt: int
    terminadaAt: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "puntos_totales": self.puntos_totales,
            "total_intentos": self.total_intentos,
            "total_aciertos": self.total_aciertos,
            "estado": self.estado.value,
            "createdAt": self.createdAt,
            "terminadaAt": self.terminadaAt
        }
