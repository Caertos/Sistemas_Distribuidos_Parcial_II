# Sistema de Autenticación FHIR

Este documento describe el sistema de autenticación y autorización implementado para la API FHIR.

## Arquitectura del Sistema

### Componentes Principales

1. **Models ORM** (`app/models/orm/auth.py`)
   - `UserORM`: Usuarios del sistema
   - `RoleORM`: Roles de usuario  
   - `PermissionORM`: Permisos granulares
   - `RefreshTokenORM`: Tokens de refresh JWT
   - `APIKeyORM`: Claves API para integraciones

2. **Models Pydantic** (`app/models/pydantic/auth.py`)
   - Esquemas de validación para requests/responses
   - DTOs para operaciones de autenticación

3. **JWT Utilities** (`app/auth/jwt_utils.py`)
   - `JWTManager`: Gestión de tokens JWT
   - `PasswordManager`: Hash y verificación de contraseñas
   - `FHIRScopeManager`: Validación de scopes SMART on FHIR
   - `APIKeyManager`: Gestión de claves API

4. **Middleware** (`app/auth/middleware.py`)
   - Middleware de autenticación para FastAPI
   - Dependencies para inyección de dependencias
   - Validación de roles y permisos

5. **Routes** (`app/routes/auth.py`)
   - Endpoints REST para autenticación
   - Gestión de usuarios y tokens

## Características

### ✅ Autenticación JWT
- Tokens de acceso (30 minutos por defecto)
- Tokens de refresh (7 días por defecto)  
- Revocación de tokens
- Gestión de sesiones

### ✅ Sistema de Roles y Permisos
- **Roles predefinidos:**
  - `admin`: Acceso completo al sistema
  - `practitioner`: Profesional de salud
  - `patient`: Paciente con acceso limitado
  - `viewer`: Solo lectura

- **Permisos granulares:**
  - Por recurso FHIR (Patient, Observation, etc.)
  - Por acción (read, write, delete)
  - Composición flexible

### ✅ API Keys
- Claves para integraciones sistema-a-sistema
- Scopes configurables
- Expiración automática
- Gestión por superusers

### ✅ SMART on FHIR Compliance
- Scopes estándar: `patient/*.read`, `user/Observation.write`
- Validación de permisos por recurso
- Compatible con flujos OAuth2

### ✅ Seguridad
- Hash de contraseñas con bcrypt
- Validación robusta de contraseñas
- Protección contra ataques de fuerza bruta
- Auditoría de intentos de login

## Endpoints Disponibles

### Autenticación
```
POST /auth/register       # Registro de usuario
POST /auth/login          # Inicio de sesión  
POST /auth/refresh        # Renovar token
POST /auth/logout         # Cerrar sesión
```

### Gestión de Usuario
```
GET  /auth/profile        # Ver perfil
PUT  /auth/profile        # Actualizar perfil
POST /auth/change-password # Cambiar contraseña
```

### API Keys (Solo Superusers)
```
GET    /auth/api-keys     # Listar claves
POST   /auth/api-keys     # Crear clave
DELETE /auth/api-keys/{id} # Revocar clave
```

## Configuración

### Variables de Entorno
```bash
SECRET_KEY=your-super-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
API_KEY_EXPIRE_DAYS=365
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_SPECIAL=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_UPPERCASE=true
```

## Setup y Migración

### 1. Ejecutar Migración de Autenticación
```bash
./setup_auth.sh
```

### 2. Usuario Administrador Por Defecto
- **Usuario:** admin
- **Email:** admin@localhost  
- **Contraseña:** admin123

⚠️ **IMPORTANTE:** Cambiar la contraseña en producción

## Uso en Endpoints FHIR

### Middleware Automático
```python
from app.auth import get_current_user, require_roles, require_fhir_scope

# Requerir usuario autenticado
@app.get("/protected")
async def protected_endpoint(user: UserORM = Depends(get_current_user)):
    return {"user_id": user.id}

# Requerir rol específico  
@app.get("/admin-only")
async def admin_endpoint(user: UserORM = Depends(require_roles(["admin"]))):
    return {"message": "Admin access"}

# Requerir scope FHIR
@app.get("/fhir/Patient")
async def get_patients(user: UserORM = Depends(require_fhir_scope("patient/*.read"))):
    return {"patients": []}
```

### Headers de Autenticación
```bash
# JWT Token
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

# API Key
X-API-Key: ak_live_1234567890abcdef...
```

## Integración con Recursos FHIR

### Permisos por Recurso
- `patient.read/write/delete` - Recursos Patient
- `practitioner.read/write/delete` - Recursos Practitioner  
- `observation.read/write/delete` - Recursos Observation
- `encounter.read/write/delete` - Recursos Encounter
- `condition.read/write/delete` - Recursos Condition
- `medicationrequest.read/write/delete` - Recursos MedicationRequest

### Scopes SMART on FHIR
- `patient/*.read` - Leer todos los recursos del paciente
- `patient/*.write` - Escribir todos los recursos del paciente
- `user/Patient.read` - Leer recursos Patient del usuario
- `user/Observation.write` - Escribir recursos Observation

## Testing

### Testear Autenticación
```bash
# Registro
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com", 
    "password": "TestPass123!",
    "full_name": "Test User"
  }'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPass123!"
  }'

# Usar token
curl -X GET http://localhost:8000/auth/profile \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Seguridad y Mejores Prácticas

### ✅ Implementado
- Hash de contraseñas con bcrypt y salt
- Validación robusta de contraseñas  
- Tokens JWT con expiración
- Revocación de tokens de refresh
- Scopes granulares por recurso
- Auditoría de intentos de login
- Protección contra fuerza bruta

### 🔄 Consideraciones Futuras
- Rate limiting por IP
- Autenticación de dos factores (2FA)
- Integración con proveedores OAuth externos
- Rotación automática de secrets
- Logs de auditoría centralizados

## Distribución en Citus

Las tablas de autenticación están optimizadas para Citus:

- **Distribuidas por user_id:** `users`, `user_role_assignments`, `refresh_tokens`, `api_keys`
- **Tablas de referencia:** `user_roles`, `user_permissions`, `role_permission_assignments`

Esto asegura co-localización de datos relacionados y consultas eficientes.

## Troubleshooting

### Error: Invalid Token
- Verificar que el token no haya expirado
- Verificar formato del header Authorization
- Verificar que SECRET_KEY sea consistente

### Error: Insufficient Permissions  
- Verificar roles asignados al usuario
- Verificar permisos del rol
- Verificar scopes requeridos vs. scopes del usuario

### Error: Database Connection
- Verificar que las migraciones se ejecutaron
- Verificar conexión a PostgreSQL/Citus
- Verificar credenciales de base de datos