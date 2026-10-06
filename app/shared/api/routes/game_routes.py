from fastapi import APIRouter, Query, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.game_context.application.services.inaturalist_service import (
    INaturalistService,
    BirdsResponse,
    AvesResponse,
    GameAveResponse
)
from app.game_context.application.services.game_result_service import GameResultService
from app.game_context.application.services.game_session_service import GameSessionService
from app.analytics_context.application.services.metrics_service import MetricsService
from app.game_context.application.dtos.game_dto import (
    RespuestaJugadorRequest,
    RespuestaJugadorResponse,
    RankingResponse,
    JugadorRanking,
    IniciarSesionResponse,
    TerminarSesionResponse,
    EstadisticasSesionResponse
)
from app.analytics_context.application.dtos.metrics_dto import (
    MetricasUsuarioResponse,
    MetricasGlobalResponse
)
from app.shared.api.dependencies import get_current_user_model, get_db, get_admin_or_moderator
from app.shared.infrastructure.database.models import UserModel

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/inaturalist",
    tags=["Game"]
)


@router.post(
    "/juego/iniciar",
    response_model=IniciarSesionResponse,
    summary="Iniciar sesión de juego",
    description="⭐ Core | 🔐 Protegido | Inicia una nueva sesión de juego"
)
async def iniciar_juego(
    current_user: UserModel = Depends(get_current_user_model),
    db: Session = Depends(get_db)
) -> IniciarSesionResponse:
    """
    Inicia una nueva sesión de juego para el usuario.

    Cada sesión agrupa múltiples preguntas y guardará la puntuación total al finalizar.
    """
    try:
        session_id = GameSessionService.iniciar_sesion(db, current_user.id)
        return IniciarSesionResponse(
            session_id=session_id,
            mensaje="Sesión iniciada. Comienza a jugar."
        )
    except Exception as e:
        logger.error(f"Error iniciando sesión: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al iniciar sesión de juego"
        )


@router.post(
    "/juego/terminar",
    response_model=TerminarSesionResponse,
    summary="Terminar sesión de juego",
    description="⭐ Core | 🔐 Protegido | Finaliza la sesión y guarda la puntuación"
)
async def terminar_juego(
    current_user: UserModel = Depends(get_current_user_model),
    db: Session = Depends(get_db)
) -> TerminarSesionResponse:
    """
    Termina la sesión de juego activa y guarda la puntuación total.

    Calcula estadísticas finales y guarda en el historial de puntuaciones.
    """
    try:
        sesion_activa = GameSessionService.obtener_sesion_activa(db, current_user.id)
        if not sesion_activa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay una sesión activa"
            )

        stats = GameSessionService.terminar_sesion(db, sesion_activa.id)

        return TerminarSesionResponse(
            session_id=stats["session_id"],
            puntos_totales=stats["puntos_totales"],
            total_intentos=stats["total_intentos"],
            total_aciertos=stats["total_aciertos"],
            porcentaje_acierto=stats["porcentaje_acierto"],
            mensaje="Sesión finalizada. Puntuación guardada."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error terminando sesión: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al terminar la sesión"
        )


@router.get(
    "/juego/sesion/estadisticas",
    response_model=EstadisticasSesionResponse,
    summary="Obtener estadísticas de sesión",
    description="🔐 Protegido | Retorna estadísticas de la sesión activa"
)
async def get_session_stats(
    current_user: UserModel = Depends(get_current_user_model),
    db: Session = Depends(get_db)
) -> EstadisticasSesionResponse:
    """
    Obtiene las estadísticas de la sesión activa del usuario.
    """
    try:
        sesion_activa = GameSessionService.obtener_sesion_activa(db, current_user.id)
        if not sesion_activa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay una sesión activa"
            )

        stats = GameSessionService.get_session_stats(db, sesion_activa.id)

        return EstadisticasSesionResponse(**stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de sesión: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener estadísticas"
        )


@router.get(
    "/juego/aves",
    response_model=GameAveResponse,
    summary="Obtener pregunta del juego",
    description="⭐ Core | 🔐 Protegido | Retorna una pregunta del juego con 4 opciones (1 correcta + 3 falsas)"
)
async def get_birds_for_game(
    place_id: int = Query(10434, description="ID del lugar (10434=Buenos Aires, 7190=Argentina)"),
    locale: str = Query("es-AR", description="Idioma/localización"),
    current_user: UserModel = Depends(get_current_user_model),
    db: Session = Depends(get_db)
) -> GameAveResponse:
    """
    Obtiene una pregunta del juego con opciones generadas.

    🔐 Requiere autenticación (Bearer token)

    Retorna:
    - id: ID único del taxón
    - nombre: Nombre común en español (respuesta correcta)
    - nombreCientifico: Nombre científico
    - foto: URL de imagen
    - atribucion: Crédito fotográfico
    - opciones: Lista de 4 opciones (nombre e id)

    Parámetros:
    - **place_id**: 10434 (Buenos Aires) o 7190 (Argentina)
    - **locale**: Idioma de respuesta (es-AR, en-US, etc)
    """
    try:
        ave_correcta, todas_aves = await INaturalistService.get_birds_for_game(
            place_id=place_id,
            locale=locale
        )
        pregunta = INaturalistService.generar_pregunta_juego(ave_correcta, todas_aves)
        return GameAveResponse(ave=pregunta)
    except Exception as e:
        logger.error(f"Error obteniendo pregunta del juego: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudieron obtener las aves de iNaturalist"
        )


@router.post(
    "/juego/respuesta",
    response_model=RespuestaJugadorResponse,
    summary="Validar respuesta del juego",
    description="⭐ Core | 🔐 Protegido | Valida la respuesta del jugador y registra el resultado"
)
async def validar_respuesta(
    request: RespuestaJugadorRequest,
    current_user: UserModel = Depends(get_current_user_model),
    db: Session = Depends(get_db)
) -> RespuestaJugadorResponse:
    """
    Valida la respuesta del jugador y guarda el resultado en la sesión actual.

    Parámetros:
    - **ave_id**: ID del ave de la pregunta
    - **ave_nombre**: Nombre correcto del ave
    - **respuesta_usuario**: Respuesta seleccionada por el usuario
    """
    try:
        # Verificar que hay sesión activa
        sesion_activa = GameSessionService.obtener_sesion_activa(db, current_user.id)
        if not sesion_activa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay una sesión activa. Inicia una con POST /juego/iniciar"
            )

        # Validar que no haya respondido esta pregunta ya
        if not GameSessionService.validar_respuesta_unica(db, sesion_activa.id, request.ave_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya has respondido esta pregunta en esta sesión"
            )

        # Validar respuesta
        es_correcta, puntos = INaturalistService.validar_respuesta(
            request.ave_id,
            request.respuesta_usuario,
            request.ave_nombre
        )

        # Guardar resultado con session_id
        GameResultService.guardar_resultado(
            db=db,
            user_id=current_user.id,
            ave_id=request.ave_id,
            ave_nombre=request.ave_nombre,
            respuesta_usuario=request.respuesta_usuario,
            es_correcta=es_correcta,
            puntos_obtenidos=puntos,
            session_id=sesion_activa.id
        )

        mensaje = "¡Correcto! ✓" if es_correcta else "Incorrecto. ✗"

        return RespuestaJugadorResponse(
            es_correcta=es_correcta,
            puntos_obtenidos=puntos,
            mensaje=mensaje
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validando respuesta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar la respuesta"
        )


@router.get(
    "/juego/ranking",
    response_model=RankingResponse,
    summary="Obtener ranking de jugadores",
    description="⭐ Core | 🔐 Protegido | Retorna el ranking de los mejores jugadores"
)
async def get_ranking(
    limit: int = Query(10, ge=1, le=100, description="Cantidad de jugadores a mostrar"),
    current_user: UserModel = Depends(get_current_user_model),
    db: Session = Depends(get_db)
) -> RankingResponse:
    """
    Obtiene el ranking de jugadores ordenado por puntos totales.

    Parámetros:
    - **limit**: Cantidad de jugadores a retornar (1-100, default 10)
    """
    try:
        ranking_data = GameResultService.obtener_ranking(db, limit)
        ranking_jugadores = [
            JugadorRanking(
                user_id=r["user_id"],
                nombre=r["nombre"],
                apellido=r["apellido"],
                puntos_totales=r["puntos_totales"],
                aciertos=r["aciertos"],
                fallos=r["fallos"]
            )
            for r in ranking_data
        ]

        return RankingResponse(
            total_jugadores=len(ranking_jugadores),
            ranking=ranking_jugadores
        )

    except Exception as e:
        logger.error(f"Error obteniendo ranking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el ranking"
        )


@router.get(
    "/metricas/usuario",
    response_model=MetricasUsuarioResponse,
    summary="Obtener métricas del usuario",
    description="📊 Analítica | 🔐 Protegido | Retorna estadísticas personales del jugador autenticado"
)
async def get_metricas_usuario(
    current_user: UserModel = Depends(get_current_user_model),
    db: Session = Depends(get_db)
) -> MetricasUsuarioResponse:
    """
    Obtiene las métricas personales del usuario actual.

    Retorna:
    - total_intentos: Cantidad total de veces que jugó
    - total_aciertos: Cantidad de respuestas correctas
    - porcentaje_acierto: % de aciertos (0-100)
    - puntuacion_total: Puntos acumulados
    - posicion_ranking: Posición en el ranking global
    """
    try:
        metricas = MetricsService.obtener_metricas_usuario(db, current_user.id)
        return metricas
    except Exception as e:
        logger.error(f"Error obteniendo métricas del usuario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener métricas del usuario"
        )


@router.get(
    "/metricas/global",
    response_model=MetricasGlobalResponse,
    summary="Obtener métricas globales",
    description="📊 Analítica | 🔐 Solo Admin/Moderador | Retorna estadísticas del sistema completo"
)
async def get_metricas_global(
    current_user: UserModel = Depends(get_admin_or_moderator),
    db: Session = Depends(get_db)
) -> MetricasGlobalResponse:
    """
    Obtiene las métricas globales del juego.

    Retorna:
    - total_jugadores_activos: Cantidad de jugadores que han jugado
    - total_intentos_sistema: Total de intentos en el sistema
    - porcentaje_acierto_global: % de acierto promedio del sistema
    - ave_mas_acertada: Ave con mayor porcentaje de aciertos
    - ave_menos_acertada: Ave con menor porcentaje de aciertos
    """
    try:
        metricas = MetricsService.obtener_metricas_global(db)
        return metricas
    except Exception as e:
        logger.error(f"Error obteniendo métricas globales: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener métricas globales"
        )
