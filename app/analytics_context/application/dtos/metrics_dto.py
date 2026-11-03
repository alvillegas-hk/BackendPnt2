from pydantic import BaseModel


class MetricasUsuarioResponse(BaseModel):
    user_id: str
    nombre: str
    apellido: str
    total_intentos: int
    total_aciertos: int
    porcentaje_acierto: float
    puntuacion_total: int
    posicion_ranking: int
    tiempo_conectado_hoy_seg: int = 0
    tiempo_conectado_total_seg: int = 0


class AveEstadistica(BaseModel):
    id: int
    nombre: str
    total_intentos: int
    total_aciertos: int
    porcentaje_acierto: float


class MetricasGlobalResponse(BaseModel):
    total_jugadores_activos: int
    total_intentos_sistema: int
    porcentaje_acierto_global: float
    ave_mas_acertada: AveEstadistica | None
    ave_menos_acertada: AveEstadistica | None
