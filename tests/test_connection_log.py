"""
Tests del registro de tiempo de conexión y de sus efectos en métricas y ranking.

Cubre: POST /api/user-connection-log (JSON y text/plain de sendBeacon, sin header Authorization),
validaciones del body, suma de tiempo en /metricas/usuario y exclusión de jugadores con 0 puntos del ranking.
"""

import json
import os
import time
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.shared.infrastructure.database.database import get_db
from app.shared.infrastructure.database.models import (
    Base,
    GameResultModel,
    UserConnectionLogModel,
    UserModel,
)
from app.shared.infrastructure.security.jwt_handler import create_access_token


# TEST_DATABASE_URL debe apuntar a una base de pruebas, nunca a la de producción.
SQLALCHEMY_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test_connection_log.db")
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def base_limpia():
    previo = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    if previo is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previo


def _crear_usuario(db, user_id: str, email: str, puntos: int = 0) -> None:
    ahora = int(time.time())
    db.add(UserModel(
        id=user_id, nombre="Ana", apellido="Test", email=email,
        password_hash="x", role="jugador", is_active=True,
        createdAt=ahora, updatedAt=ahora,
    ))
    if puntos:
        db.add(GameResultModel(
            id=f"res-{user_id}", user_id=user_id, ave_id=1, ave_nombre="Ave",
            respuesta_usuario="Ave", es_correcta=True, puntos_obtenidos=puntos,
            createdAt=ahora,
        ))
    db.commit()


def _cookie_para(user_id: str) -> dict:
    token = create_access_token({"sub": user_id, "role": "jugador", "email": "x@test.com"})
    return {"access_token": token}


@pytest.fixture
def usuario():
    db = TestingSessionLocal()
    _crear_usuario(db, "USER0000000000000000000001", "ana@test.com")
    db.close()
    return "USER0000000000000000000001"


def test_registra_tiempo_con_json(usuario):
    client.cookies = _cookie_para(usuario)
    r = client.post("/api/user-connection-log", json={"userId": usuario, "tiempoConectado": 11588})
    assert r.status_code == 201

    db = TestingSessionLocal()
    registros = db.query(UserConnectionLogModel).all()
    assert len(registros) == 1
    assert registros[0].user_id == usuario
    assert registros[0].tiempo_conectado_ms == 11588
    db.close()


def test_acepta_text_plain_de_sendbeacon(usuario):
    # sendBeacon manda el body como text/plain y sin header Authorization: se autentica por cookie
    client.cookies = _cookie_para(usuario)
    body = json.dumps({"userId": usuario, "tiempoConectado": 5000})
    r = client.post(
        "/api/user-connection-log",
        content=body,
        headers={"Content-Type": "text/plain;charset=UTF-8"},
    )
    assert r.status_code == 201


def test_ignora_userid_del_body_y_usa_el_de_la_sesion(usuario):
    otro = "USER0000000000000000000002"
    db = TestingSessionLocal()
    _crear_usuario(db, otro, "otro@test.com")
    db.close()

    client.cookies = _cookie_para(usuario)
    client.post("/api/user-connection-log", json={"userId": otro, "tiempoConectado": 1000})

    db = TestingSessionLocal()
    assert db.query(UserConnectionLogModel).one().user_id == usuario
    db.close()


def test_sin_cookie_responde_401():
    client.cookies = {}
    r = client.post("/api/user-connection-log", json={"tiempoConectado": 1000})
    assert r.status_code == 401


@pytest.mark.parametrize("body", [
    "no es json",
    json.dumps({"tiempoConectado": -1}),
    json.dumps({"tiempoConectado": "11588"}),
    json.dumps({"tiempoConectado": True}),
    json.dumps({"tiempoConectado": 86400001}),
    json.dumps({}),
])
def test_valida_el_body(usuario, body):
    client.cookies = _cookie_para(usuario)
    r = client.post("/api/user-connection-log", content=body,
                    headers={"Content-Type": "text/plain"})
    assert r.status_code == 422


def test_metricas_suman_tiempo_total_y_de_hoy(usuario):
    db = TestingSessionLocal()
    ahora = int(time.time())
    hace_dos_dias = int((datetime.now() - timedelta(days=2)).timestamp())
    db.add(UserConnectionLogModel(id="L1", user_id=usuario, tiempo_conectado_ms=10_000, createdAt=ahora))
    db.add(UserConnectionLogModel(id="L2", user_id=usuario, tiempo_conectado_ms=20_500, createdAt=ahora))
    db.add(UserConnectionLogModel(id="L3", user_id=usuario, tiempo_conectado_ms=60_000, createdAt=hace_dos_dias))
    db.commit()
    db.close()

    client.cookies = _cookie_para(usuario)
    r = client.get("/api/inaturalist/metricas/usuario")
    assert r.status_code == 200
    data = r.json()
    assert data["tiempo_conectado_total_seg"] == 90
    assert data["tiempo_conectado_hoy_seg"] == 30


def test_ranking_oculta_jugadores_con_cero_puntos():
    db = TestingSessionLocal()
    _crear_usuario(db, "USER0000000000000000000001", "ana@test.com", puntos=50)
    _crear_usuario(db, "USER0000000000000000000003", "cero@test.com", puntos=0)
    db.close()

    usuario = "USER0000000000000000000001"
    client.cookies = _cookie_para(usuario)
    r = client.get("/api/inaturalist/juego/ranking")
    assert r.status_code == 200
    ids = [j["user_id"] for j in r.json()["ranking"]]
    assert ids == [usuario]
    assert r.json()["total_jugadores"] == 1


def test_reintento_no_duplica_y_rechaza_cambios(usuario):
    client.cookies = _cookie_para(usuario)
    fin = int(time.time() * 1000)
    body = {"registroId": "reintento", "inicioMs": fin - 5000,
            "finMs": fin, "tiempoConectado": 5000}
    assert client.post("/api/user-connection-log", json=body).status_code == 201
    assert client.post("/api/user-connection-log", json=body).status_code == 201
    db = TestingSessionLocal()
    assert db.query(UserConnectionLogModel).count() == 1
    db.close()
    body["inicioMs"] -= 1000
    body["tiempoConectado"] += 1000
    assert client.post("/api/user-connection-log", json=body).status_code == 409


def test_intervalo_cruza_medianoche(usuario, monkeypatch):
    from zoneinfo import ZoneInfo
    from app.analytics_context.application.services import metrics_service
    zona = ZoneInfo("America/Argentina/Buenos_Aires")
    medianoche = int(datetime(2026, 11, 3, tzinfo=zona).timestamp())
    class RelojFijo(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromtimestamp(medianoche + 1200, tz)
    monkeypatch.setattr(metrics_service, "datetime", RelojFijo)
    monkeypatch.setattr(metrics_service, "_inicio_del_dia_argentina", lambda: medianoche)
    db = TestingSessionLocal()
    db.add(UserConnectionLogModel(id="medianoche", user_id=usuario,
        inicio_ms=(medianoche - 600) * 1000, fin_ms=(medianoche + 600) * 1000,
        tiempo_conectado_ms=1_200_000, createdAt=medianoche + 600))
    db.commit()
    resultado = metrics_service.MetricsService.obtener_metricas_usuario(db, usuario)
    assert resultado.tiempo_conectado_total_seg == 1200
    assert resultado.tiempo_conectado_hoy_seg == 600
    db.close()


@pytest.mark.parametrize("cambios", [
    {"inicioMs": True}, {"finMs": 0}, {"registroId": ""},
    {"tiempoConectado": 100}, {"finMs": None},
])
def test_valida_intervalo(usuario, cambios):
    client.cookies = _cookie_para(usuario)
    fin = int(time.time() * 1000)
    body = {"registroId": "valida", "inicioMs": fin - 5000,
            "finMs": fin, "tiempoConectado": 5000, **cambios}
    assert client.post("/api/user-connection-log", json=body).status_code == 422
