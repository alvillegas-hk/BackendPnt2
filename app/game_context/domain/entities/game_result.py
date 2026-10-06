from dataclasses import dataclass
from typing import Optional


@dataclass
class GameResult:
    id: str
    user_id: str
    ave_id: int
    ave_nombre: str
    respuesta_usuario: str
    es_correcta: bool
    puntos_obtenidos: int
    createdAt: int

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "ave_id": self.ave_id,
            "ave_nombre": self.ave_nombre,
            "respuesta_usuario": self.respuesta_usuario,
            "es_correcta": self.es_correcta,
            "puntos_obtenidos": self.puntos_obtenidos,
            "createdAt": self.createdAt
        }
