
# Proyecto Sistemas Distribuidos - Parcial II

Esta repositorio contiene una aplicación backend en Python (FastAPI) y manifiestos para desplegar una base de datos PostgreSQL+Citus en Kubernetes (Minikube), además de scripts y documentación para pruebas E2E y despliegue local.

En la carpeta `doc/` encontrarás documentación útil para entender y desplegar el sistema. A continuación se listan los documentos disponibles y una breve descripción:

- `doc/postgres-citus.md`
	- Explica qué es Citus y cómo se configura la base de datos distribuida en Kubernetes para este proyecto. Incluye detalles de StatefulSets, Services, probes y el flujo de recuperación.

- `doc/admin_backend.md`
	- Resumen no técnico del backend de administración: qué hace, tecnologías usadas, endpoints disponibles, modelos y servicios auxiliares. Es la referencia rápida para administradores del sistema.

- `doc/resultados-tests/admin_tests_report.md`
	- Informe limpio con los resultados de las ejecuciones E2E del módulo admin (tokens, métricas, logs, CRUD de usuarios). Se usa como salida del script `backend/run_admin_tests_e2e.py`.

- `doc/resultados-tests/resultados.md` y `doc/resultados-tests/resultados_refresh_smoke.md`
	- Otros informes de resultados y pruebas (smoke tests, refresh tokens, etc.).

Cómo usar estos documentos
- Para entender la infraestructura de BD y cómo levantar Citus en Minikube, lee `doc/postgres-citus.md`.
- Para saber qué endpoints y operaciones están disponibles para administradores y dónde están implementados, revisa `doc/admin_backend.md`.
- Después de ejecutar las pruebas E2E (por ejemplo con `backend/run_admin_tests_e2e.py` o desde el Job en Kubernetes), consulta `doc/resultados-tests/admin_tests_report.md` para ver el resumen.

## Diagrama de la base de datos

En `doc/schema_diagram.png` encontrarás una representación visual del esquema de la base de datos generada a partir del SQL de inicialización. Si prefieres editar el origen, el fichero Graphviz DOT está en `doc/schema_diagram.dot`.

![Diagrama de la base de datos](doc/schema_diagram.png)

## Instalación automática

El repositorio incluye un script de instalación/arranque automatizado `setup.sh` en la raíz que orquesta los pasos principales para levantar el entorno local (Minikube, Citus y backend). El script se encargará de ejecutar los scripts en `scripts/dev/` y generar un log de la ejecución.

Requisitos previos (en la máquina anfitrión):

- Docker instalado y accesible por el usuario que ejecuta el script.
- Minikube instalado y configurado.
- kubectl instalado y apuntando al contexto correcto.
- Permisos para ejecutar scripts (ejecutar como el mismo usuario que tiene acceso a docker/minikube).

Uso básico

1. Dar permiso de ejecución al script (si es necesario):

```bash
chmod +x setup.sh
```

2. Ejecutar el script (desde la raíz del repo):

```bash
./setup.sh
```

Qué hace el script

- Muestra un banner informativo.
- Lanza Minikube y aplica los manifiestos de Citus (`scripts/dev/0-StartMinikube.sh` y `scripts/dev/1-DeployCitusSql.sh`).
- Despliega el backend usando `scripts/dev/2-DeployBackend.sh`.
- Registra la salida en un archivo `setup_report_<TIMESTAMP>.log` creado en la raíz del repositorio.

Notas y recomendaciones

- El script asume que las herramientas mencionadas están instaladas y disponibles en el PATH. Si alguna falta, la ejecución fallará y el log contendrá detalles del error.
- Si necesitas ejecutar pasos manuales o quieres más control (por ejemplo, reconstruir imágenes dentro del daemon de Minikube), revisa los scripts individuales en `scripts/dev/`.
- El log de la ejecución se crea en la raíz del repositorio como `setup_report_<TIMESTAMP>.log` — revisa ese archivo para diagnosticar fallos.

Si quieres, puedo añadir una sección adicional con comprobaciones previas automáticas (verificar versiones de `minikube`, `docker` y `kubectl`) o una opción `--dry-run` para el script `setup.sh`.


