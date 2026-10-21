import json
import logging
import time
from ulid import ULID
from sqlalchemy.orm import Session

from app.infrastructure.database.models import GameSessionModel, GameResultModel, ScoreModel
from app.application.dtos.metrics_dto import MetricasUsuarioResponse

logger = logging.getLogger(__name__)


class GameSessionService:
    """Servicio para gestionar sesiones de juego"""

    @staticmethod
    def iniciar_sesion(
        db: Session,
        user_id: str,
        preguntas: list[dict],
        place_id: int,
        locale: str
    ) -> str:
        """
        Inicia una nueva sesión de juego para un usuario con su lote de preguntas.
        Si el usuario tenía sesiones activas, las cierra antes (guardando su puntuación).

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            preguntas: Lote de preguntas (dicts de GameAveQuestion), con la respuesta correcta
            place_id: ID del lugar con el que se generó el lote
            locale: Idioma con el que se generó el lote

        Returns:
            ID de la sesión iniciada
        """
        try:
            activas = db.query(GameSessionModel).filter(
                GameSessionModel.user_id == user_id,
                GameSessionModel.estado == "activa"
            ).all()
            for anterior in activas:
                GameSessionService.terminar_sesion(db, anterior.id)

            session_id = str(ULID())
            timestamp = int(time.time())

            sesion = GameSessionModel(
                id=session_id,
                user_id=user_id,
                puntos_totales=0,
                total_intentos=0,
                total_aciertos=0,
                streak_actual=0,
                streak_maximo=0,
                estado="activa",
                createdAt=timestamp,
                preguntas=json.dumps(preguntas),
                place_id=place_id,
                locale=locale
            )

            db.add(sesion)
            db.commit()
            logger.info(f"Sesión {session_id} iniciada para usuario {user_id}")
            return session_id

        except Exception as e:
            logger.error(f"Error iniciando sesión de juego: {e}")
            db.rollback()
            raise

    @staticmethod
    def obtener_sesion_activa(db: Session, user_id: str) -> GameSessionModel:
        """
        Obtiene la sesión activa del usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            GameSessionModel o None si no hay sesión activa
        """
        try:
            sesion = db.query(GameSessionModel).filter(
                GameSessionModel.user_id == user_id,
                GameSessionModel.estado == "activa"
            ).first()
            return sesion

        except Exception as e:
            logger.error(f"Error obteniendo sesión activa: {e}")
            raise

    @staticmethod
    def obtener_lote(sesion: GameSessionModel) -> list[dict] | None:
        """
        Devuelve el lote de preguntas guardado en la sesión.

        Returns:
            Lista de preguntas, o None si la sesión no tiene lote (sesiones creadas antes de guardarlo)
        """
        if not sesion.preguntas:
            return None
        return json.loads(sesion.preguntas)

    @staticmethod
    def obtener_pregunta_del_lote(sesion: GameSessionModel, ave_id: int) -> dict | None:
        """Devuelve la pregunta del lote cuyo id coincide con ave_id, o None si no está en el lote."""
        for pregunta in GameSessionService.obtener_lote(sesion) or []:
            if pregunta["id"] == ave_id:
                return pregunta
        return None

    @staticmethod
    def obtener_respuestas(db: Session, session_id: str) -> list[GameResultModel]:
        """Devuelve las respuestas de la sesión en el orden en que se respondieron."""
        return db.query(GameResultModel).filter(
            GameResultModel.session_id == session_id
        ).order_by(GameResultModel.createdAt, GameResultModel.id).all()

    @staticmethod
    def validar_respuesta_unica(db: Session, session_id: str, ave_id: int) -> bool:
        """
        Verifica que el usuario no haya respondido ya esta pregunta en esta sesión.

        Args:
            db: Sesión de base de datos
            session_id: ID de la sesión
            ave_id: ID del ave

        Returns:
            True si es la primera vez, False si ya respondió
        """
        try:
            existe = db.query(GameResultModel).filter(
                GameResultModel.session_id == session_id,
                GameResultModel.ave_id == ave_id
            ).first()
            return existe is None

        except Exception as e:
            logger.error(f"Error validando respuesta única: {e}")
            raise

    @staticmethod
    def terminar_sesion(db: Session, session_id: str) -> dict:
        """
        Termina una sesión de juego y guarda la puntuación.

        Args:
            db: Sesión de base de datos
            session_id: ID de la sesión

        Returns:
            Diccionario con resumen de la sesión
        """
        try:
            sesion = db.query(GameSessionModel).filter(
                GameSessionModel.id == session_id
            ).first()

            if not sesion:
                raise ValueError(f"Sesión {session_id} no encontrada")

            if sesion.estado == "terminada":
                raise ValueError("La sesión ya fue terminada")

            # Calcular estadísticas finales
            resultados = db.query(GameResultModel).filter(
                GameResultModel.session_id == session_id
            ).all()

            total_intentos = len(resultados)
            total_aciertos = sum(1 for r in resultados if r.es_correcta)
            puntos_totales = sum(r.puntos_obtenidos for r in resultados)

            # Actualizar sesión
            timestamp = int(time.time())
            sesion.puntos_totales = puntos_totales
            sesion.total_intentos = total_intentos
            sesion.total_aciertos = total_aciertos
            sesion.estado = "terminada"
            sesion.terminadaAt = timestamp

            # Guardar puntuación en ScoreModel
            score_id = str(ULID())
            score = ScoreModel(
                id=score_id,
                user_id=sesion.user_id,
                puntos=puntos_totales,
                juego="birds_game",
                fecha=timestamp,
                createdAt=timestamp
            )

            db.add(score)
            db.commit()

            logger.info(f"Sesión {session_id} terminada. Puntos: {puntos_totales}, Aciertos: {total_aciertos}/{total_intentos}")

            return {
                "session_id": session_id,
                "puntos_totales": puntos_totales,
                "total_intentos": total_intentos,
                "total_aciertos": total_aciertos,
                "porcentaje_acierto": round((total_aciertos / total_intentos * 100) if total_intentos > 0 else 0, 2)
            }

        except Exception as e:
            logger.error(f"Error terminando sesión: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_session_stats(db: Session, session_id: str) -> dict:
        """
        Obtiene estadísticas de una sesión.

        Args:
            db: Sesión de base de datos
            session_id: ID de la sesión

        Returns:
            Diccionario con estadísticas
        """
        try:
            sesion = db.query(GameSessionModel).filter(
                GameSessionModel.id == session_id
            ).first()

            if not sesion:
                raise ValueError(f"Sesión {session_id} no encontrada")

            return {
                "session_id": sesion.id,
                "puntos_totales": sesion.puntos_totales,
                "total_intentos": sesion.total_intentos,
                "total_aciertos": sesion.total_aciertos,
                "estado": sesion.estado,
                "porcentaje_acierto": round((sesion.total_aciertos / sesion.total_intentos * 100)
                                          if sesion.total_intentos > 0 else 0, 2)
            }

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de sesión: {e}")
            raise