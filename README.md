# 🚀 Sistema FHIR Distribuido con PostgreSQL + Citus y API FastAPI

Sistema completo de historias clínicas distribuido con **FastAPI**, **PostgreSQL 16.6**, **Citus 12.1** y desplegable en **Docker Compose** y **Kubernetes**. Incluye API REST FHIR R4 completa con autenticación JWT y auditoría.

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación Rápida](#-instalación-rápida)
- [Ejecución de Pruebas](#-ejecución-de-pruebas)
- [Comandos Útiles](#-comandos-útiles)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Documentación Adicional](#-documentación-adicional)

---

## ✨ Características

### 🏥 API FHIR R4 Completa
- ✅ **FastAPI** con endpoints FHIR R4 (Patient, Practitioner, Organization, etc.)
- ✅ **Autenticación JWT** con refresh tokens y API keys
- ✅ **Sistema de auditoría** con logging estructurado
- ✅ **Documentación automática** Swagger/OpenAPI
- ✅ **Validación FHIR** con esquemas Pydantic
- ✅ **Métricas y monitoreo** integrado

### 🗄️ Base de Datos Distribuida
- ✅ **Distribución de datos automática** con Citus (sharding)
- ✅ **Alta disponibilidad** con Kubernetes StatefulSets
- ✅ **Recuperación automática** de nodos caídos
- ✅ **Persistencia de datos** con PersistentVolumes
- ✅ **Esquema FHIR** optimizado para distribución

### 🚀 Despliegue y DevOps
- ✅ **Containerización completa** con Docker multi-stage
- ✅ **Orquestación Kubernetes** con manifiestos completos
- ✅ **Docker Compose** para desarrollo local
- ✅ **Instalador interactivo** asistido paso a paso
- ✅ **Suite de pruebas automatizadas** con generación de reportes

---

## 🔧 Requisitos Previos

### Para Docker Compose (Desarrollo)
```bash
docker --version      # Docker 20.10+
docker compose version # Docker Compose 2.0+
psql --version        # PostgreSQL Client 12+
python3 --version     # Python 3.11+ (para desarrollo local)
```

### Para Kubernetes/Minikube (Producción)
```bash
minikube version      # Minikube 1.25+
kubectl version       # kubectl 1.24+
docker --version      # Docker 20.10+
psql --version        # PostgreSQL Client 12+
```

### Para Desarrollo de la API (Opcional)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r fastapi-app/requirements-dev.txt
```

---

## 🚀 Instalación Rápida

### 1️⃣ Instalación Interactiva (Recomendado)

El instalador te guiará paso a paso:

```bash
./setup_all.sh
```

Selecciona la plataforma:
- **Docker Compose** - Rápido, ideal para desarrollo local
- **Minikube** - Alta disponibilidad, ideal para pruebas de producción

### 2️⃣ Instalación Automática

#### Docker Compose
```bash
./setup_all.sh compose
```

#### Kubernetes/Minikube
```bash
./setup_all.sh minikube
```

### 3️⃣ Verificación Post-Instalación

#### Base de Datos

Conéctate a la base de datos:

```bash
# Port-forward ya estará corriendo si usaste el instalador
psql -h localhost -p 5432 -U postgres -d clinical_records
```

Verifica workers:
```sql
SELECT * FROM citus_get_active_worker_nodes();
```

#### API FastAPI

Accede a la documentación de la API:

```bash
# Con Kubernetes
kubectl port-forward service/fastapi-fhir-service 8080:80 -n fhir-system

# Con Docker Compose
# La API ya estará disponible en puerto 8000
```

Abre en tu navegador:
- **Swagger UI**: http://localhost:8080/docs (K8s) o http://localhost:8000/docs (Compose)
- **ReDoc**: http://localhost:8080/redoc (K8s) o http://localhost:8000/redoc (Compose)
- **Health Check**: http://localhost:8080/health (K8s) o http://localhost:8000/health (Compose)

#### Prueba Rápida de la API

```bash
# Crear un usuario
curl -X POST "http://localhost:8080/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "doctor1",
    "email": "doctor1@hospital.com",
    "password": "SecurePass123!",
    "full_name": "Dr. Juan Pérez",
    "role": "practitioner"
  }'

# Hacer login
curl -X POST "http://localhost:8080/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=doctor1&password=SecurePass123!"
```

---

## 🧪 Ejecución de Pruebas

### Suite Interactiva de Pruebas (Nuevo)

```bash
./run_tests.sh
```

Esto mostrará un menú interactivo con 3 opciones:

1. **Pruebas básicas** (~2 min)
   - Conectividad
   - Extensión Citus
   - Workers registrados
   - Estado de pods

2. **Pruebas completas** (~5 min)
   - Todas las básicas +
   - Distribución de datos (1000 registros)
   - Consultas distribuidas (SELECT, JOIN, agregaciones)

3. **Pruebas con alta disponibilidad** (~10 min)
   - Todas las completas +
   - Simulación de fallo de worker
   - Verificación de recuperación automática
   - Integridad de datos

### Modo Automático de Pruebas

```bash
# Pruebas básicas
./run_tests.sh basic

# Pruebas completas
./run_tests.sh complete

# Todas las pruebas (incluyendo HA)
./run_tests.sh all
```

### 📄 Reportes Generados

Cada ejecución genera un reporte detallado en Markdown:

```
RESULTADOS_PRUEBAS_YYYYMMDD_HHMMSS.md
```

El reporte incluye:
- ✅ Resumen ejecutivo con métricas
- 📊 Resultados detallados de cada prueba
- 📈 Estadísticas del sistema
- 🔍 Logs y outputs completos

---

## 📚 Comandos Útiles

### Gestión del Cluster

#### Ver estado de pods
```bash
kubectl get pods -l 'app in (citus-coordinator,citus-worker)' -o wide
```

#### Ver logs
```bash
# Coordinator
kubectl logs -f citus-coordinator-0

# Workers
kubectl logs -f citus-worker-0
kubectl logs -f citus-worker-1
```

#### Escalar workers
```bash
kubectl scale statefulset citus-worker --replicas=3
```

### Consultas SQL Útiles

```sql
-- Ver versión de Citus
SELECT * FROM citus_version();

-- Ver workers activos
SELECT * FROM citus_get_active_worker_nodes();

-- Ver distribución de shards
SELECT 
  nodename,
  count(*) as shard_count
FROM pg_dist_shard_placement
WHERE shardstate = 1
GROUP BY nodename
ORDER BY nodename;

-- Ver tablas distribuidas
SELECT * FROM citus_tables;

-- Ver estadísticas de una tabla
SELECT * FROM citus_table_size('nombre_tabla');
```

### Limpieza y Mantenimiento

#### Limpiar todo (Docker Compose)
```bash
docker compose down -v
```

#### Limpiar todo (Minikube)
```bash
# Opción 1: Eliminar solo los recursos de Citus
kubectl delete -f k8s/

# Opción 2: Eliminar Minikube completo
minikube delete

# Script de limpieza automático
./cleanup.sh
```

---

## 📁 Estructura del Proyecto

```
.
├── setup_all.sh                    # 🚀 Instalador interactivo unificado
├── run_tests.sh                    # 🧪 Suite de pruebas unificada
├── cleanup.sh                      # 🧹 Script de limpieza
│
├── docker-compose.yml              # 🐳 Configuración Docker Compose (Base)
├── docker-compose.dev.yml         # 🐳 Stack completo con FastAPI
├── register_citus.sh               # 📝 Registro de workers (Compose)
│
├── fastapi-app/                    # 🔥 Aplicación FastAPI
│   ├── Dockerfile                 # Multi-stage container (builder/prod/dev)
│   ├── .dockerignore              # Optimización de build
│   ├── requirements.txt           # Dependencias de producción
│   ├── requirements-dev.txt       # Dependencias de desarrollo
│   ├── main.py                    # Aplicación principal
│   ├── app/                       # Código fuente
│   │   ├── __init__.py
│   │   ├── core/                  # Configuración y seguridad
│   │   │   ├── config.py          # Settings y configuración
│   │   │   ├── security.py        # JWT y autenticación
│   │   │   └── database.py        # Conexión a Citus
│   │   ├── models/                # Modelos Pydantic FHIR
│   │   │   ├── fhir_resources.py  # Recursos FHIR R4
│   │   │   ├── auth.py            # Modelos de autenticación
│   │   │   └── audit.py           # Modelos de auditoría
│   │   ├── api/                   # Endpoints de la API
│   │   │   ├── v1/                # API versión 1
│   │   │   │   ├── auth.py        # Endpoints de autenticación
│   │   │   │   ├── patients.py    # CRUD Pacientes
│   │   │   │   ├── practitioners.py # CRUD Médicos
│   │   │   │   ├── organizations.py # CRUD Organizaciones
│   │   │   │   ├── encounters.py  # CRUD Encuentros
│   │   │   │   ├── observations.py # CRUD Observaciones
│   │   │   │   ├── conditions.py  # CRUD Condiciones
│   │   │   │   ├── medications.py # CRUD Medicamentos
│   │   │   │   └── procedures.py  # CRUD Procedimientos
│   │   │   └── deps.py            # Dependencias comunes
│   │   ├── services/              # Lógica de negocio
│   │   │   ├── fhir_service.py    # Servicios FHIR
│   │   │   ├── auth_service.py    # Servicios de autenticación
│   │   │   └── audit_service.py   # Servicios de auditoría
│   │   └── utils/                 # Utilidades
│   │       ├── fhir_validator.py  # Validador FHIR
│   │       ├── logger.py          # Logger estructurado
│   │       └── exceptions.py      # Excepciones personalizadas
│   └── tests/                     # Tests automatizados
│       ├── test_auth.py           # Tests de autenticación
│       ├── test_fhir_resources.py # Tests de recursos FHIR
│       └── conftest.py            # Configuración de pytest
│
├── k8s/                            # ☸️ Manifiestos Kubernetes
│   ├── setup_minikube.sh          # Instalador Minikube
│   ├── setup_complete_k8s.sh      # Setup completo (Citus + FastAPI)
│   ├── setup_fastapi_k8s.sh       # Setup específico FastAPI
│   ├── fastapi-deployment.yml     # Deployment, Service, ConfigMap FastAPI
│   ├── citus-coordinator.yml      # Coordinator StatefulSet
│   ├── citus-worker-statefulset.yml # Workers StatefulSet
│   ├── secret-citus.yml           # Secrets de Citus
│   ├── register_citus_k8s.sh      # Registro de workers (K8s)
│   └── verify_lab.sh              # Verificación automática
│
├── postgres-citus/                 # 🗄️ Configuración PostgreSQL
│   ├── Dockerfile                 # Imagen personalizada
│   └── init/                      # Scripts de inicialización
│       ├── 01-extensions.sql      # Extensiones y roles
│       ├── 02-schema-fhir.sql     # Esquema FHIR distribuido
│       ├── 03-sample-data.sql     # Datos de ejemplo
│       └── README.md              # Documentación de scripts
│
├── README.md                       # 📖 Este archivo
├── CHECKLIST.md                    # ✅ Lista de verificación del proyecto
├── DOCUMENTACION_ARCHIVOS.md       # 📚 Documentación detallada
└── RESULTADOS_PRUEBAS_*.md         # 📊 Reportes de pruebas generados
```

---

## 🎯 Modos de Despliegue

### 🐳 Docker Compose - Desarrollo

**Ventajas:**
- ✅ Rápido y simple para desarrollo local
- ✅ Stack completo con una sola línea
- ✅ Recarga automática de código (hot reload)
- ✅ Ideal para debugging y desarrollo de features

**Componentes:**
- FastAPI app (puerto 8000)
- Citus coordinator + 2 workers
- Redis para sesiones
- Volúmenes para persistencia

**Uso:**
```bash
# Stack completo
docker compose -f docker-compose.dev.yml up -d

# Solo base de datos
docker compose up -d
```

### ☸️ Kubernetes/Minikube - Producción

**Ventajas:**
- ✅ Alta disponibilidad real
- ✅ Recuperación automática de pods
- ✅ Escalabilidad horizontal con HPA
- ✅ Persistencia de datos con PVCs
- ✅ Service discovery automático
- ✅ Load balancing integrado
- ✅ Rolling updates sin downtime

**Componentes:**
- FastAPI deployment (3 replicas)
- Citus coordinator (StatefulSet)
- 2+ Citus workers (StatefulSet)
- ConfigMaps y Secrets
- Services y LoadBalancers
- HorizontalPodAutoscaler
- NetworkPolicies

**Uso:**
```bash
# Setup completo
./k8s/setup_complete_k8s.sh full

# Solo API
./k8s/setup_fastapi_k8s.sh deploy

# Solo base de datos
./k8s/setup_complete_k8s.sh citus
```

---

## 🔬 Arquitectura del Sistema

### Distribución de Datos

```
┌─────────────────────────────────────────────────────┐
│              Citus Coordinator                       │
│  - Recibe todas las queries                          │
│  - Distribuye queries a workers                      │
│  - Agrega resultados                                 │
└─────────────────────────────────────────────────────┘
                        │
            ┌───────────┴───────────┐
            │                       │
    ┌───────▼─────┐         ┌──────▼──────┐
    │ Worker 0    │         │  Worker 1   │
    │  81 shards  │         │  81 shards  │
    │  PVC 10Gi   │         │  PVC 10Gi   │
    └─────────────┘         └─────────────┘
```

### Alta Disponibilidad

```
1. Pod citus-worker-0 falla
2. StatefulSet detecta el fallo
3. Kubernetes recrea el pod automáticamente
4. Pod se conecta al mismo PVC
5. Datos intactos, servicio restaurado (~5s)
6. Worker se re-registra automáticamente
```

---

## 📊 Rendimiento y Métricas

### Resultados de Pruebas

| Métrica | Valor |
|---------|-------|
| **Tiempo de despliegue** | ~2 minutos |
| **Workers registrados** | 2/2 (100%) |
| **Shards distribuidos** | 162 (81 por worker) |
| **Inserción de datos** | ~333 inserts/seg |
| **Latencia de consultas** | < 100ms |
| **Tiempo de recuperación** | ~5 segundos |
| **Disponibilidad durante fallo** | 100% |
| **Pérdida de datos** | 0% |

---

## 🛠️ Troubleshooting

### Problema: Pods en CrashLoopBackOff

**Solución:**
```bash
kubectl describe pod citus-coordinator-0
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

**Versión:** 3.0  
**Última actualización:** 5 de noviembre de 2025  
**Stack:** FastAPI 0.104.1 + PostgreSQL 16.6 + Citus 12.1 + Kubernetes + Docker
