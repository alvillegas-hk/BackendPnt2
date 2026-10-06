import time
import string
import random
from ulid import ULID
from app.authentication_context.domain.entities import User, Role
from app.authentication_context.domain.repositories import UserRepository
from app.infrastructure.security.password import hash_password, verify_password
from app.application.exceptions.exceptions import UserNotFoundError, AuthorizationError
from app.authentication_context.application.dtos import UpdateUserDTO, ChangePasswordDTO, PaginatedUsersDTO


class UserService:

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def get_user_profile(self, user_id: str) -> dict:
        user = self.user_repository.find_by_id(user_id)

        if not user:
            raise UserNotFoundError(f"Usuario {user_id} no encontrado")

        return user.to_dict()

    def get_user_by_id(self, user_id: str, current_user_id: str, current_user_role: str) -> dict:
        user = self.user_repository.find_by_id(user_id)

        if not user:
            raise UserNotFoundError(f"Usuario {user_id} no encontrado")

        if current_user_role == "jugador" and current_user_id != user_id:
            raise AuthorizationError("No tienes permisos para ver este usuario")

        return user.to_dict()

    def list_users(self, page: int, per_page: int, current_user_role: str, role_filter: str = None) -> PaginatedUsersDTO:
        if current_user_role == "jugador":
            raise AuthorizationError("Los jugadores no pueden ver el listado de usuarios")

        users, total = self.user_repository.find_all(page=page, per_page=per_page, role=role_filter, is_active=True)

        pages = (total + per_page - 1) // per_page

        return PaginatedUsersDTO(
            items=[user.to_dict() for user in users],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )

    def change_password(self, user_id: str, dto: ChangePasswordDTO):
        user = self.user_repository.find_by_id(user_id)

        if not user:
            raise UserNotFoundError(f"Usuario {user_id} no encontrado")

        if not verify_password(dto.current_password, user.password_hash):
            raise ValueError("Contraseña actual incorrecta")

        if len(dto.new_password) < 8:
            raise ValueError("La nueva contraseña debe tener mínimo 8 caracteres")

        user.password_hash = hash_password(dto.new_password)
        user.updatedAt = int(time.time() * 1000)

        self.user_repository.update(user)

        return {"message": "Contraseña actualizada exitosamente"}

    def update_user(self, user_id: str, dto: UpdateUserDTO, current_user_role: str):
        if current_user_role != "admin":
            raise AuthorizationError("Solo los administradores pueden actualizar usuarios")

        user = self.user_repository.find_by_id(user_id)

        if not user:
            raise UserNotFoundError(f"Usuario {user_id} no encontrado")

        if dto.nombre:
            user.nombre = dto.nombre
        if dto.apellido:
            user.apellido = dto.apellido
        if dto.role:
            user.role = Role(dto.role)
        if dto.is_active is not None:
            user.is_active = dto.is_active

        user.updatedAt = int(time.time() * 1000)

        updated_user = self.user_repository.update(user)

        return updated_user.to_dict()

    def reset_password(self, user_id: str, current_user_role: str) -> dict:
        if current_user_role != "admin":
            raise AuthorizationError("Solo los administradores pueden resetear contraseñas")

        user = self.user_repository.find_by_id(user_id)

        if not user:
            raise UserNotFoundError(f"Usuario {user_id} no encontrado")

        new_password = self._generate_random_password()
        user.password_hash = hash_password(new_password)
        user.updatedAt = int(time.time() * 1000)

        self.user_repository.update(user)

        return {
            "user_id": user_id,
            "new_password": new_password,
            "message": "Contraseña reseteada. Guarde la nueva contraseña."
        }

    def _generate_random_password(self, length: int = 12) -> str:
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
