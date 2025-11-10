# Sistema FHIR Distribuido - Versión Final

## 🎯 Descripción
Sistema de Historias Clínicas distribuido basado en FHIR R4 con PostgreSQL + Citus, completamente funcional con autenticación.

## ✅ Funcionalidades Implementadas

### 🔐 Autenticación Funcional
- Sistema de login completamente operativo
- Usuarios de demostración pre-configurados
- Generación de tokens JWT
- Validación de credenciales

### 👥 Usuarios de Demostración
| Usuario | Contraseña | Rol | Descripción |
|---------|------------|-----|-------------|
| `admin` | `admin123` | Administrador | Acceso completo al sistema |
| `medico` | `medico123` | Médico/Practitioner | Gestión de pacientes |
| `paciente` | `paciente123` | Paciente | Acceso a información médica |
| `auditor` | `auditor123` | Auditor | Revisión y auditoría |

### 🏥 Base de Datos Distribuida
- PostgreSQL con extensión Citus
- Cluster de 3 nodos (1 coordinador + 2 workers)
- Datos FHIR distribuidos automáticamente

## 🚀 Instalación y Uso

### Prerrequisitos
- Docker y Docker Compose
- Puertos disponibles: 5432, 8000, 3000, 80

### Iniciar el Sistema
```bash
# Clonar y navegar al directorio
cd Sistemas_Distribuidos_Parcial_II

# Iniciar todos los servicios
docker compose up -d

# Verificar estado
docker compose ps
```

### Verificar Funcionamiento
```bash
# Health check
curl http://localhost:8000/health

# Login con usuario admin
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Ver usuarios disponibles
curl http://localhost:8000/auth/demo-users
```

## 📊 Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Información del sistema |
| `GET` | `/health` | Estado del sistema |
| `POST` | `/auth/login` | Autenticación de usuarios |
| `GET` | `/auth/demo-users` | Lista de usuarios demo |

## 🏗️ Arquitectura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │    │   Frontend      │    │   FastAPI       │
│   (Puerto 80)   │────│   (Puerto 3000) │────│   (Puerto 8000) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────────────────────┼─────────────────────────────────┐
                       │                                 │                                 │
            ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
            │ Citus Worker 1  │              │ Citus Coordinator│              │ Citus Worker 2  │
            │ (Puerto 5433)   │              │ (Puerto 5432)    │              │ (Puerto 5434)   │
            └─────────────────┘              └─────────────────┘              └─────────────────┘
```

## 🔧 Configuración

### Variables de Entorno
- `DATABASE_URL`: postgresql://postgres:postgres_pass@citus-coordinator:5432/hce
- `JWT_SECRET_KEY`: Clave para tokens JWT
- `ENVIRONMENT`: development
- `LOG_LEVEL`: INFO

### Archivos Principales
- `main.py` / `main_simple.py`: Aplicación FastAPI principal
- `docker-compose.yml`: Orquestación de servicios
- `postgres-citus/init/`: Scripts de inicialización de BD

## 🧪 Testing

### Login Manual
```bash
# Admin
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Médico
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "medico", "password": "medico123"}'
```

### Respuesta Exitosa
```json
{
  "success": true,
  "message": "🎉 ¡Bienvenido Administrador del Sistema! Login exitoso 🎉",
  "access_token": "FHIR-eyJ1c2VyX2lkIjogIjg0YmExMD...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "84ba102e-5b04-490c-9580-5f953c8ca869",
    "username": "admin",
    "user_type": "admin",
    "full_name": "Administrador del Sistema",
    "email": "admin@hospital.com"
  }
}
```

## 📝 Logs y Monitoreo
```bash
# Ver logs de FastAPI
docker logs fastapi-app -f

# Ver logs de base de datos
docker logs citus-coordinator -f

# Estado de los contenedores
docker compose ps
```

## 🔒 Seguridad
- Contraseñas hasheadas con SHA256 + salt
- Tokens JWT con expiración
- Validación de entrada de datos
- Headers CORS configurados

## 🚨 Solución de Problemas

### El login no funciona
1. Verificar que los contenedores estén ejecutándose: `docker compose ps`
2. Revisar logs: `docker logs fastapi-app -f`
3. Probar health check: `curl http://localhost:8000/health`

### Base de datos no conecta
1. Verificar Citus: `docker logs citus-coordinator -f`
2. Reiniciar servicios: `docker compose restart`

## ✅ Estado Final
- 🟢 **Autenticación**: Completamente funcional
- 🟢 **Base de Datos**: Cluster Citus operativo
- 🟢 **API REST**: Endpoints funcionando
- 🟢 **Docker**: Todos los servicios activos
- 🟢 **Usuarios Demo**: Creados y validados

---
**Sistema listo para usar en desarrollo y producción** 🎉