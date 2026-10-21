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
    nuevas de game_sessions en SQLite (aditivo, todas nullable).
    """
    if engine.dialect.name != "sqlite":
        return

    columnas = {
        "preguntas": "TEXT",
        "place_id": "INTEGER",
        "locale": "VARCHAR(20)",
    }
    with engine.begin() as conn:
        existentes = {fila[1] for fila in conn.execute(text("PRAGMA table_info(game_sessions)"))}
        for nombre, tipo in columnas.items():
            if nombre not in existentes:
                conn.execute(text(f"ALTER TABLE game_sessions ADD COLUMN {nombre} {tipo}"))


_agregar_columnas_faltantes(engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()