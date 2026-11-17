import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics_context.application.services.metrics_service import MetricsService
from app.game_context.application.services.game_result_service import GameResultService
from app.shared.infrastructure.database.models import Base, GameResultModel, UserModel


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _crear_usuario(db, user_id, nombre=None):
    usuario = UserModel(
        id=user_id,
        nombre=nombre or user_id,
        apellido="Jugador",
        email=f"{user_id}@example.com",
        password_hash="hash",
        role="jugador",
        is_active=True,
        createdAt=1,
        updatedAt=1,
    )
    db.add(usuario)
    return usuario


def test_ranking_pagina_sobre_agregados_con_puesto_global_y_total_completo(db):
    for indice in range(102):
        user_id = f"player-{indice:03}"
        _crear_usuario(db, user_id)
        puntos = 102 if indice < 2 else 102 - indice
        db.add(GameResultModel(
            id=f"result-{indice:03}",
            user_id=user_id,
            ave_id=indice,
            ave_nombre="Ave",
            respuesta_usuario="Ave",
            es_correcta=indice % 2 == 0,
            puntos_obtenidos=puntos,
            bonus_racha=0,
            streak_en_respuesta=0,
            createdAt=indice,
        ))
    _crear_usuario(db, "player-no-results")
    db.commit()

    primera = GameResultService.obtener_ranking_paginado(
        db, limit=10, offset=0, user_id="player-101"
    )
    segunda = GameResultService.obtener_ranking_paginado(db, limit=10, offset=10)
    ultima = GameResultService.obtener_ranking_paginado(db, limit=100, offset=100)

    assert primera["total_jugadores"] == 102
    assert [fila["posicion"] for fila in primera["ranking"]] == list(range(1, 11))
    assert primera["ranking"][0]["user_id"] == "player-000"
    assert primera["ranking"][1]["user_id"] == "player-001"
    assert [fila["posicion"] for fila in segunda["ranking"]] == list(range(11, 21))
    assert len(ultima["ranking"]) == 2
    assert [fila["posicion"] for fila in ultima["ranking"]] == [101, 102]
    assert primera["jugador_actual"]["posicion"] == 102
    assert primera["jugador_actual"]["fallos"] == 1


def test_usuario_sin_respuestas_no_recibe_puesto_inventado(db):
    _crear_usuario(db, "player-no-results", "Sin Respuestas")
    db.commit()

    ranking = GameResultService.obtener_ranking_paginado(
        db, user_id="player-no-results"
    )
    metricas = MetricsService.obtener_metricas_usuario(db, "player-no-results")

    assert ranking["total_jugadores"] == 0
    assert ranking["ranking"] == []
    assert ranking["jugador_actual"] == {
        "user_id": "player-no-results",
        "nombre": "Sin Respuestas",
        "apellido": "Jugador",
        "puntos_totales": 0,
        "aciertos": 0,
        "fallos": 0,
        "posicion": None,
    }
    assert metricas.total_intentos == 0
    assert metricas.posicion_ranking is None


def test_usuario_con_respuestas_y_cero_puntos_conserva_estadisticas_sin_posicion(db):
    _crear_usuario(db, "player-zero-points", "Cero Puntos")
    db.add(GameResultModel(
        id="result-zero-points",
        user_id="player-zero-points",
        ave_id=1,
        ave_nombre="Ave",
        respuesta_usuario="Ave",
        es_correcta=True,
        puntos_obtenidos=0,
        bonus_racha=0,
        streak_en_respuesta=0,
        createdAt=1,
    ))
    db.commit()

    ranking = GameResultService.obtener_ranking_paginado(
        db, user_id="player-zero-points"
    )
    metricas = MetricsService.obtener_metricas_usuario(db, "player-zero-points")

    assert ranking["total_jugadores"] == 0
    assert ranking["ranking"] == []
    assert ranking["jugador_actual"] == {
        "user_id": "player-zero-points",
        "nombre": "Cero Puntos",
        "apellido": "Jugador",
        "puntos_totales": 0,
        "aciertos": 1,
        "fallos": 0,
        "posicion": None,
    }
    assert metricas.total_intentos == 1
    assert metricas.total_aciertos == 1
    assert metricas.posicion_ranking is None


def test_interfaz_anterior_y_metricas_comparten_posicion_global(db):
    for indice in range(3):
        user_id = f"player-{indice:03}"
        _crear_usuario(db, user_id)
        db.add(GameResultModel(
            id=f"result-{indice:03}",
            user_id=user_id,
            ave_id=indice,
            ave_nombre="Ave",
            respuesta_usuario="Ave",
            es_correcta=True,
            puntos_obtenidos=10 if indice < 2 else 1,
            bonus_racha=0,
            streak_en_respuesta=0,
            createdAt=indice,
        ))
    db.commit()

    ranking = GameResultService.obtener_ranking(db, 2)
    metricas = MetricsService.obtener_metricas_usuario(db, "player-002")

    assert len(ranking) == 2
    assert [jugador["posicion"] for jugador in ranking] == [1, 2]
    assert ranking[0]["user_id"] == "player-000"
    assert ranking[1]["user_id"] == "player-001"
    assert metricas.posicion_ranking == 3


def test_suma_varias_respuestas_por_jugador_y_comparte_posicion_con_metricas(db):
    _crear_usuario(db, "player-multiple", "Varias Respuestas")
    _crear_usuario(db, "player-leading", "Líder")
    _crear_usuario(db, "player-lower", "Menos Puntos")

    respuestas = [
        ("result-multiple-1", "player-multiple", True, 5, 2),
        ("result-multiple-2", "player-multiple", False, 3, 4),
        ("result-multiple-3", "player-multiple", True, 1, 0),
        ("result-leading", "player-leading", True, 16, 0),
        ("result-lower", "player-lower", False, 14, 0),
    ]
    for resultado_id, user_id, es_correcta, puntos, bonus in respuestas:
        db.add(GameResultModel(
            id=resultado_id,
            user_id=user_id,
            ave_id=1,
            ave_nombre="Ave",
            respuesta_usuario="Ave" if es_correcta else "Otra respuesta",
            es_correcta=es_correcta,
            puntos_obtenidos=puntos,
            bonus_racha=bonus,
            streak_en_respuesta=0,
            createdAt=1,
        ))
    db.commit()

    ranking = GameResultService.obtener_ranking_paginado(
        db, limit=10, offset=0, user_id="player-multiple"
    )
    jugador_en_ranking = next(
        jugador for jugador in ranking["ranking"]
        if jugador["user_id"] == "player-multiple"
    )
    metricas = MetricsService.obtener_metricas_usuario(db, "player-multiple")

    assert ranking["total_jugadores"] == 3
    assert sum(
        jugador["user_id"] == "player-multiple"
        for jugador in ranking["ranking"]
    ) == 1
    assert jugador_en_ranking["puntos_totales"] == 15
    assert jugador_en_ranking["aciertos"] == 2
    assert jugador_en_ranking["fallos"] == 1
    assert jugador_en_ranking["posicion"] == 2
    assert ranking["jugador_actual"]["posicion"] == jugador_en_ranking["posicion"]
    assert ranking["jugador_actual"]["puntos_totales"] == jugador_en_ranking["puntos_totales"]
    assert metricas.total_intentos == 3
    assert metricas.total_aciertos == 2
    assert metricas.puntuacion_total == 15
    assert metricas.posicion_ranking == jugador_en_ranking["posicion"]
