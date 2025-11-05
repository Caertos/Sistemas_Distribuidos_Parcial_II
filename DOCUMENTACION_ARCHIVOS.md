# 📚 Documentación Técnica de Archivos del ProyectoDOCUMENTACIÓN DE ARCHIVOS — Resumen por fichero

===============================================

**Sistema:** PostgreSQL 16.6 + Citus 12.1 con Alta Disponibilidad  

**Última actualización:** 5 de noviembre de 2025  Objetivo

**Versión:** 2.0--------

Documento que explica, para cada fichero o grupo de ficheros principales del repositorio, el "para qué" (propósito), el "cómo" (qué hace y cuándo se ejecuta), el "por medio de qué" (herramientas/comandos implicados) y el "por qué" (razón del diseño / cuándo es necesario). Está pensado para estudiantes y para quien mantenga el laboratorio.

---

Archivos en la raíz

## 🎯 Objetivo-------------------



Este documento explica el propósito, funcionamiento y diseño de cada archivo del proyecto. Está pensado para estudiantes, mantenedores y cualquiera que necesite entender la arquitectura del sistema.`README.student.md`

- Para qué: Versión muy breve y práctica para que un alumno pueda arrancar el laboratorio rápido.

---- Cómo: Instrucciones paso a paso (Docker Compose mínimo) y verificación rápida.

- Por medio de qué: Markdown; comandos `docker compose`, `bash register_citus.sh`.

## 📂 Estructura General- Por qué: Autoguía para prácticas y para no abrumar a quien solo necesita arrancar y probar queries distribuidas.



````citus-coordinator.session.sql`

.- Para qué: Archivo con una sesión o notas SQL usadas para depuración o reproducción de comandos en el coordinator.

├── 🚀 Scripts Principales- Cómo: Se puede cargar manualmente en psql (ej. `psql -f citus-coordinator.session.sql`) o consultar su contenido.

│   ├── setup_all.sh           # Instalador interactivo unificado- Por medio de qué: `psql` y PostgreSQL.

│   ├── run_tests.sh           # Suite de pruebas automatizadas- Por qué: Mantener un historial de comandos relevantes para el coordinator (registro de pruebas, ajustes manuales).

│   ├── cleanup.sh             # Limpieza de recursos

│   └── register_citus.sh      # Registro de workers (Docker Compose)`docker-compose.yml`

│- Para qué: Orquestar un entorno local con un coordinator y uno o más workers usando Docker Compose.

├── 🐳 Docker Compose- Cómo: Ejecutar `docker compose up -d` para levantar los servicios; contiene configuraciones de arranque para Postgres/Citus.

│   └── docker-compose.yml     # Orquestación local- Por medio de qué: `docker compose` / Docker Engine; define servicios, puertos, volúmenes y comandos de arranque.

│- Por qué: Permite a los estudiantes ejecutar rápidamente un cluster Citus sin Kubernetes; se configura `wal_level=logical` y otros parámetros necesarios para rebalance/drain.

├── ☸️ Kubernetes (k8s/)

│   ├── setup_minikube.sh      # Despliegue Minikube`register_citus.sh`

│   ├── *.yml                  # Manifiestos K8s- Para qué: Script principal de orquestación que registra workers en el coordinator, asegura la base de datos y la extensión, y puede ejecutar rebalance/drain.

│   ├── register_citus_k8s.sh  # Registro workers K8s- Cómo: Ejecutable Bash; se invoca desde el host (o dentro del pod coordinator en Kubernetes). Soporta flags como `--rebalance` y `--drain` y variables como `PK_FIX_LIST` para intentar arreglar tablas sin PK.

│   └── verify_lab.sh          # Verificación automática- Por medio de qué: `psql` (cliente), funciones SQL de Citus: `citus_set_coordinator_host()`, `master_add_node()`, `rebalance_table_shards()`, `citus_drain_node()`, y comandos DDL (`CREATE DATABASE`, `CREATE EXTENSION`, `ALTER TABLE ... ADD PRIMARY KEY`).

│- Por qué: Automatiza pasos repetitivos y maneja errores comunes (coordinator con hostname `localhost`, falta de DB en workers, tablas sin PK que bloquean `citus_drain_node`). Facilita reproducibilidad del laboratorio.

├── 🗄️ PostgreSQL (postgres-citus/)

│   ├── Dockerfile             # Imagen personalizada`setup_all.sh`

│   └── init/                  # Scripts SQL de inicialización- Para qué: Script de conveniencia para ejecutar todo el flujo en una opción elegida (por ejemplo `compose` o `minikube`).

│- Cómo: Ejecutarlo con el argumento `compose` o `minikube` según el entorno deseado; delega a los scripts y manifiestos correspondientes.

└── 📖 Documentación- Por medio de qué: Bash y utilidades del sistema; internamente ejecuta `docker compose` o `kubectl`/`minikube` según el modo.

    ├── README.md              # Guía principal- Por qué: Simplifica la experiencia educativa: un comando para poner en marcha el laboratorio en la configuración elegida.

    └── DOCUMENTACION_ARCHIVOS.md  # Este archivo

```Directorio `k8s/` (manifiestos y scripts Kubernetes)

---------------------------------------------------

---

`k8s/citus-coordinator.yml`

## 🚀 Scripts Principales- Para qué: Manifiesto Kubernetes (StatefulSet + Service) para desplegar el coordinator en Minikube/cluster.

- Cómo: `kubectl apply -f k8s/citus-coordinator.yml` para crear el StatefulSet y Service. Contiene configuración para arrancar Postgres con `-c wal_level=logical`.

### `setup_all.sh` ⭐- Por medio de qué: Kubernetes (kubectl), StatefulSet, PVCs/volumes, headless Service para DNS estable.

- Por qué: En Kubernetes se requiere un nombre estable para el coordinator y almacenamiento persistente; además se necesita la configuración de WAL para la replicación lógica.

**Para qué:**  

Instalador unificado e interactivo del sistema completo. Reemplaza todos los scripts de instalación anteriores.`k8s/citus-worker-statefulset.yml`

- Para qué: StatefulSet para los workers de Citus, con un PVC por réplica.

**Cómo funciona:**- Cómo: `kubectl apply -f k8s/citus-worker-statefulset.yml` para crear los workers; usar headless Service y DNS del StatefulSet para que el coordinator encuentre los workers.

1. Muestra banner de bienvenida- Por medio de qué: Kubernetes StatefulSet, PVCs, headless Services.

2. Presenta menú de selección (Compose/Minikube/Salir)- Por qué: Los workers necesitan nombres/DNS estables (p.ej. `citus-worker-0`) y almacenamiento persistente por réplica para emular un despliegue real.

3. Valida dependencias del sistema

4. Solicita confirmaciones en cada paso crítico`k8s/secret-citus.yml`

5. Ejecuta el despliegue completo- Para qué: Secret con credenciales (por ejemplo password de postgres) usado por los manifiestos.

6. Muestra resumen final con comandos útiles- Cómo: `kubectl apply -f k8s/secret-citus.yml` antes de desplegar pods que lo consumen.

- Por medio de qué: Kubernetes Secret y variables de entorno en los pods.

**Cuándo usarlo:**- Por qué: Evitar componer contraseñas en texto plano en los manifiestos; centralizar credenciales que los pods referencias.

- Primera instalación del sistema

- Reinstalación completa`k8s/register_citus_k8s.sh`

- Cambio entre Docker Compose y Kubernetes- Para qué: Script que registra los workers desde dentro del entorno Kubernetes (ejecuta comandos `psql` dentro del pod coordinator o hace `kubectl exec`).

- Cómo: Ejecutar desde el host con `./k8s/register_citus_k8s.sh --rebalance --drain` una vez que los pods estén listos.

**Modos de uso:**- Por medio de qué: `kubectl exec` + `psql` + funciones SQL de Citus.

```bash- Por qué: Automatizar la parte de registro dentro del cluster y manejar diferencias de hostnames en Kubernetes.

# Interactivo (recomendado)

./setup_all.shNota: `k8s/setup_minikube.sh` ahora invoca `k8s/register_citus_k8s.sh` automáticamente como parte del flujo totalmente automatizado.



# Automático Docker Compose`k8s/setup_minikube.sh`

./setup_all.sh compose- Para qué: Script para validar dependencias (minikube, kubectl) y opcionalmente arrancar Minikube con los recursos apropiados.

- Cómo: Ejecutar `./k8s/setup_minikube.sh` y seguir las instrucciones (puede requerir permisos o confirmar la cantidad de CPU/memoria asignada).

# Automático Minikube- Por medio de qué: `minikube`, `kubectl`, Bash.

./setup_all.sh minikube- Por qué: Facilitar el setup y evitar errores comunes cuando Minikube no tiene recursos suficientes.

```

Adicional (automatización completa):

**Por qué este diseño:**- El script construye o carga la imagen personalizada `local/citus-custom:12.1` desde `postgres-citus/Dockerfile` y la carga en Minikube.

- Evita bucles infinitos (problema anterior con port-forward)- Aplica `k8s/secret-citus.yml` y los manifiestos `citus-coordinator.yml` y `citus-worker-statefulset.yml`.

- Confirmaciones evitan ejecuciones accidentales- Espera a que los pods estén listos, invoca `k8s/register_citus_k8s.sh --rebalance --drain` para registrar workers y ejecutar rebalance/drain.

- Mensajes claros de progreso- Lanza un `kubectl port-forward` en background para exponer el coordinator en `localhost:5432` y ejecuta `k8s/verify_lab.sh` (verificación automática).

- Timeouts en todas las operaciones

- Manejo de errores robustoPor qué este cambio: eliminar pasos manuales del flujo y asegurar que un solo comando ponga el laboratorio en estado reproducible y verificable para estudiantes.



**Tecnologías:**Directorio `postgres-citus/` (imagen y scripts de inicialización)

- Bash scripting con `set -euo pipefail`----------------------------------------------------------------

- Docker Compose / kubectl

- Códigos ANSI para colores`postgres-citus/Dockerfile`

- Funciones modulares- Para qué: Dockerfile (imagen base) que copia scripts de inicialización en la imagen de PostgreSQL/Citus.

- Cómo: Se construye con `docker build -t <tag> postgres-citus/` si se quiere una imagen personalizada.

---- Por medio de qué: Docker, imagen base `citusdata/citus`.

- Por qué: Permitir inicializar el DB con extensiones, esquemas y datos al arrancar el contenedor (útil para reproducir el entorno con un esquema predefinido).

### `run_tests.sh` ⭐ NUEVO

Nota: `k8s/setup_minikube.sh` construye/carga esta imagen etiquetada por defecto como `local/citus-custom:12.1` y los manifiestos Kubernetes han sido actualizados para usarla.

**Para qué:**  

Suite unificada de pruebas automatizadas que reemplaza `test_cluster.sh`, `test_ha.sh` y `test_high_availability.sh`.Nuevo archivo añadido:

`k8s/verify_lab.sh`

**Cómo funciona:**- Para qué: Verificación automática post-despliegue que comprueba la extensión `citus`, nodos activos, shards y ejecuta una prueba distribuida mínima.

1. Presenta menú interactivo con 3 niveles de prueba- Cómo: Invocado automáticamente por `k8s/setup_minikube.sh` al final del despliegue; también puede ejecutarse manualmente.

2. Configura port-forward automáticamente- Por medio de qué: `psql` desde el host contra `localhost:5432` (port-forward) y SQL de prueba.

3. Ejecuta baterías de pruebas según selección- Por qué: Proveer feedback inmediato y automático de que el laboratorio quedó funcional, útil para estudiantes y para integraciones CI.

4. Registra resultados en tiempo real

5. Genera reporte en Markdown con timestampSalida y reporte:

- `k8s/verify_report.json`: el script genera un JSON con la marca de tiempo, estado global (`PASS` o `FAIL`) y una lista de checks con estado y mensajes. El archivo se crea por defecto en `k8s/verify_report.json`.

**Tipos de prueba:**

`postgres-citus/.env.example`

#### 1. Pruebas Básicas (~2 min)- Para qué: Ejemplo de variables de entorno usadas por el Dockerfile o docker-compose.

- ✅ Conectividad con PostgreSQL- Cómo: Copiar a `.env` y ajustar variables (contraseñas, puertos) si se quiere personalizar.

- ✅ Extensión Citus instalada- Por medio de qué: Variables de entorno leídas por `docker compose` o scripts.

- ✅ Workers registrados- Por qué: Evitar hardcodear valores y facilitar la configuración local.

- ✅ Estado de pods en Kubernetes

`postgres-citus/init/01-extensions.sql`

#### 2. Pruebas Completas (~5 min)- Para qué: SQL para crear extensiones necesarias (p.ej. citus, pgcrypto, uuid-ossp si aplica).

- Todas las básicas +- Cómo: Este archivo es copiado por el Dockerfile y ejecutado por la imagen de Postgres al iniciar (si la imagen está configurada para ejecutar scripts en `/docker-entrypoint-initdb.d`).

- ✅ Creación de esquema distribuido- Por medio de qué: PostgreSQL al arrancar el contenedor; `psql` en el proceso de init.

- ✅ Inserción de 1000 pacientes + 3000 observaciones- Por qué: Garantizar que la extensión `citus` esté instalada y disponible en la base de datos al iniciar la instancia.

- ✅ Distribución de shards entre workers

- ✅ Consultas distribuidas (SELECT, JOIN, agregaciones)`postgres-citus/init/02-schema-fhir.sql`

- Para qué: Esquema de ejemplo (en este caso FHIR) usado para poblar la base de datos con tablas de ejemplo.

#### 3. Pruebas con Alta Disponibilidad (~10 min)- Cómo: Igual que el anterior, se ejecuta durante la inicialización del contenedor.

- Todas las completas +- Por medio de qué: SQL estándar ejecutado por el init de Postgres.

- ✅ Eliminación de citus-worker-0- Por qué: Proveer datos y tablas sobre los que practicar operaciones distribuidas.

- ✅ Consultas durante recuperación (10 intentos)

- ✅ Tiempo de recuperaciónArchivos auxiliares y utilidades

- ✅ Integridad de datos post-recuperación-------------------------------

- ✅ Re-registro automático del worker

`register_citus.sh` (ver arriba) — script central de orquestación para Compose y también usable en K8s.

**Modos de uso:**

```bash`.vscode/` (si existe)

# Interactivo- Para qué: Configuración del editor (debug, tareas, ajustes de workspace).

./run_tests.sh- Por qué: Facilita la experiencia de desarrollo (opcional para los estudiantes).



# AutomáticoPautas de uso y recomendaciones

./run_tests.sh basic     # Solo básicas------------------------------

./run_tests.sh complete  # Completas- Para pruebas rápidas en la máquina del alumno, usar `docker compose up -d` y `bash register_citus.sh --rebalance --drain`.

./run_tests.sh all       # Todas (incluyendo HA)- Para entornos más realistas o para prácticas avanzadas, usar Minikube con los manifiestos en `k8s/`.

```- Si algo falla en el rebalance/drain, comprobar que `wal_level=logical` está activo y que las tablas afectadas tienen PRIMARY KEY o REPLICA IDENTITY. El script intenta arreglar PKs listadas en `PK_FIX_LIST`.



**Reportes generados:**Preguntas frecuentes (rápidas)

```------------------------------

RESULTADOS_PRUEBAS_20241105_143052.md- ¿Por qué necesito `wal_level=logical`?  

```  Porque Citus utiliza replicación lógica para mover datos entre nodos cuando se rebalanc ea o se drena un nodo.



Incluye:- ¿Qué hace `citus_set_coordinator_host()`?  

- 📊 Resumen ejecutivo con métricas  Establece el hostname que los workers usarán para comunicarse con el coordinator. Si el coordinator está configurado como `localhost` los workers no podrán conectarse desde otros hosts/containers.

- ✅/❌ Estado de cada prueba

- 📈 Tasa de éxito- ¿Puedo usar este repo sin Docker?  

- 🔍 Outputs completos de comandos SQL  Sí, si tienes PostgreSQL + Citus instalados en máquinas reales; los scripts SQL y las funciones de Citus siguen siendo válidas, pero deberás adaptar los nombres/host/puertos.

- 📝 Logs detallados

**Por qué este diseño:**
- Unifica 3 scripts de prueba anteriores
- Generación automática de documentación
- Reportes timestampeados evitan sobrescritura
- Formato Markdown facilita lectura
- Contadores de pruebas (PASS/FAIL)
- Confirmación antes de prueba destructiva (HA)

**Tecnologías:**
- Bash con funciones modulares
- PostgreSQL client (psql)
- kubectl para Kubernetes
- Archivos temporales para acumulación de resultados
- Códigos de salida apropiados (0/1)

---

### `cleanup.sh`

**Para qué:**  
Limpiar todos los recursos del sistema (Docker Compose y/o Kubernetes).

**Cómo funciona:**
1. Detecta qué servicios están corriendo
2. Detiene containers de Docker Compose
3. Elimina recursos de Kubernetes
4. Mata procesos port-forward
5. Opcionalmente elimina Minikube completo

**Cuándo usarlo:**
- Después de pruebas
- Antes de reinstalación
- Para liberar recursos

**Uso:**
```bash
./cleanup.sh
```

**Por qué:**
- Evita conflictos de recursos
- Limpieza completa garantizada
- Libera puertos (5432)

---

### `register_citus.sh`

**Para qué:**  
Registrar workers en el coordinator cuando se usa Docker Compose.

**Cómo funciona:**
1. Espera a que PostgreSQL esté listo
2. Se conecta al coordinator
3. Ejecuta `citus_add_node()` para cada worker
4. Verifica registro exitoso
5. Opcionalmente ejecuta rebalance

**Cuándo se ejecuta:**
- Automáticamente desde `setup_all.sh compose`
- Manualmente si los workers se desregistran

**Uso:**
```bash
./register_citus.sh
```

**Por qué:**
- En Docker Compose, workers no se auto-registran
- Usa funciones modernas de Citus 12.x (`citus_add_node`)
- Reintentos automáticos para robustez

---

## 🐳 Docker Compose

### `docker-compose.yml`

**Para qué:**  
Definir la orquestación de servicios para despliegue local de desarrollo.

**Servicios definidos:**

#### `citus-coordinator`
```yaml
image: citusdata/citus:12.1
ports: 5432:5432
environment:
  - POSTGRES_USER=postgres
  - POSTGRES_PASSWORD=postgres
  - POSTGRES_DB=hce_distribuida
volumes:
  - ./postgres-citus/init:/docker-entrypoint-initdb.d
```

#### `citus-worker` (x2)
```yaml
replicas: 2
environment:
  - Similar al coordinator
```

**Características:**
- ✅ Redes automáticas
- ✅ Volúmenes para persistencia
- ✅ Scripts de inicialización automática
- ✅ Health checks

**Cuándo usarlo:**
- Desarrollo local rápido
- Pruebas de queries
- Cuando no se necesita HA

**Limitaciones:**
- ❌ Sin recuperación automática
- ❌ Sin StatefulSets
- ❌ Sin PersistentVolumes reales

---

## ☸️ Kubernetes (directorio k8s/)

### `setup_minikube.sh`

**Para qué:**  
Desplegar el sistema completo en Minikube con alta disponibilidad.

**Cómo funciona:**
1. Verifica/inicia Minikube
2. Configura Docker registry de Minikube
3. Construye imagen personalizada
4. Aplica secrets
5. Aplica manifiestos (coordinator + workers)
6. Espera a que pods estén Ready
7. Configura port-forward en background
8. Registra workers automáticamente
9. Ejecuta verificación

**Tiempo estimado:** ~2-3 minutos

**Uso:**
```bash
# Llamado por setup_all.sh minikube
./k8s/setup_minikube.sh
```

**Por qué:**
- Automatización completa
- Verificación de estado en cada paso
- Esperas apropiadas (evita bucles)
- Port-forward no-bloqueante

---

### `citus-coordinator.yml`

**Para qué:**  
Manifest de Kubernetes para el Coordinator.

**Recursos definidos:**

#### Service (Headless)
```yaml
apiVersion: v1
kind: Service
metadata:
  name: citus-coordinator
spec:
  clusterIP: None  # Headless
  ports:
    - port: 5432
```

#### StatefulSet
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: citus-coordinator
spec:
  replicas: 1
  serviceName: citus-coordinator
  template:
    spec:
      containers:
      - name: coordinator
        image: citusdata/citus:12.1
        command: ["docker-entrypoint.sh"]
        args: ["postgres"]
        env:
          - POSTGRES_DB: hce_distribuida
        volumeMounts:
          - name: pgdata
            mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: pgdata
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
```

**Características:**
- ✅ StatefulSet con identidad estable
- ✅ PVC para persistencia
- ✅ Headless service para DNS
- ✅ Init scripts montados

**Por qué StatefulSet:**
- Nombre de pod predecible (citus-coordinator-0)
- Recuperación automática
- Volúmenes persistentes
- Orden de despliegue garantizado

---

### `citus-worker-statefulset.yml`

**Para qué:**  
Manifest de Kubernetes para los Workers.

**Diferencias con coordinator:**
```yaml
spec:
  replicas: 2  # 2 workers por defecto
  serviceName: citus-worker
```

**DNS generado:**
- `citus-worker-0.citus-worker.default.svc.cluster.local`
- `citus-worker-1.citus-worker.default.svc.cluster.local`

**Escalabilidad:**
```bash
# Agregar más workers
kubectl scale statefulset citus-worker --replicas=3

# Luego registrar manualmente:
./k8s/register_citus_k8s.sh
```

**Por qué 2 workers:**
- Mínimo para distribución efectiva
- Balance entre recursos y capacidad
- Pruebas de HA factibles

---

### `secret-citus.yml`

**Para qué:**  
Almacenar credenciales de PostgreSQL de forma "segura" en Kubernetes.

**Contenido (base64):**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: citus-secret
type: Opaque
data:
  postgres-password: cG9zdGdyZXM=  # "postgres"
```

**⚠️ Advertencia:**  
Base64 NO es encriptación. Para producción usar:
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Sealed Secrets

---

### `register_citus_k8s.sh`

**Para qué:**  
Registrar workers en el coordinator en Kubernetes.

**Diferencias con versión Docker Compose:**
- Usa `kubectl exec` en lugar de conexión directa
- Detecta workers automáticamente con `kubectl get pods`
- Usa nombres DNS completos (FQDN)

**Cómo funciona:**
```bash
# Obtiene lista de workers
WORKERS=$(kubectl get pods -l app=citus-worker --no-headers -o custom-columns=":metadata.name")

# Para cada worker
for worker in $WORKERS; do
  kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c \
    "SELECT citus_add_node('${worker}.citus-worker', 5432);"
done
```

**Por qué:**
- Workers se auto-registran tras recreación
- DNS de Kubernetes (service discovery)
- Idempotente (no falla si ya registrado)

---

### `verify_lab.sh`

**Para qué:**  
Verificación automática post-despliegue.

**Verificaciones:**
1. ✅ Todos los pods Running
2. ✅ Extensión Citus instalada
3. ✅ Workers registrados
4. ✅ Shards distribuidos
5. ✅ Queries funcionando

**Salida:**
- JSON con resultado (k8s/verify_report.json)
- Exit code 0/1

**Uso:**
```bash
./k8s/verify_lab.sh
```

**Por qué:**
- Validación automática de instalación
- Detección temprana de problemas
- Formato JSON para CI/CD

---

## 🗄️ PostgreSQL (postgres-citus/)

### `Dockerfile`

**Para qué:**  
Crear imagen personalizada de PostgreSQL + Citus (opcional).

**Contenido:**
```dockerfile
FROM citusdata/citus:12.1

# Scripts de inicialización
COPY init/*.sql /docker-entrypoint-initdb.d/

# Configuración adicional
RUN apt-get update && apt-get install -y postgresql-contrib
```

**Cuándo se usa:**
- Si necesitas extensiones adicionales
- Configuraciones personalizadas
- Scripts de inicialización complejos

**Nota:** Actualmente usamos la imagen oficial `citusdata/citus:12.1` directamente.

---

### `postgres-citus/init/` (Scripts SQL)

Todos los archivos `.sql` en este directorio se ejecutan automáticamente en orden alfabético al crear el container/pod por primera vez.

#### `01-extensions.sql`

**Para qué:**  
Crear extensiones, roles y bases de datos necesarias.

**Qué hace:**
```sql
-- Crear extensión Citus
CREATE EXTENSION IF NOT EXISTS citus;

-- Crear extensión pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Crear roles
CREATE ROLE app_user LOGIN PASSWORD 'app123';

-- Crear base de datos
CREATE DATABASE hce_distribuida OWNER postgres;
```

**Por qué primero:**
- Las extensiones deben crearse antes de usarse
- Los roles deben existir antes de asignar permisos
- La BD debe existir antes de crear esquemas

---

#### `02-schema-fhir.sql`

**Para qué:**  
Crear esquema de Historia Clínica Electrónica basado en estándar FHIR.

**Tablas creadas:**

##### `pacientes`
```sql
CREATE TABLE pacientes (
  documento_id BIGINT NOT NULL,     -- Columna de distribución
  paciente_id BIGINT NOT NULL,
  nombre TEXT,
  apellido TEXT,
  fecha_nacimiento DATE,
  PRIMARY KEY (documento_id, paciente_id)  -- PK compuesta
);

-- Distribuir por documento_id
SELECT create_distributed_table('pacientes', 'documento_id');
```

**⚠️ IMPORTANTE:** La Primary Key DEBE incluir la columna de distribución (`documento_id`) en Citus.

##### Otras tablas:
- `observaciones` (signos vitales, mediciones)
- `medicamentos` (prescripciones)
- `diagnosticos` (condiciones médicas)
- `encuentros` (visitas médicas)

**Todas distribuidas por `documento_id`**

**Por qué este diseño:**
- Cumple con estándar FHIR
- PKs compuestas permiten distribución
- Co-localización de datos relacionados
- Queries eficientes (menos joins entre shards)

---

#### `03-sample-data.sql`

**Para qué:**  
Insertar datos de ejemplo para pruebas.

**Qué inserta:**
```sql
-- 100 pacientes de ejemplo
INSERT INTO pacientes ...

-- 300 observaciones
INSERT INTO observaciones ...

-- Etc.
```

**Cuándo se ejecuta:**
- Solo si existe el archivo
- Automáticamente al crear el container

**Uso:**
- Demos
- Pruebas manuales
- Validación de esquema

---

### `postgres-citus/init/README.md`

**Para qué:**  
Documentar los scripts SQL y su orden de ejecución.

**Contenido:**
- Descripción de cada archivo
- Orden de ejecución
- Dependencias entre scripts
- Ejemplos de uso

---

## 📖 Documentación

### `README.md`

**Para qué:**  
Guía principal del proyecto para usuarios finales.

**Secciones:**
1. 🚀 Introducción y características
2. 🔧 Requisitos previos
3. 📦 Instalación rápida
4. 🧪 Ejecución de pruebas
5. 📚 Comandos útiles
6. 📁 Estructura del proyecto
7. 🔬 Arquitectura
8. 🛠️ Troubleshooting
9. 📊 Métricas y rendimiento

**Público objetivo:**
- Estudiantes de sistemas distribuidos
- Desarrolladores que prueban Citus
- Instructores de laboratorios

**Última actualización:** 5 de noviembre de 2025

---

### `DOCUMENTACION_ARCHIVOS.md` (este archivo)

**Para qué:**  
Documentación técnica detallada de cada archivo del proyecto.

**Público objetivo:**
- Mantenedores del proyecto
- Estudiantes avanzados
- Quienes necesitan modificar el sistema

**Enfoque:**
- **Para qué:** Propósito del archivo
- **Cómo funciona:** Flujo de ejecución
- **Cuándo usarlo:** Casos de uso
- **Por qué:** Decisiones de diseño
- **Tecnologías:** Herramientas usadas

---

## 🔄 Flujos de Trabajo

### Instalación Completa (Docker Compose)

```
1. Usuario ejecuta: ./setup_all.sh
2. Menú muestra opciones
3. Usuario selecciona "1) Docker Compose"
4. Confirmación: ¿Continuar? (y/n)
5. Validación de dependencias (docker, psql)
6. docker compose down -v (limpieza)
7. Confirmación: ¿Levantar servicios? (y/n)
8. docker compose up -d
9. Espera 15s para PostgreSQL
10. Verificación de conectividad (reintentos)
11. Confirmación: ¿Registrar workers? (y/n)
12. Ejecución de register_citus.sh
13. Resumen final con comandos útiles
```

### Instalación Completa (Minikube)

```
1. Usuario ejecuta: ./setup_all.sh
2. Menú muestra opciones
3. Usuario selecciona "2) Minikube"
4. Confirmación: ¿Continuar? (y/n)
5. Validación de dependencias (minikube, kubectl, docker)
6. Si Minikube existe: ¿Eliminar? (y/n)
7. Confirmación: ¿Continuar configuración? (y/n)
8. Ejecución de k8s/setup_minikube.sh
   a. Inicio de Minikube
   b. Build de imagen
   c. Aplicación de secrets
   d. Aplicación de manifiestos
   e. Espera de pods Ready
   f. Port-forward en background
   g. Registro de workers
   h. Verificación automática
9. Resumen final con comandos útiles
```

### Ejecución de Pruebas Completas

```
1. Usuario ejecuta: ./run_tests.sh
2. Verificación de cluster Kubernetes
3. Inicialización de reporte MD
4. Menú de selección (básicas/completas/HA)
5. Usuario selecciona "2) Pruebas completas"
6. Confirmación: ¿Confirmas? (y/n)
7. Setup de port-forward
8. PRUEBA 1: Conectividad
9. PRUEBA 2: Extensión Citus
10. PRUEBA 3: Workers registrados
11. PRUEBA 4: Estado de pods
12. PRUEBA 5: Distribución de datos
    - Creación de esquema
    - Inserción de 1000+ registros
    - Verificación de shards
13. PRUEBA 6: Consultas distribuidas
    - SELECT simple
    - JOIN distribuido
    - Agregaciones
14. Generación de reporte MD
15. Resumen en pantalla
16. Exit code 0 (todas pasaron) o 1 (alguna falló)
```

---

## 🎯 Decisiones de Diseño

### ¿Por qué StatefulSets en lugar de Deployments?

**StatefulSets:**
- ✅ Identidad estable de pods
- ✅ Nombres DNS predecibles
- ✅ Orden de inicio/stop
- ✅ PVCs persistentes por pod
- ✅ Recuperación con mismo nombre

**Deployments:**
- ❌ Nombres aleatorios de pods
- ❌ PVCs compartidos (no apropiado para BD)
- ❌ Sin garantía de orden

**Conclusión:** StatefulSets son la opción correcta para bases de datos.

---

### ¿Por qué script interactivo en lugar de automático?

**Interactivo:**
- ✅ Usuario tiene control
- ✅ Evita ejecuciones accidentales
- ✅ Educativo (muestra cada paso)
- ✅ Menos errores por entornos diferentes

**Automático:**
- ❌ Puede fallar silenciosamente
- ❌ Difícil de depurar
- ❌ No apropiado para laboratorios

**Solución:** Soporte de ambos modos (interactivo por defecto, automático con argumentos).

---

### ¿Por qué generar reportes en Markdown en lugar de JSON/HTML?

**Markdown:**
- ✅ Legible como texto plano
- ✅ Renderizable en GitHub/GitLab
- ✅ Fácil de versionar en Git
- ✅ Convertible a PDF/HTML
- ✅ No requiere visor especial

**JSON:**
- ❌ Menos legible
- ✅ Mejor para automatización

**HTML:**
- ❌ Requiere navegador
- ❌ Más complejo de generar

**Conclusión:** Markdown es el formato ideal para reportes de laboratorio.

---

## 📊 Métricas del Sistema

### Tiempos de Operación

| Operación | Tiempo Estimado |
|-----------|----------------|
| Instalación Docker Compose | ~30 segundos |
| Instalación Minikube | ~2-3 minutos |
| Pruebas básicas | ~2 minutos |
| Pruebas completas | ~5 minutos |
| Pruebas con HA | ~10 minutos |
| Recuperación de pod caído | ~5 segundos |

### Recursos de Sistema

| Componente | CPU | RAM | Disco |
|------------|-----|-----|-------|
| Coordinator | 0.5 core | 1 GB | 10 GB |
| Worker (x2) | 0.5 core | 1 GB | 10 GB |
| **Total Minikube** | 2 cores | 4 GB | 30 GB |

---

## 🔐 Consideraciones de Seguridad

### Desarrollo (actual)
- ⚠️ Passwords en texto plano
- ⚠️ Usuario `postgres` con permisos completos
- ⚠️ Sin SSL/TLS
- ⚠️ Secrets en base64 (no encriptados)

### Producción (recomendado)
- ✅ Secrets Manager (Vault, AWS, Azure)
- ✅ SSL/TLS obligatorio
- ✅ Usuarios con permisos mínimos
- ✅ Network policies de Kubernetes
- ✅ Encriptación en reposo
- ✅ Auditoría de accesos

---

## 🚀 Próximas Mejoras

### Funcionalidades Futuras
- [ ] Monitoring con Prometheus + Grafana
- [ ] Alertas automáticas
- [ ] Backups automáticos a S3
- [ ] Replicación de shards (factor 2+)
- [ ] Soporte para múltiples bases de datos
- [ ] Dashboard web de administración
- [ ] Exportación de reportes a PDF

### Mejoras Técnicas
- [ ] Helm charts para despliegue
- [ ] CI/CD con GitHub Actions
- [ ] Tests unitarios de scripts
- [ ] Integración con Terraform
- [ ] Soporte para AWS EKS / GKE

---

## 📝 Conclusión

Este proyecto demuestra un sistema de base de datos distribuida completo y funcional, con:

✅ Automatización completa de despliegue  
✅ Alta disponibilidad real y verificable  
✅ Suite de pruebas exhaustivas  
✅ Documentación detallada  
✅ Diseño educativo y profesional  

Ideal para laboratorios académicos de sistemas distribuidos y como referencia para proyectos reales con Citus y Kubernetes.

---

**Versión:** 2.0  
**Autor:** Sistema Académico de Sistemas Distribuidos  
**Última revisión:** 5 de noviembre de 2025
