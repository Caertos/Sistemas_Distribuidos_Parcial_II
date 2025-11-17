# Backend Admin — Resumen y referencia

## Resumen
El módulo "admin" del backend proporciona un conjunto de herramientas y APIs pensadas para que administradores del sistema puedan:

- Gestionar usuarios (crear, listar, actualizar, borrar y asignar roles).
- Ejecutar tareas de infraestructura y mantenimiento (desplegar/stop/rebuild servicios, crear/restore backups, ejecutar migraciones).
- Consultar métricas operativas, logs y reportes de auditoría.

Estas operaciones están protegidas: solo usuarios con el rol de administrador pueden acceder a ellas.

Si eres administrador, piensa en este módulo como el panel de control del sistema: desde aquí puedes cuidar usuarios, gestionar tareas de infraestructura y ver información operativa básica.


## Tecnologías principales

- Python 3 (FastAPI) — API web.
- SQLAlchemy — acceso a la base de datos (modelo `User`).
- Pydantic — esquemas de entrada/salida (validación de datos).
- Passlib (PBKDF2) — hashing y verificación de contraseñas.
- JWT (módulo de autenticación) — tokens de acceso.


## Qué hace (por áreas, en lenguaje sencillo)

- Gestión de usuarios: crear nuevos usuarios en la base de datos, ver la lista de usuarios, actualizar datos de usuarios (parcial o total) y eliminarlos.
- Roles: asignar roles y marcar si un usuario es superusuario.
- Operaciones de infraestructura: endpoints que actúan como "botones" para pedir acciones como desplegar un servicio o reconstruir una imagen (estas llamadas llaman a funciones de `src/services` que por defecto devuelven respuestas seguras/no destructivas).
- Base de datos: endpoints para crear backups, restaurarlos y lanzar migraciones (las rutinas reales están pensadas para ejecutarse desde herramientas separadas; desde el API se exponen stubs seguros).
- Monitorización: obtener métricas simuladas, leer logs almacenados localmente y obtener reportes de auditoría (simulados).


## Endpoints disponibles (resumen y dónde está en el código)

Los endpoints del admin están en `backend/src/routes/admin.py` bajo el prefijo `/api/admin` (el router se monta con ese prefijo en la aplicación principal).

Ejemplos directos en el código (líneas representativas):

- Crear usuario (POST /api/admin/users)

  `@router.post("/users", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED, dependencies=[require_role("admin")])`

- Listar usuarios (GET /api/admin/users)

  `@router.get("/users", response_model=List[schemas.UserOut], dependencies=[require_role("admin")])`

- Obtener usuario (GET /api/admin/users/{user_id})

  `@router.get("/users/{user_id}", response_model=schemas.UserOut, dependencies=[require_role("admin")])`

- Actualizar usuario (PATCH y PUT) (PATCH recomendado)

  `@router.patch("/users/{user_id}", response_model=schemas.UserOut, dependencies=[require_role("admin")])`

  `@router.put("/users/{user_id}", response_model=schemas.UserOut, dependencies=[require_role("admin")], deprecated=True)`

- Borrar usuario (DELETE /api/admin/users/{user_id})

  `@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[require_role("admin")])`

- Asignar rol (POST /api/admin/users/{user_id}/role)

  `@router.post("/users/{user_id}/role", response_model=schemas.UserOut, dependencies=[require_role("admin")])`

- Operaciones de infraestructura (POST /api/admin/infra/*)

  `@router.post("/infra/deploy", dependencies=[require_role("admin")])`  → llama a `src.services.admin_infra.deploy_service`

- Operaciones de BD (backup/restore/migrate)

  `@router.post("/db/backup", dependencies=[require_role("admin")])`  → llama a `src.services.admin_db.create_backup`

  `@router.post("/db/restore", dependencies=[require_role("admin")])` → llama a `src.services.admin_db.restore_backup`

  `@router.post("/db/migrate", dependencies=[require_role("admin")])` → llama a `src.services.admin_db.run_migrations`

- Monitorización (GET /api/admin/monitor/*)

  `@router.get("/monitor/metrics", dependencies=[require_role("admin")])` → `src.services.admin_monitoring.get_metrics`

  `@router.get("/monitor/logs", dependencies=[require_role("admin")])` → `src.services.admin_monitoring.get_logs`

  `@router.get("/monitor/audit", dependencies=[require_role("admin")])` → `src.services.admin_monitoring.get_audit_reports`


## Modelos de datos (qué guarda el sistema)

El objeto principal para administración de usuarios es `User` (tabla `users`) definido en `backend/src/models/user.py`.

Fragmento representativo (campos importantes):

- `id` — identificador (UUID almacenado como texto)
- `username`, `email`, `full_name`
- `hashed_password` — contraseña hasheada
- `user_type` — tipo/rol del usuario (p.ej. `admin`, `patient`, `practitioner`)
- `is_superuser`, `is_active`, `is_verified`

Ejemplo muy corto tomado del archivo (campo id):

`id = Column(String, primary_key=True)  # UUID stored as text`


## Diagrama de la base de datos

Este repositorio incluye un diagrama generado a partir del SQL de inicialización. El PNG derivado está disponible en `schema_diagram.png` (misma carpeta `doc/`) y el fichero fuente Graphviz DOT está en `schema_diagram.dot`.

![Diagrama de la base de datos](schema_diagram.png)

Si necesitas modificar el diagrama, edita `schema_diagram.dot` y vuelve a generar la imagen (por ejemplo con `dot -Tpng schema_diagram.dot -o schema_diagram.png`).


## Lógica de negocio (controladores)

Las operaciones sobre usuarios (crear, listar, actualizar, eliminar, asignar rol) están en `backend/src/controllers/admin_users.py`.

Acciones y puntos clave:

- `create_user(...)` — valida unicidad (username/email), genera un UUID, hashea la contraseña y guarda el registro.
  - Línea de ejemplo (creación de id): `u.id = str(uuid4())`
  - Hashing de contraseña: `u.hashed_password = hash_password(password)` (ver `src.auth.utils`)

- `update_user(...)` — si se envía `password`, la hashea; aplica cambios parciales sobre los campos recibidos.
  - Ejemplo: `if "password" in data and data.get("password"):`

- `delete_user(...)` — borra el registro de la base de datos.

- `assign_role(...)` — asigna `user_type` y `is_superuser`.


## Autenticación y permisos

- El control de acceso se realiza mediante una dependencia `require_role("admin")` en las rutas; revisa `backend/src/auth/roles.py`.
  - Esa dependencia comprueba `request.state.user` y su `role`.
  - Ejemplo en código: `def require_role(required_role: str) -> Callable:` (retorna una dependencia FastAPI).

- Hashing de contraseñas y compatibilidad con semillas antiguas está en `backend/src/auth/utils.py`.
  - Algoritmo actual: `pbkdf2_sha256` (passlib).
  - Verificación: primero intenta `pbkdf2_sha256.verify`, tiene compatibilidad con un hash estático usado por el script de poblado y un fallback a comparación SHA256 hex.
  - Ejemplo de llamada al hasher: `return pbkdf2_sha256.hash(password)` en `hash_password()`.


## Servicios auxiliares

En `backend/src/services/` hay módulos que implementan acciones invocadas por los endpoints de infra/db/monitoring. Están pensados como "stubs seguros" en este repositorio (dev-friendly):

- `admin_infra.py` — funciones: `deploy_service`, `stop_service`, `rebuild_image`. Generalmente devuelven una respuesta con la acción requerida y una nota para indicar que el build real se ejecuta mediante scripts CLI.
  - Ejemplo nota: `"note": "Usa los scripts en scripts/dev para realizar builds reales"`.

- `admin_db.py` — funciones: `run_migrations`, `create_backup`, `restore_backup`, `maintenance`. Devuelven respuestas simuladas o instrucciones.

- `admin_monitoring.py` — `get_metrics`, `get_logs`, `get_audit_reports`. A día de hoy devuelven métricas y logs simulados o leen ficheros locales si existen.
  - Ejemplo de métrica simulada: `"cpu_usage": 12.3`.


## Pruebas y verificación

- Hay un verificador E2E en `backend/run_admin_tests_e2e.py` que realiza llamadas HTTP reales contra `API_URL` (por defecto `http://localhost:8000`) autenticándose con el usuario semilla `admin1/secret` y ejecutando el flujo:
  1. Obtener token (POST `/api/auth/token`)
  2. Consultar métricas y logs
  3. Verificar permisos (intentar con un usuario no-admin)
  4. CRUD completo de usuario (create → get → update → delete) usando la API real

Este script es la referencia práctica para saber si "todo el admin funciona" en un despliegue.


## Dónde mirar si algo falla

- Rutas / API: `backend/src/routes/admin.py` — aquí están las rutas expuestas y las dependencias de permiso.
- Lógica de usuarios (DB): `backend/src/controllers/admin_users.py` — aquí se crean/actualizan/borran registros.
- Modelo: `backend/src/models/user.py` — descripción de los campos guardados.
- Autenticación/Hashing: `backend/src/auth/utils.py` y `backend/src/auth/roles.py` — ver compatibilidad de hashes y control de roles.
- Servicios de infra/DB/monitor: `backend/src/services/*` — implementaciones seguras de las acciones administrativas.


## Notas y recomendaciones

- Las llamadas a infra/backup/migrate están pensadas como "pedidos"; las acciones potencialmente destructivas (p. ej. un restore) no se ejecutan automáticamente aquí: los servicios devuelven instrucciones y la intención es que una herramienta externa (scripts CLI o procedimientos de DBA) realice la operación final.
- Para pruebas de integración reales, usa el script E2E (`backend/run_admin_tests_e2e.py`) contra un backend desplegado y con la DB poblada. Para desarrollos locales rápidos se pueden crear versiones con `TestClient` pero éstas no validan toda la cadena (auth real, persistencia en DB, etc.).

## Notas sobre la capa de pacientes

Aunque este documento está centrado en las capacidades administrativas, el backend incluye una capa dedicada a operaciones sobre pacientes (`/api/patient`). Cambios recientes relevantes para administradores y desarrolladores:

- Export y reportes: existe un endpoint `GET /api/patient/me/summary/export?format=pdf|fhir` que permite obtener el resumen del paciente en PDF o como Bundle FHIR JSON. El PDF usa ReportLab cuando está disponible.
- Reglas de negocio: la lógica de creación/cancelación de citas incorpora validaciones importantes (solapamientos, ventana mínima de cancelación) que pueden afectar flujos E2E y scripts de migración/monitorización.
- Datos clínicos: las respuestas sobre medicaciones y alergias han sido enriquecidas con campos opcionales (fechas de inicio/fin, vía, prescriptor, reacciones, estado clínico). Los controladores intentan consultas enriquecidas y mantienen retrocompatibilidad con esquemas simples.
- Timezones: la aplicación normaliza datetimes a UTC (timezone-aware) internamente; esto es importante al integrar sistemas externos o al revisar logs y auditorías.

Si vas a realizar tareas de administración que consulten o manipulen datos clínicos de pacientes, revisa los endpoints y las reglas de negocio arriba citadas para evitar acciones no deseadas (p. ej. cancelar citas muy próximas o crear citas en horarios en conflicto).


---

Archivo creado automáticamente: `doc/admin_backend.md` — referencia de alto nivel sobre el backend administrativo y dónde se implementan sus funciones.
