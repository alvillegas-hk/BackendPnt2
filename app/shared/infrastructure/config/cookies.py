import os
from dotenv import load_dotenv

load_dotenv()

# Ambiente
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# Configuración de Cookies HttpOnly
# HttpOnly siempre True (seguro incluso en desarrollo)
# Secure y SameSite varían según el ambiente
COOKIE_CONFIG = {
    "httponly": True,  # ✅ Siempre seguro
    "secure": IS_PRODUCTION,  # True en producción, False en desarrollo
    "samesite": "Strict" if IS_PRODUCTION else "Lax",
    "path": "/"
}

# Tiempos de expiración (configurables desde .env)
# Se convierten a segundos para max_age de cookies
ACCESS_TOKEN_EXPIRE = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")) * 60  # En minutos, convierte a segundos
REFRESH_TOKEN_EXPIRE = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")) * 86400  # En días, convierte a segundos
