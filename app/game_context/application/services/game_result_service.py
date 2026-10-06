import logging
from typing import List
from ulid import ULID
import time
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.infrastructure.database.models import GameResultModel, UserModel
from app.game_context.domain.entities import GameResult

logger = logging.getLogger(__name__)


class GameResultService:
    """Servicio para gestionar resultados del juego"""

    @staticmethod
    def guardar_resultado(
        db: Session,
        user_id: str,
        ave_id: int,
        ave_nombre: str,
        respuesta_usuario: str,
        es_correcta: bool,
        puntos_obtenidos: int,
        session_id: str = None
    ) -> GameResult:
        """
        Guarda un resultado del juego en la base de datos.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            ave_id: ID del ave
            ave_nombre: Nombre del ave
            respuesta_usuario: Respuesta del usuario
            es_correcta: Si la respuesta fue correcta
            puntos_obtenidos: Puntos obtenidos

        Returns:
            GameResult guardado
        """
        try:
            resultado_id = str(ULID())
            timestamp = int(time.time())

            resultado = GameResultModel(
                id=resultado_id,
                user_id=user_id,
                session_id=session_id,
                ave_id=ave_id,
                ave_nombre=ave_nombre,
                respuesta_usuario=respuesta_usuario,
                es_correcta=es_correcta,
                puntos_obtenidos=puntos_obtenidos,
                createdAt=timestamp
            )

            db.add(resultado)
            db.commit()
            db.refresh(resultado)

            return GameResult(
                id=resultado.id,
                user_id=resultado.user_id,
                ave_id=resultado.ave_id,
                ave_nombre=resultado.ave_nombre,
                respuesta_usuario=resultado.respuesta_usuario,
                es_correcta=resultado.es_correcta,
                puntos_obtenidos=resultado.puntos_obtenidos,
                createdAt=resultado.createdAt
            )

        except Exception as e:
            logger.error(f"Error guardando resultado del juego: {e}")
            db.rollback()
            raise

    @staticmethod
    def obtener_ranking(db: Session, limit: int = 10) -> List[dict]:
        """
        Obtiene el ranking de jugadores ordenado por puntos totales.

        Args:
            db: Sesión de base de datos
            limit: Cantidad de jugadores a retornar

        Returns:
            Lista de jugadores con sus estadísticas
        """
        try:
            resultados = db.query(
                UserModel.id,
                UserModel.nombre,
                UserModel.apellido,
                func.sum(GameResultModel.puntos_obtenidos).label("puntos_totales"),
                func.count(GameResultModel.id).label("total_intentos")
            ).outerjoin(
                GameResultModel,
                UserModel.id == GameResultModel.user_id
            ).group_by(
                UserModel.id,
                UserModel.nombre,
                UserModel.apellido
            ).order_by(
                desc("puntos_totales")
            ).limit(limit).all()

            ranking = []
            for r in resultados:
                aciertos_count = db.query(func.count(GameResultModel.id)).filter(
                    GameResultModel.user_id == r.id,
                    GameResultModel.es_correcta == True
                ).scalar() or 0

                total_intentos = r.total_intentos or 0

                ranking.append({
                    "user_id": r.id,
                    "nombre": r.nombre,
                    "apellido": r.apellido,
                    "puntos_totales": r.puntos_totales or 0,
                    "aciertos": aciertos_count,
                    "fallos": total_intentos - aciertos_count
                })

            return ranking

        except Exception as e:
            logger.error(f"Error obteniendo ranking: {e}")
            raise

    @staticmethod
    def obtener_estadisticas_usuario(db: Session, user_id: str) -> dict:
        """
        Obtiene estadísticas de un jugador específico.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            Diccionario con estadísticas
        """
        try:
            resultados = db.query(GameResultModel).filter(
                GameResultModel.user_id == user_id
            ).all()

            total_intentos = len(resultados)
            aciertos = sum(1 for r in resultados if r.es_correcta)
            puntos_totales = sum(r.puntos_obtenidos for r in resultados)

            return {
                "user_id": user_id,
                "total_intentos": total_intentos,
                "aciertos": aciertos,
                "fallos": total_intentos - aciertos,
                "puntos_totales": puntos_totales,
                "porcentaje_acierto": (aciertos / total_intentos * 100) if total_intentos > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            raise
