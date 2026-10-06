# GameManager Backend

Backend REST API para gestión de usuarios y puntuaciones de un juego.

## 📋 Características

- ✅ Autenticación con JWT (access token + refresh token)
- ✅ Registro e inicio de sesión
- ✅ Gestión de usuarios con roles (jugador, moderador, admin)
- ✅ Cambio de contraseña y reset por admin
- ✅ Listado paginado de usuarios
- ✅ Rate limiting en login/register
- ✅ Soft delete de usuarios
- ✅ Documentación automática con Swagger
- ✅ SQLite para fácil deploy local
- ✅ IDs con ULID
- ✅ Timestamps en milisegundos (LONG)

## 🚀 Setup Rápido

### 1. Clonar y entrar en el proyecto

```bash
cd C:\PNT2
```

### 2. Crear entorno virtual

```bash
python -m venv venv
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` si es necesario (por defecto usa admin/admin123)

### 5. Ejecutar servidor

```bash
python run.py
```

El servidor estará disponible en: **http://localhost:8000**

### 6. Ver documentación interactiva

Abre en el navegador: **http://localhost:8000/docs**

---

## 📚 Estructura del Proyecto

```
C:\PNT2\
├── app/
│   ├── domain/              # Lógica de negocio (DDD)
│   │   ├── entities/        # Usuario, Puntuación
│   │   ├── repositories/    # Interfaces
│   │   └── exceptions/      # Excepciones de dominio
│   ├── application/         # Servicios, casos de uso
│   │   ├── services/        # AuthService, UserService
│   │   ├── dtos/           # Estructuras de datos
│   │   └── exceptions/      # Excepciones de app
│   ├── infrastructure/      # Implementaciones concretas
│   │   ├── database/        # SQLAlchemy, modelos ORM
│   │   ├── repositories/    # Implementación de repos
│   │   ├── security/        # JWT, hashing
│   │   └── config/          # Configuración
│   ├── api/                 # Capa REST
│   │   ├── routes/          # Endpoints
│   │   ├── schemas/         # Pydantic schemas
│   │   └── dependencies.py  # Inyección de dependencias
│   └── main.py              # App FastAPI
├── tests/                   # Tests (unitarios e integración)
├── run.py                   # Script para ejecutar
├── requirements.txt         # Dependencias
├── .env.example            # Variables de entorno (ejemplo)
├── .env                    # Variables de entorno (local)
└── sqlite.db              # Base de datos SQLite
```

---

## 🔐 Autenticación

### Credenciales por defecto

- **Email**: `alfredo.villegas.hk@gmail.com`
- **Usuario**: `admin`
- **Contraseña**: `admin123`

### Flujo de autenticación

1. **Login**: `POST /auth/login` → obtener access_token y refresh_token
2. **Usar token**: Header `Authorization: Bearer <access_token>` en rutas protegidas
3. **Refrescar**: `POST /auth/refresh` con refresh_token si access_token expira

### Tokens

- **Access Token**: Expira en 15 minutos
- **Refresh Token**: Expira en 7 días

---

## 📡 Endpoints Principales

### Autenticación

- `POST /auth/register` - Registrar nuevo usuario
- `POST /auth/login` - Iniciar sesión
- `POST /auth/refresh` - Refrescar access token

### Usuarios

- `GET /users/me` - Perfil del usuario autenticado
- `PATCH /users/me/password` - Cambiar contraseña
- `GET /users` - Listar usuarios (moderadores y admins)
- `GET /users/{user_id}` - Ver usuario específico
- `PATCH /users/{user_id}` - Actualizar usuario (solo admins)
- `POST /users/{user_id}/reset-password` - Resetear contraseña (solo admins)

### Health

- `GET /` - Estado del servidor

Para más detalles, consulta `/docs`

---

## 🧪 Testing

Por implementar (TODO)

---

## 🔒 Seguridad

- ✅ Contraseñas hasheadas con bcrypt
- ✅ JWT con expiración
- ✅ Rate limiting en login/register
- ✅ CORS habilitado
- ✅ Validación de input con Pydantic
- ✅ Soft delete (nunca borrar datos)

---

## 📝 Variables de Entorno

```env
APP_ENV=development
APP_DEBUG=true
SECRET_KEY=tu-secret-key-aqui
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
DATABASE_URL=sqlite:///./sqlite.db
ADMIN_EMAIL=alfredo.villegas.hk@gmail.com
ADMIN_PASSWORD=admin123
LOG_LEVEL=INFO
```

---

## 🚧 TODO

- [ ] Tests unitarios e integración
- [ ] Endpoint de puntuaciones (integración con otro backend)
- [ ] Ranking de jugadores (TODO)
- [ ] Logging más detallado
- [ ] Rate limiting con Redis (en prod)
- [ ] Validaciones adicionales
- [ ] Documentación OpenAPI completa

---

## 📖 Tecnologías

- **FastAPI** - Framework web
- **SQLAlchemy** - ORM
- **SQLite** - Base de datos
- **JWT** - Autenticación
- **Bcrypt** - Hashing de contraseña
- **Pydantic** - Validación de datos
- **ULID** - IDs únicos

---

## 🤝 Contribuir

1. Crea una rama: `git checkout -b feature/my-feature`
2. Commit: `git commit -am 'Add my feature'`
3. Push: `git push origin feature/my-feature`
4. Pull request

---

## 📞 Soporte

Para reportar bugs o sugerencias, crea un issue en el repositorio.
