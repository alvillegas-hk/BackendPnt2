"""
Seed de usuarios con sesiones de juego y puntajes para desarrollo.

Uso (desde C:\\PNT2):
    .venv\\Scripts\\python.exe -m app.shared.infrastructure.database.seed_users

Crea CANTIDAD_USUARIOS jugadores con partidas terminadas, resultados por pregunta
y un registro en scores por cada partida. Es idempotente: los emails que ya existen
se omiten.
"""
import logging
import random
import time

from sqlalchemy import func
from ulid import ULID

from app.game_context.infrastructure.nombres_argentinos import NOMBRES_ARGENTINOS
from app.infrastructure.security.password import hash_password
from app.shared.infrastructure.database.database import SessionLocal
from app.shared.infrastructure.database.models import (
    GameResultModel,
    GameSessionModel,
    ScoreModel,
    UserModel,
)

logger = logging.getLogger(__name__)

CANTIDAD_USUARIOS = 100
CANTIDAD_MODERADORES = 3
PASSWORD_SEED = "Jugador123"
DOMINIO = "example.com"
PREGUNTAS_POR_SESION = 10
PUNTOS_POR_ACIERTO = 10
SEED_RANDOM = 42

NOMBRES = [
    "Lucía", "Mateo", "Valentina", "Santiago", "Sofía", "Thiago", "Camila", "Benjamín",
    "Martina", "Joaquín", "Emma", "Bautista", "Julieta", "Tomás", "Catalina", "Lautaro",
    "Agustina", "Nicolás", "Milagros", "Facundo", "Renata", "Ignacio", "Paula", "Federico",
    "Victoria", "Lorenzo", "Delfina", "Gonzalo", "Josefina", "Matías", "Abril", "Ramiro",
]
APELLIDOS = [
    "González", "Rodríguez", "Gómez", "Fernández", "López", "Martínez", "Pérez", "Sánchez",
    "Romero", "Díaz", "Torres", "Álvarez", "Ruiz", "Ramírez", "Flores", "Acosta",
    "Benítez", "Medina", "Herrera", "Suárez", "Aguirre", "Pereyra", "Castro", "Ojeda",
]


def _bono_racha(streak: int) -> int:
    """Mismo criterio que la ruta /juego/respuesta."""
    if streak == 3:
        return 5
    if streak == 5:
        return 15
    if streak >= 10:
        return 50
    return 0


def _simular_partida(rng: random.Random, db, user_id: str, precision: float, ahora_ms: int) -> None:
    """Crea una sesión terminada con sus resultados y su score, igual que el juego real."""
    aves = list(NOMBRES_ARGENTINOS.items())
    lote = rng.sample(aves, PREGUNTAS_POR_SESION)
    nombres = [nombre for _, nombre in aves]

    session_id = str(ULID())
    inicio = int(ahora_ms / 1000) - rng.randint(0, 60 * 60 * 24 * 60)
    sesion = GameSessionModel(
        id=session_id,
        user_id=user_id,
        puntos_totales=0,
        total_intentos=0,
        total_aciertos=0,
        streak_actual=0,
        streak_maximo=0,
        estado="activa",
        createdAt=inicio,
        place_id=10434,
        locale="es-AR",
    )
    db.add(sesion)
    db.flush()

    streak = 0
    for ave_id, nombre_correcto in lote:
        es_correcta = rng.random() < precision
        if es_correcta:
            respuesta = nombre_correcto
            streak += 1
            puntos = PUNTOS_POR_ACIERTO
        else:
            respuesta = rng.choice([n for n in nombres if n != nombre_correcto])
            streak = 0
            puntos = 0
        bonus = _bono_racha(streak) if es_correcta else 0

        db.add(GameResultModel(
            id=str(ULID()),
            user_id=user_id,
            session_id=session_id,
            ave_id=ave_id,
            ave_nombre=nombre_correcto,
            respuesta_usuario=respuesta,
            es_correcta=es_correcta,
            puntos_obtenidos=puntos,
            bonus_racha=bonus,
            streak_en_respuesta=streak,
            createdAt=inicio + rng.randint(5, 30),
        ))

    db.flush()
    resultados = db.query(GameResultModel).filter(GameResultModel.session_id == session_id).all()
    aciertos = sum(1 for r in resultados if r.es_correcta)
    puntos_totales = sum(r.puntos_obtenidos for r in resultados)
    fin = inicio + rng.randint(120, 900)

    sesion.puntos_totales = puntos_totales
    sesion.total_intentos = len(resultados)
    sesion.total_aciertos = aciertos
    sesion.streak_actual = streak
    sesion.streak_maximo = max(r.streak_en_respuesta for r in resultados)
    sesion.estado = "terminada"
    sesion.terminadaAt = fin

    db.add(ScoreModel(
        id=str(ULID()),
        user_id=user_id,
        puntos=puntos_totales,
        juego="birds_game",
        fecha=fin,
        createdAt=fin,
    ))


def seed_usuarios() -> None:
    rng = random.Random(SEED_RANDOM)
    db = SessionLocal()
    try:
        emails_existentes = {email for (email,) in db.query(UserModel.email).all()}
        password_hash = hash_password(PASSWORD_SEED)
        ahora_ms = int(time.time() * 1000)
        creados = 0

        for i in range(1, CANTIDAD_USUARIOS + 1):
            email = f"jugador{i:03d}@{DOMINIO}"
            if email in emails_existentes:
                continue

            user_id = str(ULID())
            creado_ms = ahora_ms - rng.randint(1, 90) * 24 * 60 * 60 * 1000
            db.add(UserModel(
                id=user_id,
                nombre=rng.choice(NOMBRES),
                apellido=rng.choice(APELLIDOS),
                email=email,
                password_hash=password_hash,
                role="moderador" if i <= CANTIDAD_MODERADORES else "jugador",
                is_active=True,
                createdAt=creado_ms,
                updatedAt=creado_ms,
                lastLogin=min(creado_ms + rng.randint(1, 30) * 24 * 60 * 60 * 1000, ahora_ms),
            ))
            db.flush()

            precision = rng.uniform(0.2, 0.9)
            for _ in range(rng.randint(1, 5)):
                _simular_partida(rng, db, user_id, precision, ahora_ms)
            creados += 1

        db.commit()
        logger.info(f"Seed de usuarios: {creados} usuarios creados")
    except Exception as e:
        logger.error(f"Error en seed de usuarios: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def seed_si_no_existe() -> bool:
    """
    Carga el seed solo si todavía no está cargado. Se llama al iniciar la app.
    Devuelve True si cargó datos en esta ejecución.
    """
    db = SessionLocal()
    try:
        cantidad = db.query(func.count(UserModel.id)).filter(
            UserModel.email.like(f"jugador%@{DOMINIO}")
        ).scalar()
    finally:
        db.close()

    if cantidad >= CANTIDAD_USUARIOS:
        logger.info("Seed de usuarios ya cargado, se omite")
        return False

    seed_usuarios()
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_si_no_existe()
