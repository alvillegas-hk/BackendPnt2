from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from app.domain.entities.user import User, Role
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.database.models import UserModel


class UserRepositoryImpl(UserRepository):

    def __init__(self, db: Session):
        self.db = db

    def save(self, user: User) -> User:
        db_user = UserModel(
            id=user.id,
            nombre=user.nombre,
            apellido=user.apellido,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role.value,
            is_active=user.is_active,
            createdAt=user.createdAt,
            updatedAt=user.updatedAt,
            lastLogin=user.lastLogin
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return self._map_to_entity(db_user)

    def find_by_id(self, user_id: str) -> Optional[User]:
        db_user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        return self._map_to_entity(db_user) if db_user else None

    def find_by_email(self, email: str) -> Optional[User]:
        db_user = self.db.query(UserModel).filter(UserModel.email == email).first()
        return self._map_to_entity(db_user) if db_user else None

    def find_all(self, page: int = 1, per_page: int = 20, role: Optional[str] = None, is_active: bool = True) -> Tuple[List[User], int]:
        query = self.db.query(UserModel)

        if is_active:
            query = query.filter(UserModel.is_active == True)

        if role:
            query = query.filter(UserModel.role == role)

        total = query.count()

        offset = (page - 1) * per_page
        db_users = query.offset(offset).limit(per_page).all()

        users = [self._map_to_entity(db_user) for db_user in db_users]
        return users, total

    def update(self, user: User) -> User:
        db_user = self.db.query(UserModel).filter(UserModel.id == user.id).first()

        if db_user:
            db_user.nombre = user.nombre
            db_user.apellido = user.apellido
            db_user.email = user.email
            db_user.password_hash = user.password_hash
            db_user.role = user.role.value
            db_user.is_active = user.is_active
            db_user.updatedAt = user.updatedAt
            db_user.lastLogin = user.lastLogin

            self.db.commit()
            self.db.refresh(db_user)
            return self._map_to_entity(db_user)

        return None

    def _map_to_entity(self, db_user: UserModel) -> User:
        if not db_user:
            return None

        return User(
            id=db_user.id,
            nombre=db_user.nombre,
            apellido=db_user.apellido,
            email=db_user.email,
            password_hash=db_user.password_hash,
            role=Role(db_user.role),
            is_active=db_user.is_active,
            createdAt=db_user.createdAt,
            updatedAt=db_user.updatedAt,
            lastLogin=db_user.lastLogin
        )
