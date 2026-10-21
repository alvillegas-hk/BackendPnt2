from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.infrastructure.config.settings import get_settings
from app.shared.infrastructure.database.models import Base

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.app_debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def _agregar_columnas_faltantes(engine) -> None:
    """
    create_all no agrega columnas a tablas existentes. Agrega las columnas
    nuevas de game_sessions y game_results en SQLite (aditivo). Las columnas
    NOT NULL llevan DEFAULT 0 porque SQLite lo exige para ALTER ADD COLUMN.
    """
    if engine.dialect.name != "sqlite":
        return

    columnas_por_tabla = {
        "game_sessions": {
            "preguntas": "TEXT",
            "place_id": "INTEGER",
            "locale": "VARCHAR(20)",
            "streak_actual": "INTEGER NOT NULL DEFAULT 0",
            "streak_maximo": "INTEGER NOT NULL DEFAULT 0",
        },
        "game_results": {
            "session_id": "VARCHAR(26)",
            "bonus_racha": "INTEGER NOT NULL DEFAULT 0",
            "streak_en_respuesta": "INTEGER NOT NULL DEFAULT 0",
        },
    }
    with engine.begin() as conn:
        for tabla, columnas in columnas_por_tabla.items():
            existentes = {fila[1] for fila in conn.execute(text(f"PRAGMA table_info({tabla})"))}
            for nombre, tipo in columnas.items():
                if nombre not in existentes:
                    conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}"))


_agregar_columnas_faltantes(engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()