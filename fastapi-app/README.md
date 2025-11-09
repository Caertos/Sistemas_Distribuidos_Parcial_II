# 🚀 FastAPI FHIR Clinical Records API

Sistema distribuido de historias clínicas basado en estándar FHIR R4, con PostgreSQL + Citus como backend distribuido.

## 📁 Estructura del Proyecto

```
fastapi-app/
├── app/
│   ├── __init__.py
│   ├── config/          # Configuración de la aplicación
│   ├── models/          # Modelos SQLAlchemy y Pydantic
│   ├── routes/          # Endpoints de la API
│   ├── middleware/      # Middleware personalizado
│   └── utils/           # Utilidades y helpers
├── tests/               # Tests unitarios e integración
├── main.py             # Punto de entrada de la aplicación
├── requirements.txt    # Dependencias Python
├── .env.example       # Variables de entorno de ejemplo
└── README.md          # Esta documentación
```

## 🛠️ Instalación

### 1. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # En Linux/Mac
# o
venv\Scripts\activate     # En Windows
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus configuraciones específicas
```

### 4. Ejecutar la aplicación

```bash
# Desarrollo
python main.py

# O usando uvicorn directamente
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📋 Dependencias Principales

- **FastAPI**: Framework web moderno y rápido
- **SQLAlchemy**: ORM para base de datos
- **Pydantic**: Validación de datos y settings
- **psycopg2**: Driver PostgreSQL
- **uvicorn**: Servidor ASGI
- **fhir.resources**: Soporte para estándar FHIR R4

## 🌐 Endpoints Disponibles

### Básicos
- `GET /` - Información de la API
- `GET /health` - Health check básico
- `GET /docs` - Documentación Swagger UI
- `GET /redoc` - Documentación ReDoc

### API v1 (próximamente)
- `GET /api/v1/patients` - Listar pacientes
- `POST /api/v1/patients` - Crear paciente
- `GET /api/v1/patients/{id}` - Obtener paciente
- `PUT /api/v1/patients/{id}` - Actualizar paciente
- `DELETE /api/v1/patients/{id}` - Eliminar paciente

## 🔧 Configuración

### Variables de Entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `DB_HOST` | Host de PostgreSQL | `localhost` |
| `DB_PORT` | Puerto de PostgreSQL | `5432` |
| `DB_NAME` | Nombre de la base de datos | `clinical_records` |
| `DB_USER` | Usuario de base de datos | `postgres` |
| `DB_PASSWORD` | Contraseña de base de datos | - |
| `SECRET_KEY` | Clave secreta para JWT | - |
| `DEBUG` | Modo debug | `true` |

### Conexión a Citus

La aplicación está configurada para conectarse al clúster Citus distribuido:
- **Coordinator**: Puerto 5432 (consultas y coordinación)
- **Workers**: Puertos 5433, 5434 (almacenamiento distribuido)

## 🧪 Testing

```bash
# Ejecutar todos los tests
pytest

# Con coverage
pytest --cov=app --cov-report=html

# Tests específicos
pytest tests/test_models.py
```

## 📊 Monitoreo

### Health Checks
- `GET /health` - Estado básico de la aplicación
- `GET /health/db` - Estado de conexión a base de datos (próximamente)
- `GET /health/cluster` - Estado del clúster Citus (próximamente)

### Métricas
- `GET /metrics` - Métricas básicas de la aplicación (próximamente)

## 🔒 Seguridad

- Validación automática de datos con Pydantic
- Sanitización de inputs
- CORS configurado
- Preparado para OAuth2/JWT (próxima implementación)

## 🚀 Despliegue

### Docker (próximamente)
```bash
docker build -t fastapi-fhir .
docker run -p 8000:8000 fastapi-fhir
```

### Kubernetes (próximamente)
Manifiestos disponibles en `/k8s/fastapi/`

## 🤝 Contribución

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Add nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 Licencia

Proyecto académico - Sistemas Distribuidos

---

**Estado**: 🚧 En desarrollo  
**Version**: 1.0.0  
**Última actualización**: 8 de noviembre de 2025