from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Juan",
                "apellido": "Pérez",
                "email": "juan@example.com",
                "password": "password123"
            }
        }


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "juan@example.com",
                "password": "password123"
            }
        }


class RefreshTokenRequest(BaseModel):
    refresh_token: str

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str = None
    token_type: str
    expires_in: int

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 900
            }
        }


class RegisterResponse(BaseModel):
    id: str
    nombre: str
    apellido: str
    email: str
    role: str
    createdAt: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "nombre": "Juan",
                "apellido": "Pérez",
                "email": "juan@example.com",
                "role": "jugador",
                "createdAt": 1728207600000
            }
        }
