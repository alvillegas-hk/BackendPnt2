"""
Copia los datos de sqlite.db a la base de datos destino (PostgreSQL).

Uso (desde la raíz del proyecto):
    python scripts/migrar_sqlite_a_postgres.py --destino "postgresql+psycopg://usuario:clave@localhost:5432/gamemanager"

Qué hace:
  1. Crea en el destino las tablas con el esquema de los modelos (create_all).
  2. Aborta si alguna tabla destino ya tiene filas, para no duplicar datos.
  3. Copia todas las tablas en orden de dependencias (FK) y convierte los
     booleanos de SQLite (0/1) a bool.
  4. Compara los conteos de origen y destino. Todo ocurre en UNA transacción:
     si algo falla, no queda nada copiado a medias.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import Boolean, create_engine, func, select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.shared.infrastructure.database.models import Base  # noqa: E402


def contar_origen(origen: sqlite3.Connection, nombre: str) -> int:
    return origen.execute(f"SELECT COUNT(*) FROM {nombre}").fetchone()[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra sqlite.db a PostgreSQL")
    parser.add_argument("--sqlite", default="sqlite.db", help="Ruta al archivo SQLite de origen")
    parser.add_argument("--destino", required=True, help="URL SQLAlchemy de la base destino")
    parser.add_argument("--lote", type=int, default=1000, help="Filas por INSERT")
    args = parser.parse_args()

    origen = sqlite3.connect(args.sqlite)
    origen.row_factory = sqlite3.Row
    tablas_origen = {r[0] for r in origen.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    destino = create_engine(args.destino)
    Base.metadata.create_all(bind=destino)

    tablas = [t for t in Base.metadata.sorted_tables if t.name in tablas_origen]
    omitidas = [t.name for t in Base.metadata.sorted_tables if t.name not in tablas_origen]
    for nombre in omitidas:
        print(f"[omitida] {nombre}: no existe en el origen")

    with destino.begin() as conn:
        for tabla in tablas:
            filas_destino = conn.execute(select(func.count()).select_from(tabla)).scalar()
            if filas_destino:
                raise SystemExit(
                    f"Abortado: la tabla destino '{tabla.name}' ya tiene {filas_destino} filas. "
                    "Vacíala antes de migrar."
                )

        for tabla in tablas:
            columnas_origen = {r[1] for r in origen.execute(f"PRAGMA table_info({tabla.name})")}
            columnas = [c for c in tabla.columns if c.name in columnas_origen]
            nombres = ", ".join(c.name for c in columnas)

            copiadas = 0
            lote = []
            for fila in origen.execute(f"SELECT {nombres} FROM {tabla.name}"):
                registro = {}
                for c in columnas:
                    valor = fila[c.name]
                    if isinstance(c.type, Boolean) and valor is not None:
                        valor = bool(valor)
                    registro[c.name] = valor
                lote.append(registro)
                if len(lote) >= args.lote:
                    conn.execute(tabla.insert(), lote)
                    copiadas += len(lote)
                    lote = []
            if lote:
                conn.execute(tabla.insert(), lote)
                copiadas += len(lote)
            print(f"[copiada] {tabla.name}: {copiadas} filas")

        # Verificación de conteos dentro de la misma transacción
        for tabla in tablas:
            esperadas = contar_origen(origen, tabla.name)
            obtenidas = conn.execute(select(func.count()).select_from(tabla)).scalar()
            if esperadas != obtenidas:
                raise SystemExit(
                    f"Abortado: '{tabla.name}' tiene {obtenidas} filas en destino y {esperadas} en origen."
                )
            print(f"[ok] {tabla.name}: {obtenidas} filas verificadas")

    origen.close()
    destino.dispose()
    print("Migración completada.")


if __name__ == "__main__":
    main()
