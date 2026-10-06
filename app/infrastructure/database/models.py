from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(26), primary_key=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="jugador")
    is_active = Column(Boolean, nullable=False, default=True)
    createdAt = Column(Integer, nullable=False)
    updatedAt = Column(Integer, nullable=False)
    lastLogin = Column(Integer, nullable=True)

    scores = relationship("ScoreModel", back_populates="user", cascade="all, delete-orphan")


class ScoreModel(Base):
    __tablename__ = "scores"

    id = Column(String(26), primary_key=True)
    user_id = Column(String(26), ForeignKey("users.id"), nullable=False, index=True)
    puntos = Column(Integer, nullable=False)
    juego = Column(String(255), nullable=False)
    fecha = Column(Integer, nullable=False)
    createdAt = Column(Integer, nullable=False)

    user = relationship("UserModel", back_populates="scores")
