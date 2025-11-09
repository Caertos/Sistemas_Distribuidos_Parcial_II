# Sistema FHIR Distribuido con PostgreSQL + Citus# 🚀 Sistema FHIR Distribuido con PostgreSQL + Citus y API FastAPI



## 📋 ÍndiceSistema completo de historias clínicas distribuido con **FastAPI**, **PostgreSQL 16.6**, **Citus 12.1** y desplegable en **Docker Compose** y **Kubernetes**. Incluye API REST FHIR R4 completa con autenticación JWT y auditoría.

- [Introducción](#introducción)

- [Arquitectura del Sistema](#arquitectura-del-sistema)---

- [Diagramas](#diagramas)

- [Instalación y Despliegue](#instalación-y-despliegue)## 📋 Tabla de Contenidos

- [Temas Clave de Aprendizaje](#temas-clave-de-aprendizaje)

- [Objetivos Logrados](#objetivos-logrados)- [Características](#-características)

- [Conclusiones](#conclusiones)- [Requisitos Previos](#-requisitos-previos)

- [Comandos Útiles](#comandos-útiles)- [Instalación Rápida](#-instalación-rápida)

- [Ejecución de Pruebas](#-ejecución-de-pruebas)

---- [Comandos Útiles](#-comandos-útiles)

- [Estructura del Proyecto](#-estructura-del-proyecto)

## 🔬 Introducción- [Documentación Adicional](#-documentación-adicional)



Este proyecto académico implementa un **Sistema Distribuido de Historias Clínicas** basado en el estándar **FHIR R4** (Fast Healthcare Interoperability Resources), utilizando **PostgreSQL + Citus** como base de datos distribuida. El sistema demuestra conceptos avanzados de sistemas distribuidos, microservicios, y arquitecturas escalables para el sector salud.---



### Características Principales## ✨ Características



- **📊 Base de Datos Distribuida**: PostgreSQL con extensión Citus para distribución horizontal### 🏥 API FHIR R4 Completa

- **🏥 Estándar FHIR R4**: API REST completa compatible con FHIR para interoperabilidad- ✅ **FastAPI** con endpoints FHIR R4 (Patient, Practitioner, Organization, etc.)

- **🔐 Autenticación JWT**: Sistema de autenticación robusto con roles (Admin, Médico, Paciente, Auditor)- ✅ **Autenticación JWT** con refresh tokens y API keys

- **🌐 Frontend Dinámico**: Aplicación Flask con dashboards especializados por rol- ✅ **Sistema de auditoría** con logging estructurado

- **🐳 Containerización**: Desplegable en Docker Compose y Kubernetes (Minikube)- ✅ **Documentación automática** Swagger/OpenAPI

- **⚡ Alta Performance**: FastAPI asíncrono con SQLAlchemy async- ✅ **Validación FHIR** con esquemas Pydantic

- **📝 Auditoría Completa**: Sistema de logs y auditoría para cumplimiento normativo- ✅ **Métricas y monitoreo** integrado



---### 🗄️ Base de Datos Distribuida

- ✅ **Distribución de datos automática** con Citus (sharding)

## 🏗️ Arquitectura del Sistema- ✅ **Alta disponibilidad** con Kubernetes StatefulSets

- ✅ **Recuperación automática** de nodos caídos

### Componentes Principales- ✅ **Persistencia de datos** con PersistentVolumes

- ✅ **Esquema FHIR** optimizado para distribución

```

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐### 🚀 Despliegue y DevOps

│   Nginx Proxy   │    │  Frontend Flask │    │   FastAPI API   │- ✅ **Containerización completa** con Docker multi-stage

│   (Port 80/443) │◄──►│   (Port 3000)   │◄──►│   (Port 8000)   │- ✅ **Orquestación Kubernetes** con manifiestos completos

└─────────────────┘    └─────────────────┘    └─────────────────┘- ✅ **Docker Compose** para desarrollo local

                                                        │- ✅ **Instalador interactivo** asistido paso a paso

                        ┌─────────────────────────────┐ │- ✅ **Suite de pruebas automatizadas** con generación de reportes

                        │   PostgreSQL + Citus        │ │

                        │   Distributed Database      │◄┘---

                        └─────────────────────────────┘

                                   │## 🔧 Requisitos Previos

                ┌──────────────────┼──────────────────┐

                │                  │                  │### Para Docker Compose (Desarrollo)

          ┌──────────┐      ┌──────────┐      ┌──────────┐```bash

          │  Coord   │      │ Worker 1 │      │ Worker 2 │docker --version      # Docker 20.10+

          │ (5432)   │      │ (5433)   │      │ (5434)   │docker compose version # Docker Compose 2.0+

          └──────────┘      └──────────┘      └──────────┘psql --version        # PostgreSQL Client 12+

```python3 --version     # Python 3.11+ (para desarrollo local)

```

### Stack Tecnológico

### Para Kubernetes/Minikube (Producción)

| Componente | Tecnología | Propósito |```bash

|------------|------------|-----------|minikube version      # Minikube 1.25+

| **Frontend** | Flask 3.0 + Jinja2 | Interfaz web dinámica con autenticación |kubectl version       # kubectl 1.24+

| **Backend API** | FastAPI 0.104 + Pydantic v2 | API REST FHIR R4 de alto rendimiento |docker --version      # Docker 20.10+

| **Base de Datos** | PostgreSQL 15 + Citus 12.1 | Almacenamiento distribuido y escalabilidad horizontal |psql --version        # PostgreSQL Client 12+

| **Proxy** | Nginx 1.24 | Balanceador de carga y proxy reverso |```

| **Autenticación** | JWT + BCrypt | Seguridad y control de acceso |

| **Containerización** | Docker + Docker Compose | Orquestación de servicios |### Para Desarrollo de la API (Opcional)

| **Orquestación K8s** | Minikube + kubectl | Despliegue en Kubernetes |```bash

python3 -m venv venv

---source venv/bin/activate

pip install -r fastapi-app/requirements-dev.txt

## 📊 Diagramas```



### Diagrama de Arquitectura Distribuida---



```mermaid## 🚀 Instalación Rápida

graph TB

    subgraph "Load Balancer"### 1️⃣ Instalación Interactiva (Recomendado)

        NX[Nginx Proxy<br/>Port 80/443]

    endEl instalador te guiará paso a paso:

    

    subgraph "Frontend Layer"```bash

        FL[Flask Frontend<br/>Port 3000<br/>🔐 Authentication<br/>📋 Dashboards]./setup_all.sh

    end```

    

    subgraph "API Layer"Selecciona la plataforma:

        FA[FastAPI Backend<br/>Port 8000<br/>🏥 FHIR R4 API<br/>🔑 JWT Auth]- **Docker Compose** - Rápido, ideal para desarrollo local

    end- **Minikube** - Alta disponibilidad, ideal para pruebas de producción

    

    subgraph "Database Cluster"### 2️⃣ Instalación Automática

        CO[Coordinator<br/>PostgreSQL + Citus<br/>Port 5432<br/>📊 Master Node]

        W1[Worker 1<br/>PostgreSQL + Citus<br/>Port 5433<br/>💾 Data Shard 1]#### Docker Compose

        W2[Worker 2<br/>PostgreSQL + Citus<br/>Port 5434<br/>💾 Data Shard 2]```bash

    end./setup_all.sh compose

    ```

    NX --> FL

    NX --> FA#### Kubernetes/Minikube

    FL --> FA```bash

    FA --> CO./setup_all.sh minikube

    CO --> W1```

    CO --> W2

    ### 3️⃣ Verificación Post-Instalación

    style NX fill:#e1f5fe

    style FL fill:#f3e5f5#### Base de Datos

    style FA fill:#e8f5e8

    style CO fill:#fff3e0Conéctate a la base de datos:

    style W1 fill:#fce4ec

    style W2 fill:#fce4ec```bash

```# Port-forward ya estará corriendo si usaste el instalador

psql -h localhost -p 5432 -U postgres -d clinical_records

### Diagrama de Flujo de Autenticación```



```mermaidVerifica workers:

sequenceDiagram```sql

    participant U as UsuarioSELECT * FROM citus_get_active_worker_nodes();

    participant F as Flask Frontend```

    participant A as FastAPI Backend

    participant D as Base de Datos#### API FastAPI

    

    U->>F: 1. Login (usuario/password)Accede a la documentación de la API:

    F->>A: 2. POST /auth/login

    A->>D: 3. Validar credenciales```bash

    D-->>A: 4. Usuario válido# Con Kubernetes

    A-->>F: 5. JWT Token + Refresh Tokenkubectl port-forward service/fastapi-fhir-service 8080:80 -n fhir-system

    F-->>U: 6. Redirect a Dashboard

    # Con Docker Compose

    Note over U,D: Usuario autenticado# La API ya estará disponible en puerto 8000

    ```

    U->>F: 7. Acceso a Dashboard

    F->>A: 8. GET /dashboard/{role} + JWTAbre en tu navegador:

    A->>A: 9. Validar token y rol- **Swagger UI**: http://localhost:8080/docs (K8s) o http://localhost:8000/docs (Compose)

    A->>D: 10. Obtener datos personalizados- **ReDoc**: http://localhost:8080/redoc (K8s) o http://localhost:8000/redoc (Compose)

    D-->>A: 11. Datos del usuario- **Health Check**: http://localhost:8080/health (K8s) o http://localhost:8000/health (Compose)

    A-->>F: 12. HTML renderizado

    F-->>U: 13. Dashboard personalizado#### Prueba Rápida de la API

```

```bash

### Diagrama de Distribución de Datos# Crear un usuario

curl -X POST "http://localhost:8080/auth/register" \

```mermaid  -H "Content-Type: application/json" \

graph LR  -d '{

    subgraph "Coordinador (Master)"    "username": "doctor1",

        CM[Metadatos<br/>📋 Esquemas<br/>🔍 Query Planner<br/>📊 Estadísticas]    "email": "doctor1@hospital.com",

    end    "password": "SecurePass123!",

        "full_name": "Dr. Juan Pérez",

    subgraph "Worker 1"    "role": "practitioner"

        W1T1[Pacientes<br/>ID: 1,4,7...]  }'

        W1T2[Observaciones<br/>Shard 1]

        W1T3[Condiciones<br/>Shard 1]# Hacer login

    endcurl -X POST "http://localhost:8080/auth/login" \

      -H "Content-Type: application/x-www-form-urlencoded" \

    subgraph "Worker 2"  -d "username=doctor1&password=SecurePass123!"

        W2T1[Pacientes<br/>ID: 2,5,8...]```

        W2T2[Observaciones<br/>Shard 2]

        W2T3[Condiciones<br/>Shard 2]---

    end

    ## 🧪 Ejecución de Pruebas

    CM --> W1T1

    CM --> W1T2### Suite Interactiva de Pruebas (Nuevo)

    CM --> W1T3

    CM --> W2T1```bash

    CM --> W2T2./run_tests.sh

    CM --> W2T3```

    

    style CM fill:#ffecb3Esto mostrará un menú interactivo con 3 opciones:

    style W1T1 fill:#e8f5e8

    style W1T2 fill:#e8f5e81. **Pruebas básicas** (~2 min)

    style W1T3 fill:#e8f5e8   - Conectividad

    style W2T1 fill:#fce4ec   - Extensión Citus

    style W2T2 fill:#fce4ec   - Workers registrados

    style W2T3 fill:#fce4ec   - Estado de pods

```

2. **Pruebas completas** (~5 min)

---   - Todas las básicas +

   - Distribución de datos (1000 registros)

## 🚀 Instalación y Despliegue   - Consultas distribuidas (SELECT, JOIN, agregaciones)



### Prerrequisitos3. **Pruebas con alta disponibilidad** (~10 min)

   - Todas las completas +

- **Docker** 20.10+ y **Docker Compose** 2.0+   - Simulación de fallo de worker

- **Git** para clonar el repositorio   - Verificación de recuperación automática

- **4GB RAM** mínimo recomendado   - Integridad de datos

- **10GB** espacio en disco

### Modo Automático de Pruebas

Para Kubernetes:

- **Minikube** 1.30+```bash

- **kubectl** 1.27+# Pruebas básicas

./run_tests.sh basic

### Instalación Rápida con Docker Compose

# Pruebas completas

```bash./run_tests.sh complete

# 1. Clonar el repositorio

git clone <repository-url># Todas las pruebas (incluyendo HA)

cd Sistemas_Distribuidos_Parcial_II./run_tests.sh all

```

# 2. Ejecutar instalador interactivo

./setup_all.sh### 📄 Reportes Generados



# 3. Seleccionar opción 1 (Docker Compose)Cada ejecución genera un reporte detallado en Markdown:

# El script guiará paso a paso la instalación

``````

RESULTADOS_PRUEBAS_YYYYMMDD_HHMMSS.md

### Instalación con Kubernetes (Minikube)```



```bashEl reporte incluye:

# 1. Clonar el repositorio- ✅ Resumen ejecutivo con métricas

git clone <repository-url>- 📊 Resultados detallados de cada prueba

cd Sistemas_Distribuidos_Parcial_II- 📈 Estadísticas del sistema

- 🔍 Logs y outputs completos

# 2. Ejecutar instalador interactivo

./setup_all.sh---



# 3. Seleccionar opción 2 (Minikube)## 📚 Comandos Útiles

# El script configurará el cluster automáticamente

```### Gestión del Cluster



### Instalación Automática (Sin Interacción)#### Ver estado de pods

```bash

```bashkubectl get pods -l 'app in (citus-coordinator,citus-worker)' -o wide

# Docker Compose```

./setup_all.sh compose

#### Ver logs

# Minikube```bash

./setup_all.sh minikube# Coordinator

```kubectl logs -f citus-coordinator-0



### Verificación Post-Instalación# Workers

kubectl logs -f citus-worker-0

El sistema estará disponible en:kubectl logs -f citus-worker-1

```

- **Frontend Web**: http://localhost (Puerto 80)

- **API FastAPI**: http://localhost:8000#### Escalar workers

- **Documentación API**: http://localhost:8000/docs```bash

- **Base de Datos**: localhost:5432 (usuario: postgres)kubectl scale statefulset citus-worker --replicas=3

```

#### Usuarios de Prueba

### Consultas SQL Útiles

| Usuario | Contraseña | Rol | Descripción |

|---------|------------|-----|-------------|```sql

| `admin` | `admin123` | Administrador | Gestión completa del sistema |-- Ver versión de Citus

| `medico` | `medico123` | Practitioner | Atención médica y registros |SELECT * FROM citus_version();

| `paciente` | `paciente123` | Patient | Consulta de historia clínica |

| `auditor` | `auditor123` | Auditor | Revisión de logs y cumplimiento |-- Ver workers activos

SELECT * FROM citus_get_active_worker_nodes();

---

-- Ver distribución de shards

## 📚 Temas Clave de AprendizajeSELECT 

  nodename,

### 1. Sistemas Distribuidos  count(*) as shard_count

- **Distribución Horizontal**: Particionamiento de datos con CitusFROM pg_dist_shard_placement

- **Consistencia y Disponibilidad**: Implementación de patrones CAPWHERE shardstate = 1

- **Tolerancia a Fallos**: Manejo de errores en arquitecturas distribuidasGROUP BY nodename

- **Escalabilidad**: Técnicas para escalar horizontalmenteORDER BY nodename;



### 2. Bases de Datos Distribuidas-- Ver tablas distribuidas

- **Sharding**: Distribución automática de datos por hashSELECT * FROM citus_tables;

- **Replicación**: Configuración master-worker

- **Query Distribution**: Enrutamiento inteligente de consultas-- Ver estadísticas de una tabla

- **Rebalancing**: Redistribución automática de datosSELECT * FROM citus_table_size('nombre_tabla');

```

### 3. Microservicios y APIs

- **REST API Design**: Implementación de API RESTful con FastAPI### Limpieza y Mantenimiento

- **FHIR Standards**: Cumplimiento con estándares de interoperabilidad

- **API Gateway Pattern**: Nginx como proxy reverso#### Limpiar todo (Docker Compose)

- **Service Discovery**: Comunicación entre servicios```bash

docker compose down -v

### 4. Autenticación y Autorización```

- **JWT Tokens**: Implementación de JSON Web Tokens

- **Role-Based Access Control (RBAC)**: Control de acceso por roles#### Limpiar todo (Minikube)

- **Password Hashing**: Seguridad con BCrypt```bash

- **Session Management**: Gestión de sesiones con Flask# Opción 1: Eliminar solo los recursos de Citus

kubectl delete -f k8s/

### 5. Containerización y Orquestación

- **Docker Multi-Stage Builds**: Optimización de imágenes# Opción 2: Eliminar Minikube completo

- **Docker Compose**: Orquestación de múltiples serviciosminikube delete

- **Kubernetes Deployments**: Despliegue en K8s con StatefulSets

- **Service Mesh**: Comunicación entre pods# Script de limpieza automático

./cleanup.sh

### 6. Observabilidad y Monitoreo```

- **Structured Logging**: Logs estructurados para análisis

- **Health Checks**: Verificación de estado de servicios---

- **Metrics Collection**: Recolección de métricas de rendimiento

- **Audit Trails**: Trazabilidad de operaciones## 📁 Estructura del Proyecto



---```

.

## 🎯 Objetivos Logrados├── setup_all.sh                    # 🚀 Instalador interactivo unificado

├── run_tests.sh                    # 🧪 Suite de pruebas unificada

### ✅ Objetivos Técnicos├── cleanup.sh                      # 🧹 Script de limpieza

- [x] **Sistema Distribuido Funcional**: Cluster PostgreSQL + Citus con 1 coordinador y 2 workers│

- [x] **API FHIR R4 Completa**: 6 recursos FHIR implementados (Patient, Practitioner, Observation, etc.)├── docker-compose.yml              # 🐳 Configuración Docker Compose (Base)

- [x] **Autenticación Robusta**: JWT con roles y permisos granulares├── docker-compose.dev.yml         # 🐳 Stack completo con FastAPI

- [x] **Frontend Dinámico**: Dashboards especializados por rol de usuario├── register_citus.sh               # 📝 Registro de workers (Compose)

- [x] **Containerización Completa**: Despliegue en Docker Compose y Kubernetes│

- [x] **Escalabilidad Horizontal**: Capacidad de agregar workers adicionales├── fastapi-app/                    # 🔥 Aplicación FastAPI

- [x] **Alta Disponibilidad**: Tolerancia a fallos en modo Kubernetes│   ├── Dockerfile                 # Multi-stage container (builder/prod/dev)

│   ├── .dockerignore              # Optimización de build

### ✅ Objetivos Académicos│   ├── requirements.txt           # Dependencias de producción

- [x] **Comprensión de Sistemas Distribuidos**: Implementación práctica de conceptos teóricos│   ├── requirements-dev.txt       # Dependencias de desarrollo

- [x] **Manejo de Consistencia**: Implementación de transacciones distribuidas│   ├── main.py                    # Aplicación principal

- [x] **Patrones de Diseño**: Aplicación de patrones como Gateway, Repository, Observer│   ├── app/                       # Código fuente

- [x] **Mejores Prácticas**: Código limpio, documentación, y estructura modular│   │   ├── __init__.py

- [x] **DevOps**: Automatización de despliegue e integración continua│   │   ├── core/                  # Configuración y seguridad

│   │   │   ├── config.py          # Settings y configuración

### ✅ Objetivos de Negocio│   │   │   ├── security.py        # JWT y autenticación

- [x] **Interoperabilidad**: Cumplimiento con estándares FHIR para intercambio de datos│   │   │   └── database.py        # Conexión a Citus

- [x] **Seguridad**: Implementación de medidas de seguridad para datos médicos│   │   ├── models/                # Modelos Pydantic FHIR

- [x] **Auditabilidad**: Sistema completo de logs para cumplimiento normativo│   │   │   ├── fhir_resources.py  # Recursos FHIR R4

- [x] **Usabilidad**: Interfaces intuitivas para diferentes tipos de usuarios│   │   │   ├── auth.py            # Modelos de autenticación

- [x] **Escalabilidad**: Arquitectura preparada para crecimiento empresarial│   │   │   └── audit.py           # Modelos de auditoría

│   │   ├── api/                   # Endpoints de la API

---│   │   │   ├── v1/                # API versión 1

│   │   │   │   ├── auth.py        # Endpoints de autenticación

## 📈 Conclusiones│   │   │   │   ├── patients.py    # CRUD Pacientes

│   │   │   │   ├── practitioners.py # CRUD Médicos

### Logros Principales│   │   │   │   ├── organizations.py # CRUD Organizaciones

│   │   │   │   ├── encounters.py  # CRUD Encuentros

1. **Implementación Exitosa de Sistema Distribuido**│   │   │   │   ├── observations.py # CRUD Observaciones

   - Se logró implementar un cluster PostgreSQL + Citus completamente funcional│   │   │   │   ├── conditions.py  # CRUD Condiciones

   - Distribución automática de datos con balanceamiento de carga│   │   │   │   ├── medications.py # CRUD Medicamentos

   - Capacidad de escalamiento horizontal demostrada│   │   │   │   └── procedures.py  # CRUD Procedimientos

│   │   │   └── deps.py            # Dependencias comunes

2. **Integración Completa de Tecnologías Modernas**│   │   ├── services/              # Lógica de negocio

   - Stack tecnológico actual y robusto (FastAPI, Flask, PostgreSQL, Docker)│   │   │   ├── fhir_service.py    # Servicios FHIR

   - Implementación de mejores prácticas en desarrollo de APIs│   │   │   ├── auth_service.py    # Servicios de autenticación

   - Containerización completa para portabilidad│   │   │   └── audit_service.py   # Servicios de auditoría

│   │   └── utils/                 # Utilidades

3. **Cumplimiento con Estándares de Salud**│   │       ├── fhir_validator.py  # Validador FHIR

   - API FHIR R4 completamente funcional y testeable│   │       ├── logger.py          # Logger estructurado

   - Manejo seguro de datos médicos con autenticación robusta│   │       └── exceptions.py      # Excepciones personalizadas

   - Sistema de auditoría para cumplimiento normativo│   └── tests/                     # Tests automatizados

│       ├── test_auth.py           # Tests de autenticación

### Aprendizajes Clave│       ├── test_fhir_resources.py # Tests de recursos FHIR

│       └── conftest.py            # Configuración de pytest

1. **Complejidad de Sistemas Distribuidos**│

   - La coordinación entre nodos requiere manejo cuidadoso de la consistencia├── k8s/                            # ☸️ Manifiestos Kubernetes

   - Importancia de health checks y monitoring para detección temprana de fallos│   ├── setup_minikube.sh          # Instalador Minikube

   - Necesidad de automatización para gestión eficiente del cluster│   ├── setup_complete_k8s.sh      # Setup completo (Citus + FastAPI)

│   ├── setup_fastapi_k8s.sh       # Setup específico FastAPI

2. **Importancia de la Arquitectura**│   ├── fastapi-deployment.yml     # Deployment, Service, ConfigMap FastAPI

   - Separación clara de responsabilidades mejora mantenibilidad│   ├── citus-coordinator.yml      # Coordinator StatefulSet

   - Patrones como Gateway y Repository simplifican el desarrollo│   ├── citus-worker-statefulset.yml # Workers StatefulSet

   - Microservicios permiten escalabilidad independiente de componentes│   ├── secret-citus.yml           # Secrets de Citus

│   ├── register_citus_k8s.sh      # Registro de workers (K8s)

3. **Seguridad en Sistemas de Salud**│   └── verify_lab.sh              # Verificación automática

   - Autenticación y autorización son críticas en sistemas médicos│

   - Auditoría completa es esencial para cumplimiento regulatorio├── postgres-citus/                 # 🗄️ Configuración PostgreSQL

   - Encriptación y manejo seguro de tokens es fundamental│   ├── Dockerfile                 # Imagen personalizada

│   └── init/                      # Scripts de inicialización

### Desafíos Superados│       ├── 01-extensions.sql      # Extensiones y roles

│       ├── 02-schema-fhir.sql     # Esquema FHIR distribuido

1. **Configuración de Citus**│       ├── 03-sample-data.sql     # Datos de ejemplo

   - Configuración inicial compleja del cluster distribuido│       └── README.md              # Documentación de scripts

   - Manejo de conectividad entre nodos en diferentes entornos│

   - Optimización de consultas distribuidas├── README.md                       # 📖 Este archivo

├── CHECKLIST.md                    # ✅ Lista de verificación del proyecto

2. **Integración Frontend-Backend**├── DOCUMENTACION_ARCHIVOS.md       # 📚 Documentación detallada

   - Manejo de autenticación entre Flask y FastAPI└── RESULTADOS_PRUEBAS_*.md         # 📊 Reportes de pruebas generados

   - Sincronización de datos en tiempo real```

   - Gestión de sesiones y tokens JWT

---

3. **Containerización Multi-Servicio**

   - Orquestación de múltiples contenedores con dependencias## 🎯 Modos de Despliegue

   - Configuración de redes y volúmenes persistentes

   - Manejo de secretos y variables de entorno### 🐳 Docker Compose - Desarrollo



### Proyecciones Futuras**Ventajas:**

- ✅ Rápido y simple para desarrollo local

1. **Escalabilidad**- ✅ Stack completo con una sola línea

   - Implementación de auto-scaling en Kubernetes- ✅ Recarga automática de código (hot reload)

   - Optimización de queries para mejor rendimiento- ✅ Ideal para debugging y desarrollo de features

   - Implementación de cache distribuido (Redis)

**Componentes:**

2. **Observabilidad**- FastAPI app (puerto 8000)

   - Integración con Prometheus y Grafana- Citus coordinator + 2 workers

   - Implementación de distributed tracing- Redis para sesiones

   - Alerting automático para eventos críticos- Volúmenes para persistencia



3. **Funcionalidades****Uso:**

   - Más recursos FHIR (Medication, Procedure, etc.)```bash

   - Integración con sistemas externos de salud# Stack completo

   - Machine Learning para análisis predictivodocker compose -f docker-compose.dev.yml up -d



### Valor Académico y Profesional# Solo base de datos

docker compose up -d

Este proyecto demuestra la capacidad de:```

- Diseñar e implementar sistemas distribuidos complejos

- Integrar múltiples tecnologías modernas de forma coherente### ☸️ Kubernetes/Minikube - Producción

- Aplicar principios de ingeniería de software en proyectos reales

- Manejar requisitos de seguridad y cumplimiento en sistemas críticos**Ventajas:**

- Documentar y comunicar soluciones técnicas efectivamente- ✅ Alta disponibilidad real

- ✅ Recuperación automática de pods

El conocimiento adquirido es directamente aplicable en entornos profesionales que requieran sistemas distribuidos, microservicios, y arquitecturas cloud-native.- ✅ Escalabilidad horizontal con HPA

- ✅ Persistencia de datos con PVCs

---- ✅ Service discovery automático

- ✅ Load balancing integrado

## 🛠️ Comandos Útiles- ✅ Rolling updates sin downtime



### Docker Compose**Componentes:**

- FastAPI deployment (3 replicas)

```bash- Citus coordinator (StatefulSet)

# Ver estado de contenedores- 2+ Citus workers (StatefulSet)

docker compose ps- ConfigMaps y Secrets

- Services y LoadBalancers

# Ver logs en tiempo real- HorizontalPodAutoscaler

docker compose logs -f- NetworkPolicies



# Conectar a base de datos**Uso:**

psql -h localhost -p 5432 -U postgres -d fhir_db```bash

# Setup completo

# Reiniciar servicios./k8s/setup_complete_k8s.sh full

docker compose restart

# Solo API

# Limpiar sistema./k8s/setup_fastapi_k8s.sh deploy

docker compose down -v

./cleanup.sh# Solo base de datos

```./k8s/setup_complete_k8s.sh citus

```

### Kubernetes (Minikube)

---

```bash

# Ver estado de pods## 🔬 Arquitectura del Sistema

kubectl get pods -l 'app in (citus-coordinator,citus-worker)'

### Distribución de Datos

# Ver logs de coordinador

kubectl logs -f citus-coordinator-0```

┌─────────────────────────────────────────────────────┐

# Ejecutar comando en pod│              Citus Coordinator                       │

kubectl exec -it citus-coordinator-0 -- psql -U postgres -d fhir_db│  - Recibe todas las queries                          │

│  - Distribuye queries a workers                      │

# Port forwarding para acceso local│  - Agrega resultados                                 │

kubectl port-forward svc/citus-coordinator 5432:5432└─────────────────────────────────────────────────────┘

                        │

# Limpiar deployment            ┌───────────┴───────────┐

kubectl delete -f k8s/            │                       │

```    ┌───────▼─────┐         ┌──────▼──────┐

    │ Worker 0    │         │  Worker 1   │

### Pruebas y Validación    │  81 shards  │         │  81 shards  │

    │  PVC 10Gi   │         │  PVC 10Gi   │

```bash    └─────────────┘         └─────────────┘

# Ejecutar tests del cluster```

./run_tests.sh

### Alta Disponibilidad

# Verificar configuración K8s

./k8s/verify_lab.sh```

1. Pod citus-worker-0 falla

# Pruebas de carga (si disponible)2. StatefulSet detecta el fallo

./test_cluster.sh3. Kubernetes recrea el pod automáticamente

```4. Pod se conecta al mismo PVC

5. Datos intactos, servicio restaurado (~5s)

### API Testing6. Worker se re-registra automáticamente

```

```bash

# Health check---

curl http://localhost:8000/health

## 📊 Rendimiento y Métricas

# Documentación interactiva

open http://localhost:8000/docs### Resultados de Pruebas



# Ejemplo de consulta FHIR| Métrica | Valor |

curl -H "Accept: application/json" http://localhost:8000/fhir/R4/Patient|---------|-------|

```| **Tiempo de despliegue** | ~2 minutos |

| **Workers registrados** | 2/2 (100%) |

---| **Shards distribuidos** | 162 (81 por worker) |

| **Inserción de datos** | ~333 inserts/seg |

## 📞 Soporte| **Latencia de consultas** | < 100ms |

| **Tiempo de recuperación** | ~5 segundos |

Para problemas durante la instalación:| **Disponibilidad durante fallo** | 100% |

| **Pérdida de datos** | 0% |

1. Verificar que Docker esté corriendo: `docker --version`

2. Revisar logs: `docker compose logs`---

3. Limpiar y reintentar: `./cleanup.sh && ./setup_all.sh`

4. Verificar puertos disponibles: `netstat -tulpn | grep :5432`## 🛠️ Troubleshooting



---### Problema: Pods en CrashLoopBackOff



**Proyecto Académico - Sistemas Distribuidos**  **Solución:**

*Sistema FHIR Distribuido con PostgreSQL + Citus*  ```bash

Versión 2.0 - 2025kubectl describe pod citus-coordinator-0
kubectl logs citus-coordinator-0
```

Verifica:
- Secrets creados correctamente
- PVC disponibles
- Recursos suficientes en Minikube

### Problema: Workers no se registran

**Solución:**
```bash
# Verifica que los pods estén Running
kubectl get pods

# Ejecuta registro manual
./k8s/register_citus_k8s.sh
```

### Problema: No puedo conectarme con psql

**Solución:**
```bash
# Verifica port-forward
ps aux | grep "port-forward"

# Reinicia port-forward
pkill -f "kubectl.*port-forward"
kubectl port-forward svc/citus-coordinator 5432:5432 &
```

### Problema: Minikube sin recursos

**Solución:**
```bash
# Detén Minikube
minikube stop

# Reinicia con más recursos
minikube start --cpus=4 --memory=8192
```

---

## 📖 Documentación Adicional

- **Documentación Citus:** https://docs.citusdata.com/
- **PostgreSQL Docs:** https://www.postgresql.org/docs/
- **Kubernetes Docs:** https://kubernetes.io/docs/

### Documentos del Proyecto

- `postgres-citus/init/README.md` - Detalles de scripts SQL
- `DOCUMENTACION_ARCHIVOS.md` - Descripción de todos los archivos
- `RESULTADOS_PRUEBAS_*.md` - Reportes de pruebas ejecutadas

---

## 👥 Contribuir

Este proyecto es parte de un laboratorio académico de Sistemas Distribuidos.

---

## 📝 Notas Importantes

### Seguridad

⚠️ **IMPORTANTE**: Este setup usa credenciales de desarrollo (`postgres/postgres`).

**Para producción:**
- Cambia las contraseñas en `k8s/secret-citus.yml`
- Usa gestores de secrets (Vault, AWS Secrets Manager)
- Habilita SSL/TLS
- Configura firewalls y network policies

### Replicación

Por defecto: `citus.shard_replication_factor = 1`

**Para producción**, aumenta la replicación:
```sql
ALTER SYSTEM SET citus.shard_replication_factor = 2;
SELECT pg_reload_conf();
```

### Backups

Configura backups regulares:
```bash
# Backup completo
kubectl exec citus-coordinator-0 -- pg_dumpall -U postgres | gzip > backup_$(date +%Y%m%d).sql.gz

# Restauración
gunzip -c backup_20241105.sql.gz | kubectl exec -i citus-coordinator-0 -- psql -U postgres
```

---

## ✅ Checklist de Verificación

Después de la instalación, verifica:

- [ ] Todos los pods en estado `Running`
- [ ] Workers registrados en Citus
- [ ] Port-forward activo
- [ ] Puedes conectarte con `psql`
- [ ] Las pruebas básicas pasan
- [ ] Los datos se distribuyen correctamente

Ejecuta:
```bash
./run_tests.sh basic
```

---

## 🎓 Resultados de Aprendizaje

Este proyecto demuestra:

1. ✅ **Bases de datos distribuidas** con sharding
2. ✅ **Alta disponibilidad** con Kubernetes
3. ✅ **Persistencia de datos** con PVCs
4. ✅ **Service discovery** con DNS
5. ✅ **Recuperación automática** de fallos
6. ✅ **Escalabilidad horizontal** de workers
7. ✅ **Consultas distribuidas** eficientes
8. ✅ **Automatización** con scripts bash

---

## 🚀 Inicio Rápido (TL;DR)

### Para Desarrollo (Docker Compose)
```bash
# 1. Stack completo
docker compose -f docker-compose.dev.yml up -d

# 2. Acceder a la API
open http://localhost:8000/docs

# 3. Conectar a DB
psql -h localhost -p 5432 -U postgres -d clinical_records
```

### Para Producción (Kubernetes)
```bash
# 1. Instalar todo
./k8s/setup_complete_k8s.sh full

# 2. Probar
./run_tests.sh

# 3. Acceder a la API
kubectl port-forward service/fastapi-fhir-service 8080:80 -n fhir-system
open http://localhost:8080/docs

# 4. Conectar a DB
psql -h localhost -p 5432 -U postgres -d clinical_records

# 5. Limpiar
./cleanup.sh
```

---

## 👥 Autores

- **Carlos Cochero** - Desarrollo e implementación del sistema distribuido
- **Andrés Palacio** - Arquitectura y configuración de infraestructura

---

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

### Licencia MIT

```
MIT License

Copyright (c) 2025 Carlos Cochero, Andrés Palacio

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

**Proyecto Académico - Sistemas Distribuidos**  
*Sistema FHIR Distribuido con PostgreSQL + Citus*  
**Versión:** 3.0  
**Última actualización:** 5 de noviembre de 2025  
**Stack:** FastAPI 0.104.1 + PostgreSQL 16.6 + Citus 12.1 + Kubernetes + Docker  
**Autores:** Carlos Cochero, Andrés Palacio
