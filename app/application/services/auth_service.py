import time
import string
import random
from datetime import timedelta
from ulid import ULID
from app.domain.entities.user import User, Role
from app.domain.repositories.user_repository import UserRepository
from app.domain.exceptions.exceptions import EmailAlreadyExistsError, InvalidCredentialsError
from app.infrastructure.security.password import hash_password, verify_password
from app.infrastructure.security.jwt_handler import create_access_token, create_refresh_token, decode_token
from app.application.exceptions.exceptions import AuthenticationError, RateLimitError
from app.application.dtos.user_dto import RegisterUserDTO


class AuthService:

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.login_attempts = {}  # TODO: Usar Redis en prod

    def register(self, dto: RegisterUserDTO) -> dict:
        if len(dto.password) < 8:
            raise ValueError("Contraseña debe tener mínimo 8 caracteres")

        if len(dto.password) > 72:
            raise ValueError("Contraseña no puede tener más de 72 caracteres")

        existing_user = self.user_repository.find_by_email(dto.email)
        if existing_user:
            raise EmailAlreadyExistsError(f"El email {dto.email} ya está registrado")

        user_id = str(ULID())
        now = int(time.time() * 1000)

        new_user = User(
            id=user_id,
            nombre=dto.nombre,
            apellido=dto.apellido,
            email=dto.email,
            password_hash=hash_password(dto.password),
            role=Role.JUGADOR,
            is_active=True,
            createdAt=now,
            updatedAt=now
        )

        saved_user = self.user_repository.save(new_user)

        return {
            "id": saved_user.id,
            "nombre": saved_user.nombre,
            "apellido": saved_user.apellido,
            "email": saved_user.email,
            "role": saved_user.role.value,
            "createdAt": saved_user.createdAt
        }

    def login(self, email: str, password: str) -> dict:
        self._check_rate_limit(email)

        user = self.user_repository.find_by_email(email)

        if not user or not verify_password(password, user.password_hash):
            self._record_failed_attempt(email)
            raise InvalidCredentialsError("Email o contraseña inválidos")

        if not user.is_active:
            raise AuthenticationError("El usuario está inactivo")

        self._clear_failed_attempts(email)

        now = int(time.time() * 1000)
        user.lastLogin = now
        self.user_repository.update(user)

        access_token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role.value})
        refresh_token = create_refresh_token(data={"sub": user.id, "email": user.email})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 900
        }

    def refresh_access_token(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token)

        if not payload or payload.get("type") != "refresh":
            raise AuthenticationError("Token de refresco inválido")

        user_id = payload.get("sub")
        user = self.user_repository.find_by_id(user_id)

        if not user or not user.is_active:
            raise AuthenticationError("Usuario no encontrado o inactivo")

        access_token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role.value})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 900
        }

    def _check_rate_limit(self, email: str):
        if email in self.login_attempts:
            attempts, timestamp = self.login_attempts[email]
            if time.time() - timestamp < 900:  # 15 minutos
                if attempts >= 5:
                    raise RateLimitError("Máximo de intentos de login excedido. Intente más tarde.")

    def _record_failed_attempt(self, email: str):
        if email not in self.login_attempts:
            self.login_attempts[email] = [0, time.time()]

        attempts, timestamp = self.login_attempts[email]
        if time.time() - timestamp < 900:
            self.login_attempts[email] = [attempts + 1, timestamp]
        else:
            self.login_attempts[email] = [1, time.time()]

    def _clear_failed_attempts(self, email: str):
        if email in self.login_attempts:
            del self.login_attempts[email]
