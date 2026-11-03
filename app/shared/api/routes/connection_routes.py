import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from ulid import ULID

from app.shared.api.dependencies import get_current_user_model, get_db
from app.shared.infrastructure.database.models import UserConnectionLogModel, UserModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Connection"]
)

# Tope por registro: 24 h. Evita guardar valores absurdos si el cliente manda basura.
MAX_TIEMPO_CONECTADO_MS = 24 * 60 * 60 * 1000


@router.post(
    "/user-connection-log",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar tiempo de conexión",
    description="🔐 Protegido | Guarda el tiempo conectado (en ms) al cerrar sesión o la pestaña. "
                "Acepta text/plain (lo envía navigator.sendBeacon). El usuario sale de la cookie de sesión."
)
async def registrar_tiempo_conexion(
    request: Request,
    current_user: UserModel = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """
    Body JSON: `{"tiempoConectado": <ms>}`. El campo `userId` que mande el cliente se ignora:
    el dueño del registro siempre es el usuario autenticado.
    """
    try:
        datos = json.loads(await request.body() or b"{}")
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El body debe ser JSON válido"
        )

    tiempo_ms = datos.get("tiempoConectado") if isinstance(datos, dict) else None
    if not isinstance(tiempo_ms, int) or isinstance(tiempo_ms, bool) or not 0 <= tiempo_ms <= MAX_TIEMPO_CONECTADO_MS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tiempoConectado debe ser un entero en ms entre 0 y 86400000"
        )

    try:
        registro = UserConnectionLogModel(
            id=str(ULID()),
            user_id=current_user.id,
            tiempo_conectado_ms=tiempo_ms,
            createdAt=int(time.time())
        )
        db.add(registro)
        db.commit()
    except Exception as e:
        logger.error(f"Error guardando tiempo de conexión: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar el tiempo de conexión"
        )

    return {"status": "ok", "tiempo_conectado_ms": tiempo_ms}
