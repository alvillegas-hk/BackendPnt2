#!/usr/bin/env python3
"""
Script para refactorizar el proyecto en contextos limitados.
Mueve archivos y actualiza imports automáticamente.
"""
import os
import shutil
from pathlib import Path

BASE = Path("C:/PNT2/app")

# Mapeo de archivos a mover: (source, destination)
MOVES = [
    # Authentication Context
    ("domain/entities/user.py", "authentication_context/domain/entities/user.py"),
    ("domain/repositories/user_repository.py", "authentication_context/domain/repositories/user_repository.py"),
    ("application/services/auth_service.py", "authentication_context/application/services/auth_service.py"),
    ("application/services/user_service.py", "authentication_context/application/services/user_service.py"),
    ("application/dtos/user_dto.py", "authentication_context/application/dtos/user_dto.py"),
    ("infrastructure/repositories/user_repository_impl.py", "authentication_context/infrastructure/repositories/user_repository_impl.py"),

    # Game Context
    ("domain/entities/game_result.py", "game_context/domain/entities/game_result.py"),
    ("application/services/game_result_service.py", "game_context/application/services/game_result_service.py"),
    ("application/services/game_session_service.py", "game_context/application/services/game_session_service.py"),
    ("application/services/inaturalist_service.py", "game_context/application/services/inaturalist_service.py"),
    ("application/dtos/game_dto.py", "game_context/application/dtos/game_dto.py"),

    # Analytics Context
    ("application/services/metrics_service.py", "analytics_context/application/services/metrics_service.py"),
    ("application/dtos/metrics_dto.py", "analytics_context/application/dtos/metrics_dto.py"),

    # Shared
    ("api/dependencies.py", "shared/api/dependencies.py"),
]

# Imports que cambiarán según el contexto
IMPORT_UPDATES = {
    "authentication_context": {
        "from app.domain.entities.user import": "from app.authentication_context.domain.entities import",
        "from app.domain.repositories.user_repository import": "from app.authentication_context.domain.repositories import",
        "from app.application.dtos.user_dto import": "from app.authentication_context.application.dtos import",
        "from app.infrastructure.repositories.user_repository_impl import": "from app.authentication_context.infrastructure.repositories import",
    },
    "game_context": {
        "from app.domain.entities.game_result import": "from app.game_context.domain.entities import",
        "from app.application.dtos.game_dto import": "from app.game_context.application.dtos import",
        "from app.application.services.game_result_service import": "from app.game_context.application.services import",
        "from app.application.services.game_session_service import": "from app.game_context.application.services import",
        "from app.application.services.inaturalist_service import": "from app.game_context.application.services import",
    },
    "analytics_context": {
        "from app.application.dtos.metrics_dto import": "from app.analytics_context.application.dtos import",
        "from app.application.services.metrics_service import": "from app.analytics_context.application.services import",
    },
    "shared": {
        "from app.api.dependencies import": "from app.shared.api.dependencies import",
    },
}

def copy_with_import_updates(src, dst, context):
    """Copia un archivo y actualiza sus imports."""
    print(f"  Moviendo: {src} → {dst}")

    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()

    # Actualizar imports específicos del contexto
    if context in IMPORT_UPDATES:
        for old_import, new_import in IMPORT_UPDATES[context].items():
            content = content.replace(old_import, new_import)

    # Actualizar imports genéricos del dominio a contextos específicos
    if "authentication_context" in dst:
        content = content.replace("from app.domain.entities.user", "from app.authentication_context.domain.entities")
        content = content.replace("from app.domain.repositories.user", "from app.authentication_context.domain.repositories")
    elif "game_context" in dst:
        content = content.replace("from app.domain.entities.game", "from app.game_context.domain.entities")
    elif "analytics_context" in dst:
        pass  # No tiene entidades específicas

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    print("🔄 Iniciando refactoring de contextos...\n")

    for src_rel, dst_rel in MOVES:
        src = BASE / src_rel
        dst = BASE / dst_rel

        if not src.exists():
            print(f"⚠️  No existe: {src}")
            continue

        # Determinar contexto
        if "authentication_context" in dst_rel:
            context = "authentication_context"
        elif "game_context" in dst_rel:
            context = "game_context"
        elif "analytics_context" in dst_rel:
            context = "analytics_context"
        else:
            context = "shared"

        copy_with_import_updates(str(src), str(dst), context)

    print("\n✅ Refactoring completado!")
    print("📌 Próximos pasos:")
    print("  1. Revisar imports en archivos movidos")
    print("  2. Actualizar routes en shared/api/routes/")
    print("  3. Crear tests/")
    print("  4. Eliminar archivos viejos")

if __name__ == "__main__":
    main()
