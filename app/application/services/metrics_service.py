import logging
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.infrastructure.database.models import GameResultModel, UserModel
from app.application.dtos.metrics_dto import (
    MetricasUsuarioResponse,
    MetricasGlobalResponse,
    AveEstadistica
)

logger = logging.getLogger(__name__)


class MetricsService:
    """Servicio para obtener métricas del juego"""

    @staticmethod
    def obtener_metricas_usuario(db: Session, user_id: str) -> MetricasUsuarioResponse:
        """
        Obtiene las métricas personales de un usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            MetricasUsuarioResponse con estadísticas del usuario
        """
        try:
            usuario = db.query(UserModel).filter(UserModel.id == user_id).first()
            if not usuario:
                raise ValueError(f"Usuario {user_id} no encontrado")

            resultados = db.query(GameResultModel).filter(
                GameResultModel.user_id == user_id
            ).all()

            total_intentos = len(resultados)
            total_aciertos = sum(1 for r in resultados if r.es_correcta)
            puntuacion_total = sum(r.puntos_obtenidos for r in resultados)

            porcentaje_acierto = (total_aciertos / total_intentos * 100) if total_intentos > 0 else 0

            # Obtener posición en ranking
            ranking = db.query(
                UserModel.id,
                func.sum(GameResultModel.puntos_obtenidos).label("puntos_totales")
            ).outerjoin(
                GameResultModel,
                UserModel.id == GameResultModel.user_id
            ).group_by(
                UserModel.id
            ).order_by(
                func.sum(GameResultModel.puntos_obtenidos).desc()
            ).all()

            posicion = 1
            for idx, (uid, _) in enumerate(ranking, 1):
                if uid == user_id:
                    posicion = idx
                    break

            return MetricasUsuarioResponse(
                user_id=usuario.id,
                nombre=usuario.nombre,
                apellido=usuario.apellido,
                total_intentos=total_intentos,
                total_aciertos=total_aciertos,
                porcentaje_acierto=round(porcentaje_acierto, 2),
                puntuacion_total=puntuacion_total,
                posicion_ranking=posicion
            )

        except Exception as e:
            logger.error(f"Error obteniendo métricas del usuario {user_id}: {e}")
            raise

    @staticmethod
    def obtener_metricas_global(db: Session) -> MetricasGlobalResponse:
        """
        Obtiene las métricas globales del sistema.

        Args:
            db: Sesión de base de datos

        Returns:
            MetricasGlobalResponse con estadísticas del sistema
        """
        try:
            # Total de jugadores activos (que han jugado al menos una vez)
            jugadores_activos = db.query(func.count(func.distinct(GameResultModel.user_id))).scalar() or 0

            # Total de intentos en el sistema
            total_intentos = db.query(func.count(GameResultModel.id)).scalar() or 0

            # Porcentaje de acierto global
            total_aciertos = db.query(func.count(GameResultModel.id)).filter(
                GameResultModel.es_correcta == True
            ).scalar() or 0

            porcentaje_global = (total_aciertos / total_intentos * 100) if total_intentos > 0 else 0

            # Ave más acertada - obtener todas y calcular en Python
            ave_mas_acertada = None
            aves_stats = db.query(
                GameResultModel.ave_id,
                GameResultModel.ave_nombre,
                func.count(GameResultModel.id).label("total")
            ).group_by(
                GameResultModel.ave_id,
                GameResultModel.ave_nombre
            ).all()

            if aves_stats:
                aves_con_porcentaje = []
                for ave_id, ave_nombre, total in aves_stats:
                    aciertos = db.query(func.count(GameResultModel.id)).filter(
                        GameResultModel.ave_id == ave_id,
                        GameResultModel.es_correcta == True
                    ).scalar() or 0

                    porcentaje = (aciertos / total * 100) if total > 0 else 0
                    aves_con_porcentaje.append({
                        "id": ave_id,
                        "nombre": ave_nombre,
                        "total": total,
                        "aciertos": aciertos,
                        "porcentaje": porcentaje
                    })

                # Más acertada (mayor porcentaje)
                ave_mas = max(aves_con_porcentaje, key=lambda x: x["porcentaje"])
                ave_mas_acertada = AveEstadistica(
                    id=ave_mas["id"],
                    nombre=ave_mas["nombre"],
                    total_intentos=ave_mas["total"],
                    total_aciertos=ave_mas["aciertos"],
                    porcentaje_acierto=round(ave_mas["porcentaje"], 2)
                )

                # Menos acertada (menor porcentaje)
                ave_menos_acertada = None
                ave_menos = min(aves_con_porcentaje, key=lambda x: x["porcentaje"])
                ave_menos_acertada = AveEstadistica(
                    id=ave_menos["id"],
                    nombre=ave_menos["nombre"],
                    total_intentos=ave_menos["total"],
                    total_aciertos=ave_menos["aciertos"],
                    porcentaje_acierto=round(ave_menos["porcentaje"], 2)
                )

            return MetricasGlobalResponse(
                total_jugadores_activos=jugadores_activos,
                total_intentos_sistema=total_intentos,
                porcentaje_acierto_global=round(porcentaje_global, 2),
                ave_mas_acertada=ave_mas_acertada,
                ave_menos_acertada=ave_menos_acertada
            )

        except Exception as e:
            logger.error(f"Error obteniendo métricas globales: {e}")
            raise
