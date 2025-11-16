
# Proyecto Sistemas Distribuidos - Parcial II

Esta repositorio contiene una aplicación backend en Python (FastAPI) y manifiestos para desplegar una base de datos PostgreSQL+Citus en Kubernetes (Minikube), además de scripts y documentación para pruebas E2E y despliegue local.

En la carpeta `doc/` encontrarás documentación útil para entender y desplegar el sistema. A continuación se listan los documentos disponibles y una breve descripción:

- `doc/postgres-citus.md`
	- Explica qué es Citus y cómo se configura la base de datos distribuida en Kubernetes para este proyecto. Incluye detalles de StatefulSets, Services, probes y el flujo de recuperación.

	- `doc/admin_backend.md`
		- Resumen del backend de administración: qué hace, tecnologías usadas, endpoints disponibles, modelos y servicios auxiliares. Es la referencia rápida para administradores del sistema.

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


## Patient API (resumen de las recientes mejoras)

El backend incluye un conjunto de endpoints para la capa de pacientes bajo el prefijo `/api/patient`. Recientemente se añadieron y mejoraron varias funcionalidades importantes:

- Endpoints principales:
	- `GET /api/patient/me` — perfil público mínimo del paciente autenticado.
	- `GET /api/patient/me/summary` — resumen del paciente (incluye últimas citas y encuentros).
	- `GET /api/patient/me/summary/export?format=pdf|fhir` — exporta el resumen en PDF (attachment para descarga) o como Bundle FHIR JSON.
	- `GET /api/patient/me/appointments` — lista de citas (paginada y filtrable por estado).
	- `POST /api/patient/me/appointments` — crear/solicitar una cita (valida solapamientos y retorna 409 si hay conflicto).
	- `PATCH /api/patient/me/appointments/{appointment_id}` — actualizar una cita.
	- `DELETE /api/patient/me/appointments/{appointment_id}` — cancelar una cita (aplica política de ventana mínima de cancelación).
	- `GET /api/patient/me/medications` — lista de medicaciones del paciente (esquema enriquecido).
	- `GET /api/patient/me/allergies` — lista de alergias del paciente (esquema enriquecido).

- Reglas de negocio y validaciones importantes:
	- Disponibilidad de citas: la creación de citas valida solapamientos con citas existentes (se ignoran las canceladas).
	- Política de cancelación: las cancelaciones se restringen si faltan menos de 24 horas (configurable en código).
	- Cuando hay conflicto de horario, el endpoint de creación responde 409 Conflict con detalle apropiado.

- Formato de tiempos y zonas horarias:
	- El sistema migra a datetimes timezone-aware en UTC internamente. Las APIs y los schemas Pydantic normalizan datetimes recibidos (si vienen como cadenas ISO sin zona se asumen en UTC y se convierten a objetos datetime con tzinfo UTC). Esto reduce errores de comparación y evita advertencias relacionadas con datetimes "naive".

- Medicaciones y alergias:
	- Las respuestas de `medications` y `allergies` se enriquecieron con campos opcionales adicionales (p. ej. `inicio`, `fin`, `via`, `prescriptor`, `estado`, `reacciones` para medicaciones; `onset`, `resolved_at`, `clinical_status`, `reacciones` para alergias).
	- Las consultas en el controlador intentan devolver campos enriquecidos si existen en la base de datos; si no, caen a una consulta mínima para mantener compatibilidad con esquemas más simples.

- Exportación PDF/FHIR:
	- La generación de PDF utiliza ReportLab y produce un PDF adjunto descargable con un resumen legible; si ReportLab no está disponible, se devuelve un placeholder PDF básico.
	- La exportación FHIR produce un Bundle básico con el recurso Patient.

Estos cambios están cubiertos por tests unitarios en `backend/tests_patient`.



