# Capas de acceso (roles) — Resumen y estado

Este documento resume las capas de acceso (roles) previstas en el sistema, su objetivo, el estado de implementación actual y las referencias a los archivos relevantes del código.

> Nota: antes de avanzar con nuevas capas, es importante tener el backend de autenticación/roles probado (tokens JWT y refresh) y verificar que cada endpoint aplica correctamente las dependencias/chequeos de rol.

## Contenidos

- [Capa Administrativa (admin)](#capa-administrativa-admin)
- [Capa Auditoría (auditor)](#capa-auditor%C3%ADa-auditor)
- [Capa Profesional / Médico (practitioner)](#capa-profesional--m%C3%A9dico-practitioner)
- [Capa Admisión / Enfermería (admission)](#capa-admisión--enfermería-admission)
- [Capa Paciente (patient)](#capa-paciente-patient)
- [Observaciones operativas y recomendaciones](#observaciones-operativas-y-recomendaciones)

---

## Capa Administrativa (Admin)

- Estado: ✅ Implementado (endpoints y controladores disponibles).
- Funcionalidades principales:
  - Gestión de usuarios: crear, editar, eliminar, asignar roles y permisos.
    - Código: `backend/src/routes/admin.py`, `backend/src/controllers/admin_users.py`.
  - Gestión de infra/config: deploy/stop/rebuild, gestión de ConfigMaps/Secrets (stubs seguros).
    - Código: `backend/src/services/admin_infra.py` y rutas en `backend/src/routes/admin.py`.
  - Operaciones BD: migraciones, backups/restores (stubs controlados).
    - Código: `backend/src/services/admin_db.py`.
  - Monitorización y logs: endpoints para métricas, logs y auditoría.
    - Código: `backend/src/services/admin_monitoring.py`, rutas en `backend/src/routes/admin.py`.

---

## Capa Auditoría (Auditor)

- Estado: ✅ Implementado (funcional para laboratorio / parcial académica).
- Notas:
  - Se creó el role `auditor` y se añadieron permisos de solo lectura (dependencia `require_auditor_read_only`).
  - Endpoints disponibles:
    - `GET /api/admin/auditor/logs` — listar logs de auditoría (acceso: admin y auditor en modo lectura).
    - `GET /api/admin/auditor/logs/{id}` — detalle de un log.
    - `GET /api/admin/auditor/export` — exportar logs (CSV/PDF). Por diseño, la exportación está restringida a `admin` (se puede ajustar si se desea permitir a auditors).
  - Persistencia y resiliencia:
    - Se añadió la tabla `auditoria` al DDL (`postgres-citus/init/02-schema-fhir.sql`) y está marcada como distribuida por `documento_id` para co-localizar registros por paciente.
    - El sistema registra accesos automáticamente mediante `AuditMiddleware` para rutas auditadas (ej. `/api/patient/*`, `/api/practitioner/*`, `/api/admin/*`).
    - El registro intenta insertar en la tabla distribuida; si la BD no está disponible cae a un fallback en disco (`backend/logs/audit_access.csv` y `backend/logs/audit_exports.csv`).
  - Heurística y contrato de `documento_id`:
    - El middleware infiere `documento_id` por este orden: header (`X-Documento-Id`, `X-Document-Id`, `X-Patient-Id`), `path_params` (ej. `patient_id`), query params, y finalmente el último segmento numérico de la ruta.
    - Existe una opción configurable `require_document_header` (en `backend/src/config.py`) para forzar que proxys/frontends inyecten `X-Documento-Id` y garantizar shard correcto. Cuando está activada, las peticiones a rutas auditadas sin ese header reciben 428 Precondition Required.
  - Export y trazabilidad:
    - La operación de export registra la acción (intento de insert en DB o fallback) y devuelve CSV o PDF.
  - Tests y validación:
    - Añadí tests unitarios para el middleware de auditoría (`backend/tests/test_audit_middleware.py`) que verifican la exigencia del header y la escritura de fallback.

### Limitaciones (aceptables para un parcial)

- No hay UI específica para auditors en el repo; los endpoints y exportes están listos para integrar con una vista.
- Políticas formales de retención/redacción de PII no están definidas (recomendado para producción, no obligatorio en laboratorio).
- El registro es síncrono (insert o append) — suficiente para pruebas y baja carga, pero en producción se sugiere un pipeline asíncrono/cola.

### Recomendaciones rápidas

- Para pruebas reproducibles, habilita `require_document_header=true` en el `.env` o configura el proxy para inyectar `X-Documento-Id`.
- Si quieres que auditors puedan exportar, ajustar la dependencia del endpoint `/export` para incluir al role `auditor`.
- Añadir seed SQL para poblar `auditoria` en staging si necesitas listas de ejemplo para la demo.


---

## Capa Profesional / Médico (Practitioner)

- Estado: ✅ Implementado (endpoints, controladores y dependencias de permiso añadidos).
- Implementación realizada:
  - Endpoints principales añadidos: rutas bajo `src/routes/practitioner.py` que exponen operaciones de lectura para profesionales (p. ej. listar citas filtradas por `admitted`, obtener datos de paciente asignado).
  - Controladores: `src/controllers/practitioner.py` contiene la lógica para obtener pacientes y citas desde la BD.
  - Permisos y chequeos: nuevas dependencias en `src/auth/permissions.py` — p. ej. `require_practitioner_assigned`, `require_admission_or_admin`, y `require_practitioner_or_admin` que aplican las reglas de acceso por rol y por asignación.
  - Flujo de visibilidad de citas: se añadió la regla operativa que las citas "patient-held" deben ser aceptadas por un admissioner antes de ser visibles para profesionales. Esto se implementó comprobando el estado `admitted` de la cita y usando la dependencia `require_admission_or_admin` para administrar el bypass por `admin`.
  - Ajustes al controlador de admisión: `src/controllers/admission.py` ahora devuelve `paciente_id` tras crear una admisión; además la prueba de integración añadió la función SQL `generar_codigo_admision()` en el DDL de pruebas para mantener compatibilidad con el controlador.
  - Tests: se añadieron y/o adaptaron tests unitarios y de integración:
    - Unit / mocks: `backend/tests_patient/test_practitioner_assignment.py` y `backend/tests_patient/test_practitioner_endpoints.py` (cubren asignación, accesos por role y filtrado por `admitted`).
    - Integración/E2E: existe un test opt-in `backend/tests/test_admission_integration_db.py` que levanta un Postgres en contenedor y comprueba el flujo real de admisión. Está marcado opt-in (RUN_INTEGRATION=1) para no ejecutar en cada CI por defecto.
  - Resultado de pruebas: la suite completa de tests (unit + patient tests) se ejecuta satisfactoriamente en local tras las modificaciones y estabilizaciones (ejecución registrada: 37 tests coleccionados — 35 passed, 2 skipped).

Intención original mantenida:
  - Proveer acceso clínico controlado a profesionales, con separación clara entre lo que puede ver un `practitioner` y lo que sólo ve el `admission`/staff hasta que la admisión es confirmada.

---

## Capa Admisión / Enfermería (Admission)

- Estado: ✅ Implementado (endpoints y controladores disponibles; ver notas más abajo).
- Intención:
  - Registro demográfico, gestión de citas, registro de signos vitales, notas de enfermería, workflows de admisión/triage.

### Notas sobre el estado actual

- Implementación funcional: se añadieron rutas y controladores para crear/listar admisiones, marcar admitido/alta, crear derivaciones (tasks), registrar signos vitales, notas de enfermería, administración de medicamentos y actualizar demografía. Código relevante: `backend/src/routes/patient.py`, `backend/src/controllers/admission.py`, `backend/src/schemas/admission.py`.
- Protecciones: endpoints administrativos están protegidos por la dependencia que niega el rol `patient` (`src/auth/permissions.py`).
- Pendientes (no bloqueantes para uso básico): pruebas de integración E2E contra BD seedada, documentación ampliada (OpenAPI/ejemplos), manejo transaccional más robusto (rollbacks en operaciones compuestas) y observabilidad adicional (logs/metrics).

---

## Capa Paciente (Patient)

- Objetivo: permitir al paciente autenticado acceder a sus datos, solicitar citas, descargar resúmenes y consultar medicaciones/alergias.
- Estado: PARCIAL — varias funcionalidades implementadas y verificadas; quedan pruebas E2E y ajustes menores.

### Implementado (verificado en el código)

- Autenticación y claims
  - JWT + refresh implementados; claim `documento_id` incluido. Archivos: `backend/src/auth/jwt.py`, `backend/src/auth/refresh.py`.
  - Middleware que inyecta `request.state.user`: `backend/src/middleware/auth.py`.

- Endpoints de lectura y export
  - `GET /api/patient/me` → `backend/src/routes/patient.py:get_my_profile` (fallback a partir del token si `User` no existe en BD).
  - `GET /api/patient/me/summary` → `backend/src/routes/patient.py:get_my_summary` (usa `src/controllers/patient.get_patient_summary_from_model`).
  - `GET /api/patient/me/summary/export?format=pdf|fhir` → `backend/src/controllers/patient.generate_patient_summary_export` (PDF con ReportLab y Bundle FHIR JSON).
  - `GET /api/patient/me/appointments` → `backend/src/routes/patient.py:get_my_appointments` (paginación y filtro `estado`).
  - `GET /api/patient/me/appointments/{appointment_id}` → `backend/src/routes/patient.py:get_my_appointment_detail`.
  - `GET /api/patient/me/encounters/{encounter_id}` → `backend/src/routes/patient.py:get_my_encounter`.

- Mutaciones de citas (implementadas y con reglas de negocio)
  - `POST /api/patient/me/appointments` → `backend/src/controllers/patient.create_patient_appointment` (incluye `documento_id` para cumplir constraints Citus; valida disponibilidad y retorna 409 en conflicto).
  - `PATCH /api/patient/me/appointments/{id}` → `backend/src/controllers/patient.update_patient_appointment`.
  - `DELETE /api/patient/me/appointments/{id}` → `backend/src/controllers/patient.cancel_patient_appointment` (soft-cancel con `estado='cancelada'` y política de ventana mínima).

- Reglas de negocio relevantes
  - `is_timeslot_available` y `can_cancel_appointment` implementadas en `backend/src/controllers/patient.py`.
  - Las citas con estado `cancelada` se ignoran al comprobar solapamientos.

- Schemas y modelos
  - `backend/src/schemas/` contiene `PatientOut`, `PatientSummaryOut`, `AppointmentOut`, `EncounterOut`.
  - `MedicationOut` y `AllergyOut` enriquecidos con campos opcionales (`inicio`, `fin`, `via`, `prescriptor`, `estado`, `reacciones`, `onset`, `resolved_at`, `clinical_status`) y validadores que normalizan datetimes a UTC.
  - `backend/src/models/user.py` expone `fhir_patient_id` que enlaza `User` ↔ paciente.

- Medicaciones / Alergias
  - `GET /api/patient/me/medications` y `GET /api/patient/me/allergies` implementados; controladores realizan consultas enriquecidas cuando es posible y caen a consultas mínimas si las columnas no existen.

- Permisos y seguridad
  - Se añadieron protecciones que impiden que el role `patient` modifique historias clínicas o recursos ajenos (`backend/src/auth/permissions.py` y middleware).

- Tests
  - Tests unitarios para la capa paciente: `backend/tests_patient/` (cobertura de mutaciones, export, medicaciones/alergias y endpoints de lectura). Se ejecutaron localmente y pasan.

### Pendiente / Falta por implementar (importante)

- Pruebas E2E reproducibles contra BD seedada (opcional, de integración). Hay seeds y scripts en `postgres-citus/init/` y `k8s/1-CitusSql/populate_db_k8s.sh`, pero no hay una E2E automatizada dentro del repo.
- Revisar comparaciones DB aware/naive si la BD devuelve timestamps sin zona (subtarea de timezone-aware pendiente).

---

## Observaciones operativas y recomendaciones

- Las consultas clínico-administrativas dependen de `User.fhir_patient_id`; si no está poblado, se devuelven listas vacías (comportamiento intencionado).
- Las consultas usan SQL textual (`sqlalchemy.text()`), lo que facilita compatibilidad con el esquema actual pero requiere cuidado con tipos y Citus/Postgres.
- Para pruebas de CI reproducibles es recomendable usar los seed scripts disponibles y/o añadir fixtures que creen `User` con `fhir_patient_id` y filas en `cita`/`encuentro`.

---

## Próximos pasos sugeridos

1. Automatizar un test E2E básico que use la BD seedada y verifique el flujo de paciente (login -> crear cita -> listar -> cancelar).
2. Completar la revisión DB timezone-aware y ejecutar la suite completa de tests del repositorio.
3. Añadir mapeos adicionales en consultas de medicaciones/alergias si el esquema de BD tiene nombres distintos de columnas.

---

_Archivo generado a partir de `capas.txt` y el estado actual del repositorio (rama: experimental)._ 
