from typing import List
from pydantic import BaseModel


class GameAveOption(BaseModel):
    id: int
    nombre: str
    nombreCientifico: str


class GameAveQuestion(BaseModel):
    id: int
    nombre: str
    nombreCientifico: str
    foto: str
    atribucion: str | None = None
    opciones: List[GameAveOption]


class GameAveResponse(BaseModel):
    ave: GameAveQuestion


class IniciarSesionResponse(BaseModel):
    session_id: str
    mensaje: str


class RespuestaJugadorRequest(BaseModel):
    ave_id: int
    ave_nombre: str
    respuesta_usuario: str


class RespuestaJugadorResponse(BaseModel):
    es_correcta: bool
    puntos_obtenidos: int
    mensaje: str


class TerminarSesionResponse(BaseModel):
    session_id: str
    puntos_totales: int
    total_intentos: int
    total_aciertos: int
    porcentaje_acierto: float
    mensaje: str


class EstadisticasSesionResponse(BaseModel):
    session_id: str
    puntos_totales: int
    total_intentos: int
    total_aciertos: int
    estado: str
    porcentaje_acierto: float


class JugadorRanking(BaseModel):
    user_id: str
    nombre: str
    apellido: str
    puntos_totales: int
    aciertos: int
    fallos: int


class RankingResponse(BaseModel):
    total_jugadores: int
    ranking: List[JugadorRanking]
