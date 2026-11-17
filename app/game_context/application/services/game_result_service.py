import logging
from typing import List
from ulid import ULID
import time
from sqlalchemy.orm import Session
from sqlalchemy import case, func

from app.shared.infrastructure.database.models import GameResultModel, UserModel
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
        session_id: str = None,
        streak: int = 0,
        bonus_racha: int = 0
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
            session_id: ID de la sesión
            streak: Racha de respuestas correctas consecutivas
            bonus_racha: Puntos bonus por racha

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
                bonus_racha=bonus_racha,
                streak_en_respuesta=streak,
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
    def _consulta_estadisticas_jugadores(db: Session):
        puntos_totales = func.coalesce(
            func.sum(GameResultModel.puntos_obtenidos + GameResultModel.bonus_racha),
            0
        ).label("puntos_totales")
        aciertos = func.coalesce(func.sum(
            case((GameResultModel.es_correcta.is_(True), 1), else_=0)
        ), 0).label("aciertos")

        return db.query(
            UserModel.id.label("user_id"),
            UserModel.nombre.label("nombre"),
            UserModel.apellido.label("apellido"),
            puntos_totales,
            func.count(GameResultModel.id).label("total_intentos"),
            aciertos
        ).join(
            GameResultModel,
            UserModel.id == GameResultModel.user_id,
            isouter=True
        ).group_by(
            UserModel.id,
            UserModel.nombre,
            UserModel.apellido
        ).subquery()

    @staticmethod
    def _consulta_ranking(db: Session):
        agregados = GameResultService._consulta_estadisticas_jugadores(db)

        return db.query(
            agregados.c.user_id,
            agregados.c.nombre,
            agregados.c.apellido,
            agregados.c.puntos_totales,
            agregados.c.aciertos,
            (agregados.c.total_intentos - agregados.c.aciertos).label("fallos"),
            func.row_number().over(
                order_by=(agregados.c.puntos_totales.desc(), agregados.c.user_id.asc())
            ).label("posicion")
        ).filter(
            agregados.c.puntos_totales > 0
        ).subquery()

    @staticmethod
    def _jugador_desde_fila(fila) -> dict:
        return {
            "user_id": fila.user_id,
            "nombre": fila.nombre,
            "apellido": fila.apellido,
            "puntos_totales": fila.puntos_totales,
            "aciertos": fila.aciertos,
            "fallos": fila.fallos,
            "posicion": fila.posicion
        }

    @staticmethod
    def obtener_ranking_paginado(
        db: Session,
        limit: int = 10,
        offset: int = 0,
        user_id: str | None = None
    ) -> dict:
        """
        Obtiene una página del ranking, su total y la fila personal.

        Args:
            db: Sesión de base de datos
            limit: Cantidad de jugadores a retornar
            offset: Cantidad de jugadores a omitir
            user_id: Usuario para el que se solicita la fila personal

        Returns:
            Página ordenada, total de participantes y fila personal
        """
        try:
            consulta = GameResultService._consulta_ranking(db)
            filas = db.query(consulta).order_by(
                consulta.c.posicion
            ).offset(offset).limit(limit).all()
            total_jugadores = db.query(func.count(consulta.c.user_id)).scalar() or 0

            jugador_actual = None
            if user_id is not None:
                jugador_actual = GameResultService.obtener_jugador_ranking(db, user_id)

            return {
                "ranking": [GameResultService._jugador_desde_fila(fila) for fila in filas],
                "total_jugadores": total_jugadores,
                "jugador_actual": jugador_actual
            }

        except Exception as e:
            logger.error(f"Error obteniendo ranking: {e}")
            raise

    @staticmethod
    def obtener_ranking(db: Session, limit: int = 10, offset: int = 0) -> List[dict]:
        """Mantiene la interfaz de lista usada por los consumidores existentes."""
        return GameResultService.obtener_ranking_paginado(db, limit, offset)["ranking"]

    @staticmethod
    def obtener_jugador_ranking(db: Session, user_id: str) -> dict | None:
        """Obtiene estadísticas personales reales y el puesto si participa del ranking."""
        estadisticas = GameResultService._consulta_estadisticas_jugadores(db)
        fila_personal = db.query(estadisticas).filter(
            estadisticas.c.user_id == user_id
        ).first()
        if not fila_personal:
            return None

        jugador = {
            "user_id": fila_personal.user_id,
            "nombre": fila_personal.nombre,
            "apellido": fila_personal.apellido,
            "puntos_totales": fila_personal.puntos_totales,
            "aciertos": fila_personal.aciertos,
            "fallos": fila_personal.total_intentos - fila_personal.aciertos,
            "posicion": None
        }

        consulta_ranking = GameResultService._consulta_ranking(db)
        fila_ranking = db.query(consulta_ranking).filter(
            consulta_ranking.c.user_id == user_id
        ).first()
        if fila_ranking:
            jugador["posicion"] = fila_ranking.posicion

        return jugador

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
            puntos_totales = sum(r.puntos_obtenidos + r.bonus_racha for r in resultados)

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
