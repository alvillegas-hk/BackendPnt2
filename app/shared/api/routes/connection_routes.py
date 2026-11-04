import hashlib
import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
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
    Body: `{"tiempoConectado": <ms>, "inicioMs": <epoch ms>, "finMs": <epoch ms>,
    "registroId": "<identificador único del tramo>"}`. Los tres campos adicionales son
    opcionales para compatibilidad; juntos permiten reintentos sin duplicación y
    atribución por día. El campo `userId` que mande el cliente se ignora:
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

    inicio = datos.get("inicioMs")
    fin = datos.get("finMs")
    registro_id = datos.get("registroId")
    id_registro = str(ULID())
    if any(valor is not None for valor in (inicio, fin, registro_id)):
        if (not isinstance(registro_id, str) or not 1 <= len(registro_id) <= 128
                or type(inicio) is not int or type(fin) is not int
                or inicio < 0 or fin - inicio != tiempo_ms
                or fin > int(time.time() * 1000) + 60_000):
            raise HTTPException(status_code=422, detail="Intervalo de conexión inválido")
        id_registro = hashlib.sha256(f"{current_user.id}:{registro_id}".encode()).hexdigest()[:26]

    def comprobar_reintento():
        existente = db.get(UserConnectionLogModel, id_registro)
        if existente is None:
            return False
        if (existente.inicio_ms, existente.fin_ms, existente.tiempo_conectado_ms) != (inicio, fin, tiempo_ms):
            raise HTTPException(status_code=409, detail="registroId ya utilizado para otro intervalo")
        return True

    if comprobar_reintento():
        return {"status": "ok", "tiempo_conectado_ms": tiempo_ms}
    try:
        registro = UserConnectionLogModel(
            id=id_registro,
            inicio_ms=inicio,
            fin_ms=fin,
            user_id=current_user.id,
            tiempo_conectado_ms=tiempo_ms,
            createdAt=int(time.time())
        )
        db.add(registro)
        db.commit()
    except IntegrityError:
        db.rollback()
        if not comprobar_reintento():
            raise HTTPException(status_code=500, detail="Error al guardar el tiempo de conexión")
    except Exception as e:
        logger.error(f"Error guardando tiempo de conexión: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar el tiempo de conexión"
        )

    return {"status": "ok", "tiempo_conectado_ms": tiempo_ms}
