from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from app.authentication_context.domain.entities import User


class UserRepository(ABC):

    @abstractmethod
    def save(self, user: User) -> User:
        pass

    @abstractmethod
    def find_by_id(self, user_id: str) -> Optional[User]:
        pass

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def find_all(self, page: int = 1, per_page: int = 20, role: Optional[str] = None, is_active: bool = True) -> Tuple[List[User], int]:
        pass

    @abstractmethod
    def update(self, user: User) -> User:
        pass
