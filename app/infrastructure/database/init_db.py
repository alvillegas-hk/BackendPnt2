import logging
from sqlalchemy.orm import Session
from ulid import ULID
import time
from app.infrastructure.database.models import Base, UserModel
from app.infrastructure.database.database import engine, SessionLocal
from app.infrastructure.config.settings import get_settings
from app.infrastructure.security.password import hash_password

logger = logging.getLogger(__name__)


def init_db():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    settings = get_settings()

    try:
        existing_admin = db.query(UserModel).filter(UserModel.email == settings.admin_email).first()

        if not existing_admin:
            now = int(time.time() * 1000)
            admin_password = settings.admin_password[:72] if len(settings.admin_password) > 72 else settings.admin_password
            admin_user = UserModel(
                id=str(ULID()),
                nombre="Admin",
                apellido="Admin",
                email=settings.admin_email,
                password_hash=hash_password(admin_password),
                role="admin",
                is_active=True,
                createdAt=now,
                updatedAt=now
            )
            db.add(admin_user)
            db.commit()
            logger.info(f"Usuario admin creado: {settings.admin_email}")
        else:
            logger.info(f"Usuario admin ya existe: {settings.admin_email}")

    except Exception as e:
        logger.error(f"Error inicializando BD: {e}")
        db.rollback()

    finally:
        db.close()
