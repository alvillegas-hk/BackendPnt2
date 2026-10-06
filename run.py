#!/usr/bin/env python3
import uvicorn
import os
import sys
from app.infrastructure.database.init_db import init_db

if __name__ == "__main__":
    print("Inicializando base de datos...")
    init_db()

    print("Iniciando servidor...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
