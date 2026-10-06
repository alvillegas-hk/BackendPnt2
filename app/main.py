from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from scalar_fastapi import get_scalar_api_reference
import logging
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import engine
from app.infrastructure.database.models import Base
from app.api.routes import auth, users

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API para gestión de usuarios y puntuaciones del juego",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/", tags=["health"])
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version
    }


@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )


@app.get("/documentation", tags=["documentation"])
async def get_documentation():
    return {
        "scalar_url": "/scalar",
        "swagger_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
