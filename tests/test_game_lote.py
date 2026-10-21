"""
Tests del lote de preguntas guardado en la sesión de juego.

Cubre: lote generado al iniciar, /juego/aves devuelve el mismo lote mientras la sesión está activa,
validación de respuestas contra el lote, GET /juego/sesion para retomar la partida,
cierre de sesiones previas al iniciar y migración de columnas en SQLite.
"""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.game_context.application.services.inaturalist_service import Ave, INaturalistService
from app.shared.infrastructure.database.database import _agregar_columnas_faltantes, get_db
from app.shared.infrastructure.database.models import Base, GameSessionModel


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_game_lote.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


def _aves_falsas(cantidad: int) -> list[Ave]:
    return [
        Ave(
            id=1000 + i,
            nombre=f"Ave {i}",
            nombreCientifico=f"Avis testus {i}",
            foto=f"https://example.com/{i}.jpg",
            atribucion="Test",
        )
        for i in range(cantidad)
    ]


@pytest.fixture(autouse=True)
def base_limpia_y_inat_falso(monkeypatch):
    """Reinicia la base, usa su propia DB de test y reemplaza iNaturalist por 15 aves fijas (sin red)."""
    previo = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    aves = _aves_falsas(15)

    async def get_birds_falso(place_id: int = 10434, locale: str = "es-AR"):
        return aves[0], aves

    monkeypatch.setattr(INaturalistService, "get_birds_for_game", get_birds_falso)
    yield

    if previo is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previo


@pytest.fixture
def auth_headers():
    response = client.post(
        "/auth/register",
        json={
            "nombre": "Lote",
            "apellido": "Test",
            "email": "lote@example.com",
            "password": "LoteTest123!",
        },
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _iniciar(headers):
    response = client.post("/api/inaturalist/juego/iniciar", headers=headers)
    assert response.status_code == 200
    return response.json()["session_id"]


def _responder(headers, pregunta: dict, respuesta: str, ave_nombre: str | None = None):
    body = {"ave_id": pregunta["id"], "respuesta_usuario": respuesta}
    if ave_nombre is not None:
        body["ave_nombre"] = ave_nombre
    return client.post("/api/inaturalist/juego/respuesta", headers=headers, json=body)


class TestLoteGuardado:

    def test_iniciar_guarda_lote_de_10_en_la_sesion(self, auth_headers):
        session_id = _iniciar(auth_headers)

        db = TestingSessionLocal()
        try:
            sesion = db.query(GameSessionModel).filter(GameSessionModel.id == session_id).one()
            assert sesion.preguntas is not None
            assert sesion.place_id == 10434
            assert sesion.locale == "es-AR"
        finally:
            db.close()

        response = client.get("/api/inaturalist/juego/sesion", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["preguntas"]) == 10

    def test_juego_aves_devuelve_el_mismo_lote_mientras_la_sesion_esta_activa(self, auth_headers):
        _iniciar(auth_headers)

        primero = client.get("/api/inaturalist/juego/aves", headers=auth_headers).json()
        segundo = client.get("/api/inaturalist/juego/aves", headers=auth_headers).json()

        assert primero["total"] == 10
        assert primero == segundo

    def test_juego_aves_sin_sesion_sigue_generando_lote_nuevo(self, auth_headers):
        response = client.get("/api/inaturalist/juego/aves", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 10

    def test_iniciar_responde_503_si_inaturalist_falla_y_no_crea_sesion(self, auth_headers, monkeypatch):
        async def fallar(place_id: int = 10434, locale: str = "es-AR"):
            raise httpx.ConnectError("sin red")

        monkeypatch.setattr(INaturalistService, "get_birds_for_game", fallar)

        response = client.post("/api/inaturalist/juego/iniciar", headers=auth_headers)
        assert response.status_code == 503

        sin_sesion = client.get("/api/inaturalist/juego/sesion", headers=auth_headers)
        assert sin_sesion.status_code == 404


class TestValidacionContraLote:

    def test_respuesta_correcta_usa_el_nombre_del_lote_no_el_del_cliente(self, auth_headers):
        _iniciar(auth_headers)
        pregunta = client.get("/api/inaturalist/juego/sesion", headers=auth_headers).json()["preguntas"][0]

        # El cliente manda un ave_nombre trucado: no debe cambiar el resultado
        response = _responder(auth_headers, pregunta, pregunta["nombre"], ave_nombre="Cualquiera")

        assert response.status_code == 200
        assert response.json()["es_correcta"] is True

    def test_respuesta_incorrecta_se_marca_aunque_el_cliente_mande_el_nombre_correcto(self, auth_headers):
        _iniciar(auth_headers)
        pregunta = client.get("/api/inaturalist/juego/sesion", headers=auth_headers).json()["preguntas"][0]

        response = _responder(auth_headers, pregunta, "Otra cosa", ave_nombre=pregunta["nombre"])

        assert response.status_code == 200
        assert response.json()["es_correcta"] is False

    def test_ave_fuera_del_lote_se_rechaza(self, auth_headers):
        _iniciar(auth_headers)

        response = client.post(
            "/api/inaturalist/juego/respuesta",
            headers=auth_headers,
            json={"ave_id": 999999, "respuesta_usuario": "Cualquiera"},
        )

        assert response.status_code == 400
        assert "lote" in response.json()["detail"]

    def test_sesion_sin_lote_responde_409(self, auth_headers):
        """Sesión creada antes de guardar lotes: no se puede validar, se pide cerrarla."""
        session_id = _iniciar(auth_headers)

        db = TestingSessionLocal()
        try:
            db.query(GameSessionModel).filter(GameSessionModel.id == session_id).update({"preguntas": None})
            db.commit()
        finally:
            db.close()

        response = client.post(
            "/api/inaturalist/juego/respuesta",
            headers=auth_headers,
            json={"ave_id": 1000, "respuesta_usuario": "Ave 0"},
        )

        assert response.status_code == 409


class TestRetomarSesion:

    def test_sesion_sin_sesion_activa_responde_404(self, auth_headers):
        response = client.get("/api/inaturalist/juego/sesion", headers=auth_headers)
        assert response.status_code == 404

    def test_retomar_muestra_lote_respuestas_y_puntos(self, auth_headers):
        _iniciar(auth_headers)
        preguntas = client.get("/api/inaturalist/juego/sesion", headers=auth_headers).json()["preguntas"]

        _responder(auth_headers, preguntas[0], preguntas[0]["nombre"])  # correcta
        _responder(auth_headers, preguntas[1], "Otra cosa")  # incorrecta

        response = client.get("/api/inaturalist/juego/sesion", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert len(data["preguntas"]) == 10
        assert [r["ave_id"] for r in data["respuestas"]] == [preguntas[0]["id"], preguntas[1]["id"]]
        assert [r["es_correcta"] for r in data["respuestas"]] == [True, False]
        assert data["puntos_totales"] == sum(r["puntos_obtenidos"] + r["bonus_racha"] for r in data["respuestas"])
        assert data["streak_actual"] == 0

    def test_retomar_no_cambia_el_lote_al_recargar(self, auth_headers):
        _iniciar(auth_headers)

        primero = client.get("/api/inaturalist/juego/sesion", headers=auth_headers).json()["preguntas"]
        recargado = client.get("/api/inaturalist/juego/sesion", headers=auth_headers).json()["preguntas"]

        assert primero == recargado


class TestCierreDeSesionesPrevias:

    def test_iniciar_cierra_la_sesion_anterior_y_deja_una_sola_activa(self, auth_headers):
        primera = _iniciar(auth_headers)
        segunda = _iniciar(auth_headers)

        assert primera != segunda

        db = TestingSessionLocal()
        try:
            activas = db.query(GameSessionModel).filter(GameSessionModel.estado == "activa").all()
            assert [s.id for s in activas] == [segunda]
            anterior = db.query(GameSessionModel).filter(GameSessionModel.id == primera).one()
            assert anterior.estado == "terminada"
        finally:
            db.close()


class TestMigracionColumnas:

    def test_agrega_columnas_nuevas_a_una_tabla_vieja(self, tmp_path):
        engine_viejo = create_engine(f"sqlite:///{tmp_path / 'viejo.db'}")
        with engine_viejo.begin() as conn:
            conn.execute(text(
                "CREATE TABLE game_sessions (id VARCHAR(26) PRIMARY KEY, user_id VARCHAR(26), "
                "estado VARCHAR(50), createdAt INTEGER)"
            ))

        _agregar_columnas_faltantes(engine_viejo)
        # Segunda ejecución: no debe fallar aunque las columnas ya existan
        _agregar_columnas_faltantes(engine_viejo)

        with engine_viejo.begin() as conn:
            columnas = {fila[1] for fila in conn.execute(text("PRAGMA table_info(game_sessions)"))}
        assert {"preguntas", "place_id", "locale"} <= columnas
        engine_viejo.dispose()
