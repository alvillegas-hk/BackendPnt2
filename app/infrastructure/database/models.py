from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

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
    game_results = relationship("GameResultModel", back_populates="user", cascade="all, delete-orphan")
    game_sessions = relationship("GameSessionModel", back_populates="user", cascade="all, delete-orphan")


class ScoreModel(Base):
    __tablename__ = "scores"

    id = Column(String(26), primary_key=True)
    user_id = Column(String(26), ForeignKey("users.id"), nullable=False, index=True)
    puntos = Column(Integer, nullable=False)
    juego = Column(String(255), nullable=False)
    fecha = Column(Integer, nullable=False)
    createdAt = Column(Integer, nullable=False)

    user = relationship("UserModel", back_populates="scores")


class GameResultModel(Base):
    __tablename__ = "game_results"

    id = Column(String(26), primary_key=True)
    user_id = Column(String(26), ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(26), ForeignKey("game_sessions.id"), nullable=True, index=True)
    ave_id = Column(Integer, nullable=False)
    ave_nombre = Column(String(255), nullable=False)
    respuesta_usuario = Column(String(255), nullable=False)
    es_correcta = Column(Boolean, nullable=False)
    puntos_obtenidos = Column(Integer, nullable=False, default=0)
    bonus_racha = Column(Integer, nullable=False, default=0)
    streak_en_respuesta = Column(Integer, nullable=False, default=0)
    createdAt = Column(Integer, nullable=False)

    user = relationship("UserModel", back_populates="game_results")
    session = relationship("GameSessionModel", back_populates="results")


class GameSessionModel(Base):
    __tablename__ = "game_sessions"

    id = Column(String(26), primary_key=True)
    user_id = Column(String(26), ForeignKey("users.id"), nullable=False, index=True)
    puntos_totales = Column(Integer, nullable=False, default=0)
    total_intentos = Column(Integer, nullable=False, default=0)
    total_aciertos = Column(Integer, nullable=False, default=0)
    streak_actual = Column(Integer, nullable=False, default=0)
    streak_maximo = Column(Integer, nullable=False, default=0)
    estado = Column(String(50), nullable=False, default="activa")
    createdAt = Column(Integer, nullable=False)
    terminadaAt = Column(Integer, nullable=True)

    user = relationship("UserModel", back_populates="game_sessions")
    results = relationship("GameResultModel", back_populates="session", cascade="all, delete-orphan")
