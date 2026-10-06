# Backend Game Manager Skill

## 📋 Visión General

Backend REST API para gestionar usuarios de un juego con autenticación JWT, roles y puntuaciones. Arquitectura DDD con capas de dominio, aplicación e infraestructura.

**Stack**: FastAPI + SQLAlchemy + SQLite + ULID + JWT

---

## 🏗️ Arquitectura DDD

```
proyecto/
├── app/
│   ├── domain/              # Lógica pura, sin dependencias externas
│   │   ├── entities/        # Usuario, Puntuación
│   │   ├── value_objects/   # Role, Email
│   │   ├── repositories/    # Interfaces (contrato)
│   │   └── exceptions/      # Excepciones de dominio
│   │
│   ├── application/         # Casos de uso, orquestación
│   │   ├── services/        # UserService, AuthService, ScoreService
│   │   ├── dtos/           # Request/Response schemas
│   │   └── exceptions/      # Excepciones de aplicación
│   │
│   ├── infrastructure/      # Implementaciones concretas
│   │   ├── repositories/    # UserRepository, ScoreRepository (SQLAlchemy)
│   │   ├── database/        # Configuración SQLAlchemy, modelos ORM
│   │   ├── security/        # JWT, hash de contraseña
│   │   └── config/          # Env vars, settings
│   │
│   ├── api/                 # Capa REST
│   │   ├── routes/          # auth.py, users.py, scores.py
│   │   ├── middleware/      # Auth middleware
│   │   ├── schemas/         # Pydantic schemas
│   │   └── dependencies.py  # Inyección de dependencias
│   │
│   ├── __init__.py
│   └── main.py              # FastAPI app
│
├── tests/
│   ├── integration/
│   └── unit/
│
├── .env.example
├── .env                     # Local (no commitear)
├── requirements.txt
├── sqlite.db               # DB local (no commitear)
├── README.md
└── run.py                  # Script para ejecutar localmente
```

---

## 🔐 Autenticación & Autorización

- **Tokens JWT**:
  - `access_token`: expires en 15 minutos
  - `refresh_token`: expires en 7 días
  - Secret key en `.env`

- **Bearer Token**: Header `Authorization: Bearer <token>`

- **Rate Limiting**: Máximo 5 intentos fallidos en login/register (15 minutos)

- **Rutas protegidas**: Todos excepto `/auth/login` y `/auth/register`

---

## 📊 Modelo de Datos

### Usuario
```
id: ULID (único)
nombre: str (requerido)
apellido: str (requerido)
email: str (unique, requerido)
password_hash: str (hasheada, 8+ caracteres)
role: Enum(jugador, moderador, admin)
is_active: bool (soft delete)
createdAt: int (LONG - milisegundos)
updatedAt: int (LONG - milisegundos)
lastLogin: int (LONG - milisegundos, nullable)
```

### Puntuación (TODO: datos completos desde otro backend)
```
id: ULID
user_id: ULID (FK)
puntos: int
juego: str
fecha: int (LONG - milisegundos)
createdAt: int (LONG)
```

---

## 🔌 Endpoints

### 1. Autenticación

#### POST `/auth/register`
**Público**
```
Request:
{
  "nombre": "string",
  "apellido": "string",
  "email": "string",
  "password": "string"  // 8+ caracteres
}

Response (201):
{
  "id": "ULID",
  "nombre": "string",
  "apellido": "string",
  "email": "string",
  "role": "jugador",
  "createdAt": 1728207600000
}

Errores:
- 400: Email ya existe, contraseña < 8 caracteres, campos faltantes
- 429: Rate limit (5 intentos en 15 min)
```

#### POST `/auth/login`
**Público**
```
Request:
{
  "email": "string",
  "password": "string"
}

Response (200):
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 900  // segundos
}

Errores:
- 401: Credenciales inválidas
- 429: Rate limit
```

#### POST `/auth/refresh`
**Protegido** - Usa refresh token
```
Request:
{
  "refresh_token": "string"
}

Response (200):
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 900
}

Errores:
- 401: Token inválido o expirado
```

---

### 2. Usuarios

#### GET `/users/me`
**Protegido** - Devuelve datos del usuario autenticado
```
Response (200):
{
  "id": "ULID",
  "nombre": "string",
  "apellido": "string",
  "email": "string",
  "role": "jugador|moderador|admin",
  "createdAt": 1728207600000,
  "updatedAt": 1728207600000,
  "lastLogin": 1728207600000
}

Errores:
- 401: No autenticado
```

#### PATCH `/users/me/password`
**Protegido** - Solo cambiar contraseña del usuario
```
Request:
{
  "current_password": "string",
  "new_password": "string"  // 8+ caracteres
}

Response (200):
{
  "message": "Contraseña actualizada exitosamente"
}

Errores:
- 400: Contraseña actual incorrecta, nueva < 8 caracteres
- 401: No autenticado
```

#### GET `/users`
**Protegido** - Listar usuarios (solo moderadores y admins ven todos)
```
Query params:
- page: int (default: 1)
- per_page: int (default: 20, máximo: 100)
- role: jugador|moderador|admin (optional, solo admins)
- is_active: boolean (optional, soft delete)

Response (200):
{
  "items": [
    {
      "id": "ULID",
      "nombre": "string",
      "apellido": "string",
      "email": "string",
      "role": "string",
      "is_active": true,
      "createdAt": 1728207600000,
      "lastLogin": 1728207600000
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}

Autorización:
- Jugadores: 403 (Forbidden)
- Moderadores: ven todos
- Admins: ven todos

Errores:
- 401: No autenticado
- 403: Sin permiso
```

#### GET `/users/{user_id}`
**Protegido** - Ver datos de un usuario específico
```
Response (200):
{
  "id": "ULID",
  "nombre": "string",
  "apellido": "string",
  "email": "string",
  "role": "string",
  "createdAt": 1728207600000,
  "updatedAt": 1728207600000,
  "lastLogin": 1728207600000
}

Autorización:
- Jugadores: 403 (solo su propio perfil)
- Moderadores y Admins: acceso total

Errores:
- 401: No autenticado
- 403: Sin permiso
- 404: Usuario no encontrado
```

#### PATCH `/users/{user_id}`
**Protegido - Solo Admins** - Editar datos de usuario
```
Request:
{
  "nombre": "string",  // opcional
  "apellido": "string",  // opcional
  "role": "jugador|moderador|admin",  // opcional
  "is_active": boolean  // opcional (soft delete)
}

Response (200):
{
  "id": "ULID",
  "nombre": "string",
  "apellido": "string",
  "email": "string",
  "role": "string",
  "is_active": true,
  "updatedAt": 1728207600000
}

Errores:
- 400: Datos inválidos
- 401: No autenticado
- 403: No es admin
- 404: Usuario no encontrado
```

#### POST `/users/{user_id}/reset-password`
**Protegido - Solo Admins** - Resetear contraseña de usuario
```
Response (200):
{
  "user_id": "ULID",
  "new_password": "string",  // Nueva contraseña generada, mostrar UNA SOLA VEZ
  "message": "Contraseña reseteada. Guarde la nueva contraseña."
}

Errores:
- 401: No autenticado
- 403: No es admin
- 404: Usuario no encontrado
```

---

### 3. Puntuaciones (TODO)

#### GET `/scores/me`
**Protegido** - Historial de puntuaciones del usuario
```
Query params:
- page: int (default: 1)
- per_page: int (default: 20)

Response (200):
{
  "items": [
    {
      "id": "ULID",
      "puntos": 100,
      "juego": "string",
      "fecha": 1728207600000,
      "createdAt": 1728207600000
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

---

## 🔑 Configuración .env

```env
# App
APP_ENV=development
APP_DEBUG=true
APP_NAME=GameManager
APP_VERSION=1.0.0

# Security
SECRET_KEY=tu-super-secret-key-cambiar-en-prod
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=sqlite:///./sqlite.db

# Admin seed
ADMIN_EMAIL=alfredo.villegas.hk@gmail.com
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# Logging
LOG_LEVEL=INFO
```

---

## 🚀 Setup & Ejecución

### 1. Crear el proyecto
```bash
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Copiar .env
```bash
cp .env.example .env
```

### 3. Inicializar DB (automático en primer run)
```bash
python run.py
```

### 4. Probar en Postman
- Base URL: `http://localhost:8000`
- Register: `POST /auth/register`
- Login: `POST /auth/login`
- Ver endpoints en `/docs` (Swagger)

---

## 🧪 Testing

- **Unitarios**: Servicios de dominio sin DB
- **Integración**: Endpoints con DB en memory (opcional)
- Ejecutar: `pytest`

---

## 🔒 Consideraciones de Seguridad

1. ✅ Contraseñas hasheadas con bcrypt
2. ✅ JWT con expiración
3. ✅ Rate limiting en login/register
4. ✅ Validación de input con Pydantic
5. ✅ CORS (si frontend separado)
6. ✅ Soft delete (nunca borrar datos)
7. ✅ Logs de acciones sensibles
8. ✅ Email único
9. ✅ Autenticación en todas las rutas protegidas
10. ✅ Autorización por rol

---

## 📝 Notas Importantes

- **ULID**: IDs únicos, sortables. Librería `python-ulid`
- **LONG (milisegundos)**: Usar `int(time.time() * 1000)` en Python
- **Soft delete**: Campo `is_active: bool`, nunca DELETE
- **Swagger**: Automático en `/docs` con FastAPI
- **Sin Docker**: Código limpio para ejecutar en cualquier máquina
- **Seed automático**: Usuario admin creado en primer run si no existe
- **Rate limiting**: Implementar con decorador o middleware
- **Logs**: Usar `logging` estándar de Python, nivel INFO/ERROR

---

## ✅ Checklist Implementación

- [ ] Estructura de carpetas
- [ ] Configuración FastAPI + SQLAlchemy
- [ ] Modelos ORM (Usuario, Puntuación)
- [ ] Entities y Value Objects (Dominio)
- [ ] Repositories (interfaces)
- [ ] Services (lógica)
- [ ] Security (JWT, bcrypt)
- [ ] Auth routes (register, login, refresh)
- [ ] User routes (CRUD, me, password)
- [ ] Score routes (TODO)
- [ ] Middleware de autenticación
- [ ] Rate limiting
- [ ] Seed de BD
- [ ] Validaciones Pydantic
- [ ] Error handling global
- [ ] Logging
- [ ] .env.example
- [ ] README
- [ ] Documentación Swagger
