# PostgreSQL Citus: Base de Datos Distribuida para Historias Clínicas

## ¿Qué es Citus?

Citus es una extensión de PostgreSQL que convierte una base de datos normal en una **base de datos distribuida**. En lugar de tener toda la información en un solo servidor, Citus divide los datos entre múltiples nodos (servidores). En este proyecto, usamos Citus para distribuir las historias clínicas de cada paciente en diferentes servidores, mejorando el rendimiento cuando hay muchos pacientes simultáneamente.

```sql
CREATE EXTENSION IF NOT EXISTS citus;
```

Esta línea (del archivo `01-extensions.sql`) activa la extensión Citus en PostgreSQL, permitiendo que la base de datos funcione en modo distribuido.

## Estructura de Carpetas

### 1. `postgres-citus/` - La Imagen Docker

Esta carpeta contiene todo lo necesario para crear un contenedor Docker de PostgreSQL con Citus preinstalado:

- **Dockerfile**: Define cómo construir la imagen. Comienza desde `citusdata/citus:12.1` (PostgreSQL con Citus ya incluido) y copia scripts SQL:

```dockerfile
FROM citusdata/citus:12.1
COPY init/ /docker-entrypoint-initdb.d/
```

Esto significa: "Toma la imagen oficial de Citus y coloca nuestros scripts SQL en la carpeta especial `/docker-entrypoint-initdb.d/`. Postgres ejecutará automáticamente estos scripts la primera vez que inicie."

- **init/ (carpeta de inicialización)**:
  - `00-create-db.sql`: Crea la base de datos `hce_distribuida` donde vivirán todos los datos de pacientes.
  - `01-extensions.sql`: Activa Citus y crea extensiones adicionales como `pgcrypto` para generar identificadores únicos.
  - `02-schema-fhir.sql`: Define todas las tablas (paciente, medicamento, citas, etc.) siguiendo el estándar FHIR.

### 2. `k8s/1-CitusSql/` - Despliegue en Kubernetes

Aquí se configuran los recursos de Kubernetes para ejecutar Citus en Minikube:

- **citus-namespace.yaml**: Crea un espacio aislado llamado `clinical-database` dentro de Kubernetes para organizar todos los recursos de la base de datos.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: clinical-database
```

- **citus-statefulsets.yaml**: Define dos componentes principales:
  
  1. **Coordinador** (1 réplica): Es el "cerebro" que distribuye consultas SQL a los workers y recibe resultados. Expone el puerto `30007` como NodePort para que accedas desde tu computadora durante pruebas:
  
  ```yaml
  type: NodePort
  ports:
    - port: 5432
      targetPort: 5432
      nodePort: 30007
  ```
  
  2. **Workers** (2 réplicas): Son servidores que almacenan y procesan datos. Trabajan en paralelo para manejar grandes volúmenes de información:
  
  ```yaml
  replicas: 2
  ```

Cada componente tiene almacenamiento persistente (1Gi) para que los datos no se pierdan si el contenedor se reinicia.

## Orquestación y Alta Disponibilidad

Kubernetes incluido en Minikube maneja automáticamente la salud y recuperación de los pods:

### 1. **Detección de Fallos** (Health Checks)

Cada pod tiene dos tipos de verificaciones:

- **Liveness Probe**: Verifica si el contenedor está vivo. Si falla, Kubernetes lo reinicia:

```yaml
livenessProbe:
  exec:
    command: ["pg_isready","-U","postgres","-d","postgres"]
  initialDelaySeconds: 30
  periodSeconds: 10
```

- **Readiness Probe**: Verifica si el pod está listo para recibir tráfico. Si falla, se excluye del balanceo:

```yaml
readinessProbe:
  exec:
    command: ["pg_isready","-U","postgres"]
  initialDelaySeconds: 10
  periodSeconds: 5
```

### 2. **Recuperación Automática** (StatefulSet)

StatefulSet es el controlador de Kubernetes que garantiza:

- **Reinicio automático**: Si un pod muere, StatefulSet lo recrea
- **Persistencia de identidad**: Los pods mantienen nombres y almacenamiento (importante para BD)
- **Orden de despliegue**: Los workers se inician después del coordinador

```yaml
apiVersion: apps/v1
kind: StatefulSet
replicas: 2  # Mantiene siempre 2 workers activos
```

### 3. **Balanceo de Cargas** (Service)

El Service actúa como punto de entrada único:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: citus-worker
spec:
  clusterIP: None  # Headless service: distribuye entre todos los workers
  selector:
    app: citus-worker  # Selecciona solo pods sanos (según readinessProbe)
```

**Cómo funciona:**
1. Si un worker cae, el readinessProbe detecta el fallo
2. Kubernetes lo excluye del Service (no recibe más consultas)
3. StatefulSet reinicia el pod caído
4. Cuando está listo, el readinessProbe lo devuelve al Service

### 4. **Flujo de Recuperación en Tiempo Real**

```
Pod Worker 1: [ACTIVO] ← recibe consultas
Pod Worker 2: [FALLA] → readinessProbe falla
  ↓
Service excluye Worker 2 (tráfico solo a Worker 1)
  ↓
StatefulSet reinicia Worker 2
  ↓
readinessProbe verifica cada 5 segundos
  ↓
Pod Worker 2: [LISTO] ← Service lo devuelve al balanceo
```

## Flujo de Datos

1. Tu aplicación FastAPI conecta al **Coordinador** en `localhost:30007`
2. El Coordinador recibe la consulta SQL (ej: "dame todos los medicamentos del paciente X")
3. Citus divide la consulta y la envía a los **Workers** que contienen esos datos
4. Los Workers procesan y retornan resultados
5. El Coordinador consolida y envía la respuesta a tu aplicación

## Resumen

| Componente | Función |
|-----------|---------|
| `postgres-citus/Dockerfile` | Construye la imagen con PostgreSQL + Citus |
| `postgres-citus/init/` | Scripts SQL que inicializan la BD y tablas |
| `k8s/1-CitusSql/` | Manifiesta Kubernetes para ejecutar Citus en Minikube |
| **StatefulSet** | Mantiene replicas activas, reinicia pods caídos |
| **Service** | Balancear carga entre pods sanos |
| **Liveness Probe** | Detecta pods muertos y los reinicia |
| **Readiness Probe** | Verifica si el pod está listo para recibir tráfico |
