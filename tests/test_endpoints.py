"""
Comprehensive endpoint tests for Birds Game API.
Tests all endpoints to verify functionality after refactoring to bounded contexts.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.shared.infrastructure.database.models import Base
from app.shared.infrastructure.database.database import get_db


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_db():
    """Clean up database before each test"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


# ============================================================================
# AUTH ENDPOINTS TESTS
# ============================================================================

class TestAuthEndpoints:
    """Test authentication endpoints: register, login, refresh"""

    def test_register_success(self):
        """Test successful user registration"""
        response = client.post(
            "/auth/register",
            json={
                "nombre": "Juan",
                "apellido": "Pérez",
                "email": "juan@example.com",
                "password": "SecurePassword123!"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self):
        """Test registration with existing email"""
        # First registration
        client.post(
            "/auth/register",
            json={
                "nombre": "Juan",
                "apellido": "Pérez",
                "email": "duplicate@example.com",
                "password": "SecurePassword123!"
            }
        )

        # Second registration with same email
        response = client.post(
            "/auth/register",
            json={
                "nombre": "Pedro",
                "apellido": "González",
                "email": "duplicate@example.com",
                "password": "SecurePassword123!"
            }
        )
        assert response.status_code == 400
        assert "ya está registrado" in response.json()["detail"]

    def test_register_weak_password(self):
        """Test registration with weak password"""
        response = client.post(
            "/auth/register",
            json={
                "nombre": "Juan",
                "apellido": "Pérez",
                "email": "test@example.com",
                "password": "short"
            }
        )
        assert response.status_code == 400

    def test_login_success(self):
        """Test successful login"""
        # Register user first
        client.post(
            "/auth/register",
            json={
                "nombre": "Juan",
                "apellido": "Pérez",
                "email": "login@example.com",
                "password": "SecurePassword123!"
            }
        )

        # Login
        response = client.post(
            "/auth/login",
            json={
                "email": "login@example.com",
                "password": "SecurePassword123!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword123!"
            }
        )
        assert response.status_code == 401

    def test_refresh_token(self):
        """Test token refresh"""
        # Register and get tokens
        reg_response = client.post(
            "/auth/register",
            json={
                "nombre": "Juan",
                "apellido": "Pérez",
                "email": "refresh@example.com",
                "password": "SecurePassword123!"
            }
        )
        refresh_token = reg_response.json()["refresh_token"]

        # Refresh access token
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


# ============================================================================
# GAME ENDPOINTS TESTS
# ============================================================================

class TestGameEndpoints:
    """Test game session and gameplay endpoints"""

    @pytest.fixture
    def auth_token(self):
        """Get a valid auth token for tests"""
        response = client.post(
            "/auth/register",
            json={
                "nombre": "Player",
                "apellido": "Test",
                "email": "player@example.com",
                "password": "TestPass123!"
            }
        )
        return response.json()["access_token"]

    def test_iniciar_sesion(self, auth_token):
        """Test starting a game session"""
        response = client.post(
            "/api/inaturalist/juego/iniciar",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["mensaje"] == "Sesión iniciada. Comienza a jugar."

    def test_iniciar_sesion_unauthorized(self):
        """Test starting session without authentication"""
        response = client.post("/api/inaturalist/juego/iniciar")
        assert response.status_code == 401

    def test_get_session_stats_no_session(self, auth_token):
        """Test getting stats with no active session"""
        response = client.get(
            "/api/inaturalist/juego/sesion/estadisticas",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404
        assert "No hay una sesión activa" in response.json()["detail"]

    def test_get_session_stats_with_session(self, auth_token):
        """Test getting stats with active session"""
        # Start session
        client.post(
            "/api/inaturalist/juego/iniciar",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # Get stats
        response = client.get(
            "/api/inaturalist/juego/sesion/estadisticas",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "puntos_totales" in data
        assert "total_intentos" in data
        assert "total_aciertos" in data

    def test_terminar_sesion_no_session(self, auth_token):
        """Test ending a session when none is active"""
        response = client.post(
            "/api/inaturalist/juego/terminar",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404

    def test_terminar_sesion_with_session(self, auth_token):
        """Test ending an active session"""
        # Start session
        client.post(
            "/api/inaturalist/juego/iniciar",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # End session
        response = client.post(
            "/api/inaturalist/juego/terminar",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "puntos_totales" in data
        assert data["mensaje"] == "Sesión finalizada. Puntuación guardada."

    def test_get_birds_for_game(self, auth_token):
        """Test getting a game question"""
        response = client.get(
            "/api/inaturalist/juego/aves",
            headers={"Authorization": f"Bearer {auth_token}"},
            params={"place_id": 10434, "locale": "es-AR"}
        )
        # Note: This may fail if iNaturalist API is not available
        # But should return either 200 (success) or 503 (service unavailable)
        assert response.status_code in [200, 503]

    def test_get_ranking_no_auth(self):
        """Test ranking without authentication"""
        response = client.get("/api/inaturalist/juego/ranking")
        assert response.status_code == 401

    def test_get_ranking_with_auth(self, auth_token):
        """Test getting ranking with authentication"""
        response = client.get(
            "/api/inaturalist/juego/ranking",
            headers={"Authorization": f"Bearer {auth_token}"},
            params={"limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_jugadores" in data
        assert "ranking" in data
        assert isinstance(data["ranking"], list)


# ============================================================================
# METRICS ENDPOINTS TESTS
# ============================================================================

class TestMetricsEndpoints:
    """Test metrics and analytics endpoints"""

    @pytest.fixture
    def auth_token(self):
        """Get a valid auth token"""
        response = client.post(
            "/auth/register",
            json={
                "nombre": "Metrics",
                "apellido": "Player",
                "email": "metrics@example.com",
                "password": "TestPass123!"
            }
        )
        return response.json()["access_token"]

    @pytest.fixture
    def admin_token(self):
        """Get an admin token (would need DB setup to create actual admin)"""
        # This is a placeholder - in real tests, you'd seed admin user
        response = client.post(
            "/auth/register",
            json={
                "nombre": "Admin",
                "apellido": "User",
                "email": "admin@example.com",
                "password": "AdminPass123!"
            }
        )
        return response.json()["access_token"]

    def test_get_metricas_usuario_no_auth(self):
        """Test getting user metrics without authentication"""
        response = client.get("/api/inaturalist/metricas/usuario")
        assert response.status_code == 401

    def test_get_metricas_usuario_with_auth(self, auth_token):
        """Test getting user metrics with authentication"""
        response = client.get(
            "/api/inaturalist/metricas/usuario",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_intentos" in data
        assert "total_aciertos" in data
        assert "porcentaje_acierto" in data
        assert "puntuacion_total" in data
        assert "posicion_ranking" in data

    def test_get_metricas_global_no_auth(self):
        """Test getting global metrics without authentication"""
        response = client.get("/api/inaturalist/metricas/global")
        assert response.status_code == 401

    def test_get_metricas_global_user_forbidden(self, auth_token):
        """Test that regular users cannot access global metrics"""
        response = client.get(
            "/api/inaturalist/metricas/global",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # Regular user should get 403 Forbidden
        assert response.status_code == 403
        assert "Acceso denegado" in response.json()["detail"]


# ============================================================================
# USERS ENDPOINTS TESTS
# ============================================================================

class TestUsersEndpoints:
    """Test user management endpoints"""

    @pytest.fixture
    def auth_token(self):
        """Get a valid auth token"""
        response = client.post(
            "/auth/register",
            json={
                "nombre": "User",
                "apellido": "Test",
                "email": "usertest@example.com",
                "password": "TestPass123!"
            }
        )
        return response.json()["access_token"]

    def test_get_profile_no_auth(self):
        """Test getting profile without authentication"""
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_get_profile_with_auth(self, auth_token):
        """Test getting user profile"""
        response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "nombre" in data
        assert "email" in data

    def test_change_password_no_auth(self):
        """Test changing password without authentication"""
        response = client.patch(
            "/users/me/password",
            json={
                "current_password": "OldPass123!",
                "new_password": "NewPass123!"
            }
        )
        assert response.status_code == 401

    def test_change_password_wrong_current(self, auth_token):
        """Test changing password with wrong current password"""
        response = client.patch(
            "/users/me/password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "current_password": "WrongPassword!",
                "new_password": "NewPass123!"
            }
        )
        assert response.status_code == 400


# ============================================================================
# HEALTH ENDPOINT TESTS
# ============================================================================

class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "app" in data
        assert "version" in data

    def test_scalar_docs(self):
        """Test Scalar API docs endpoint"""
        response = client.get("/scalar")
        assert response.status_code == 200


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows"""

    def test_complete_auth_flow(self):
        """Test complete authentication flow"""
        # Register
        reg_response = client.post(
            "/auth/register",
            json={
                "nombre": "Full",
                "apellido": "Flow",
                "email": "flow@example.com",
                "password": "FlowTest123!"
            }
        )
        assert reg_response.status_code == 201
        access_token = reg_response.json()["access_token"]
        refresh_token = reg_response.json()["refresh_token"]

        # Use access token
        profile_response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert profile_response.status_code == 200

        # Refresh token
        refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == 200

    def test_complete_game_flow(self):
        """Test complete game session flow"""
        # Register user
        reg_response = client.post(
            "/auth/register",
            json={
                "nombre": "Game",
                "apellido": "Flow",
                "email": "game@example.com",
                "password": "GameTest123!"
            }
        )
        token = reg_response.json()["access_token"]

        # Start session
        start_response = client.post(
            "/api/inaturalist/juego/iniciar",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert start_response.status_code == 200

        # Get user metrics
        metrics_response = client.get(
            "/api/inaturalist/metricas/usuario",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert metrics_response.status_code == 200

        # End session
        end_response = client.post(
            "/api/inaturalist/juego/terminar",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert end_response.status_code == 200

        # Check ranking
        ranking_response = client.get(
            "/api/inaturalist/juego/ranking",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert ranking_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
