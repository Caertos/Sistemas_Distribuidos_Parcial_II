DOCUMENTACIÓN DE ARCHIVOS — Resumen por fichero
===============================================

Objetivo
--------
Documento que explica, para cada fichero o grupo de ficheros principales del repositorio, el "para qué" (propósito), el "cómo" (qué hace y cuándo se ejecuta), el "por medio de qué" (herramientas/comandos implicados) y el "por qué" (razón del diseño / cuándo es necesario). Está pensado para estudiantes y para quien mantenga el laboratorio.

Archivos en la raíz
-------------------

`README.student.md`
- Para qué: Versión muy breve y práctica para que un alumno pueda arrancar el laboratorio rápido.
- Cómo: Instrucciones paso a paso (Docker Compose mínimo) y verificación rápida.
- Por medio de qué: Markdown; comandos `docker compose`, `bash register_citus.sh`.
- Por qué: Autoguía para prácticas y para no abrumar a quien solo necesita arrancar y probar queries distribuidas.

`citus-coordinator.session.sql`
- Para qué: Archivo con una sesión o notas SQL usadas para depuración o reproducción de comandos en el coordinator.
- Cómo: Se puede cargar manualmente en psql (ej. `psql -f citus-coordinator.session.sql`) o consultar su contenido.
- Por medio de qué: `psql` y PostgreSQL.
- Por qué: Mantener un historial de comandos relevantes para el coordinator (registro de pruebas, ajustes manuales).

`docker-compose.yml`
- Para qué: Orquestar un entorno local con un coordinator y uno o más workers usando Docker Compose.
- Cómo: Ejecutar `docker compose up -d` para levantar los servicios; contiene configuraciones de arranque para Postgres/Citus.
- Por medio de qué: `docker compose` / Docker Engine; define servicios, puertos, volúmenes y comandos de arranque.
- Por qué: Permite a los estudiantes ejecutar rápidamente un cluster Citus sin Kubernetes; se configura `wal_level=logical` y otros parámetros necesarios para rebalance/drain.

`register_citus.sh`
- Para qué: Script principal de orquestación que registra workers en el coordinator, asegura la base de datos y la extensión, y puede ejecutar rebalance/drain.
- Cómo: Ejecutable Bash; se invoca desde el host (o dentro del pod coordinator en Kubernetes). Soporta flags como `--rebalance` y `--drain` y variables como `PK_FIX_LIST` para intentar arreglar tablas sin PK.
- Por medio de qué: `psql` (cliente), funciones SQL de Citus: `citus_set_coordinator_host()`, `master_add_node()`, `rebalance_table_shards()`, `citus_drain_node()`, y comandos DDL (`CREATE DATABASE`, `CREATE EXTENSION`, `ALTER TABLE ... ADD PRIMARY KEY`).
- Por qué: Automatiza pasos repetitivos y maneja errores comunes (coordinator con hostname `localhost`, falta de DB en workers, tablas sin PK que bloquean `citus_drain_node`). Facilita reproducibilidad del laboratorio.

`setup_all.sh`
- Para qué: Script de conveniencia para ejecutar todo el flujo en una opción elegida (por ejemplo `compose` o `minikube`).
- Cómo: Ejecutarlo con el argumento `compose` o `minikube` según el entorno deseado; delega a los scripts y manifiestos correspondientes.
- Por medio de qué: Bash y utilidades del sistema; internamente ejecuta `docker compose` o `kubectl`/`minikube` según el modo.
- Por qué: Simplifica la experiencia educativa: un comando para poner en marcha el laboratorio en la configuración elegida.

Directorio `k8s/` (manifiestos y scripts Kubernetes)
---------------------------------------------------

`k8s/citus-coordinator.yml`
- Para qué: Manifiesto Kubernetes (StatefulSet + Service) para desplegar el coordinator en Minikube/cluster.
- Cómo: `kubectl apply -f k8s/citus-coordinator.yml` para crear el StatefulSet y Service. Contiene configuración para arrancar Postgres con `-c wal_level=logical`.
- Por medio de qué: Kubernetes (kubectl), StatefulSet, PVCs/volumes, headless Service para DNS estable.
- Por qué: En Kubernetes se requiere un nombre estable para el coordinator y almacenamiento persistente; además se necesita la configuración de WAL para la replicación lógica.

`k8s/citus-worker-statefulset.yml`
- Para qué: StatefulSet para los workers de Citus, con un PVC por réplica.
- Cómo: `kubectl apply -f k8s/citus-worker-statefulset.yml` para crear los workers; usar headless Service y DNS del StatefulSet para que el coordinator encuentre los workers.
- Por medio de qué: Kubernetes StatefulSet, PVCs, headless Services.
- Por qué: Los workers necesitan nombres/DNS estables (p.ej. `citus-worker-0`) y almacenamiento persistente por réplica para emular un despliegue real.

`k8s/secret-citus.yml`
- Para qué: Secret con credenciales (por ejemplo password de postgres) usado por los manifiestos.
- Cómo: `kubectl apply -f k8s/secret-citus.yml` antes de desplegar pods que lo consumen.
- Por medio de qué: Kubernetes Secret y variables de entorno en los pods.
- Por qué: Evitar componer contraseñas en texto plano en los manifiestos; centralizar credenciales que los pods referencias.

`k8s/register_citus_k8s.sh`
- Para qué: Script que registra los workers desde dentro del entorno Kubernetes (ejecuta comandos `psql` dentro del pod coordinator o hace `kubectl exec`).
- Cómo: Ejecutar desde el host con `./k8s/register_citus_k8s.sh --rebalance --drain` una vez que los pods estén listos.
- Por medio de qué: `kubectl exec` + `psql` + funciones SQL de Citus.
- Por qué: Automatizar la parte de registro dentro del cluster y manejar diferencias de hostnames en Kubernetes.

Nota: `k8s/setup_minikube.sh` ahora invoca `k8s/register_citus_k8s.sh` automáticamente como parte del flujo totalmente automatizado.

`k8s/setup_minikube.sh`
- Para qué: Script para validar dependencias (minikube, kubectl) y opcionalmente arrancar Minikube con los recursos apropiados.
- Cómo: Ejecutar `./k8s/setup_minikube.sh` y seguir las instrucciones (puede requerir permisos o confirmar la cantidad de CPU/memoria asignada).
- Por medio de qué: `minikube`, `kubectl`, Bash.
- Por qué: Facilitar el setup y evitar errores comunes cuando Minikube no tiene recursos suficientes.

Adicional (automatización completa):
- El script construye o carga la imagen personalizada `local/citus-custom:12.1` desde `postgres-citus/Dockerfile` y la carga en Minikube.
- Aplica `k8s/secret-citus.yml` y los manifiestos `citus-coordinator.yml` y `citus-worker-statefulset.yml`.
- Espera a que los pods estén listos, invoca `k8s/register_citus_k8s.sh --rebalance --drain` para registrar workers y ejecutar rebalance/drain.
- Lanza un `kubectl port-forward` en background para exponer el coordinator en `localhost:5432` y ejecuta `k8s/verify_lab.sh` (verificación automática).

Por qué este cambio: eliminar pasos manuales del flujo y asegurar que un solo comando ponga el laboratorio en estado reproducible y verificable para estudiantes.

Directorio `postgres-citus/` (imagen y scripts de inicialización)
----------------------------------------------------------------

`postgres-citus/Dockerfile`
- Para qué: Dockerfile (imagen base) que copia scripts de inicialización en la imagen de PostgreSQL/Citus.
- Cómo: Se construye con `docker build -t <tag> postgres-citus/` si se quiere una imagen personalizada.
- Por medio de qué: Docker, imagen base `citusdata/citus`.
- Por qué: Permitir inicializar el DB con extensiones, esquemas y datos al arrancar el contenedor (útil para reproducir el entorno con un esquema predefinido).

Nota: `k8s/setup_minikube.sh` construye/carga esta imagen etiquetada por defecto como `local/citus-custom:12.1` y los manifiestos Kubernetes han sido actualizados para usarla.

Nuevo archivo añadido:
`k8s/verify_lab.sh`
- Para qué: Verificación automática post-despliegue que comprueba la extensión `citus`, nodos activos, shards y ejecuta una prueba distribuida mínima.
- Cómo: Invocado automáticamente por `k8s/setup_minikube.sh` al final del despliegue; también puede ejecutarse manualmente.
- Por medio de qué: `psql` desde el host contra `localhost:5432` (port-forward) y SQL de prueba.
- Por qué: Proveer feedback inmediato y automático de que el laboratorio quedó funcional, útil para estudiantes y para integraciones CI.

Salida y reporte:
- `k8s/verify_report.json`: el script genera un JSON con la marca de tiempo, estado global (`PASS` o `FAIL`) y una lista de checks con estado y mensajes. El archivo se crea por defecto en `k8s/verify_report.json`.

`postgres-citus/.env.example`
- Para qué: Ejemplo de variables de entorno usadas por el Dockerfile o docker-compose.
- Cómo: Copiar a `.env` y ajustar variables (contraseñas, puertos) si se quiere personalizar.
- Por medio de qué: Variables de entorno leídas por `docker compose` o scripts.
- Por qué: Evitar hardcodear valores y facilitar la configuración local.

`postgres-citus/init/01-extensions.sql`
- Para qué: SQL para crear extensiones necesarias (p.ej. citus, pgcrypto, uuid-ossp si aplica).
- Cómo: Este archivo es copiado por el Dockerfile y ejecutado por la imagen de Postgres al iniciar (si la imagen está configurada para ejecutar scripts en `/docker-entrypoint-initdb.d`).
- Por medio de qué: PostgreSQL al arrancar el contenedor; `psql` en el proceso de init.
- Por qué: Garantizar que la extensión `citus` esté instalada y disponible en la base de datos al iniciar la instancia.

`postgres-citus/init/02-schema-fhir.sql`
- Para qué: Esquema de ejemplo (en este caso FHIR) usado para poblar la base de datos con tablas de ejemplo.
- Cómo: Igual que el anterior, se ejecuta durante la inicialización del contenedor.
- Por medio de qué: SQL estándar ejecutado por el init de Postgres.
- Por qué: Proveer datos y tablas sobre los que practicar operaciones distribuidas.

Archivos auxiliares y utilidades
-------------------------------

`register_citus.sh` (ver arriba) — script central de orquestación para Compose y también usable en K8s.

`.vscode/` (si existe)
- Para qué: Configuración del editor (debug, tareas, ajustes de workspace).
- Por qué: Facilita la experiencia de desarrollo (opcional para los estudiantes).

Pautas de uso y recomendaciones
------------------------------
- Para pruebas rápidas en la máquina del alumno, usar `docker compose up -d` y `bash register_citus.sh --rebalance --drain`.
- Para entornos más realistas o para prácticas avanzadas, usar Minikube con los manifiestos en `k8s/`.
- Si algo falla en el rebalance/drain, comprobar que `wal_level=logical` está activo y que las tablas afectadas tienen PRIMARY KEY o REPLICA IDENTITY. El script intenta arreglar PKs listadas en `PK_FIX_LIST`.

Preguntas frecuentes (rápidas)
------------------------------
- ¿Por qué necesito `wal_level=logical`?  
  Porque Citus utiliza replicación lógica para mover datos entre nodos cuando se rebalanc ea o se drena un nodo.

- ¿Qué hace `citus_set_coordinator_host()`?  
  Establece el hostname que los workers usarán para comunicarse con el coordinator. Si el coordinator está configurado como `localhost` los workers no podrán conectarse desde otros hosts/containers.

- ¿Puedo usar este repo sin Docker?  
  Sí, si tienes PostgreSQL + Citus instalados en máquinas reales; los scripts SQL y las funciones de Citus siguen siendo válidas, pero deberás adaptar los nombres/host/puertos.
