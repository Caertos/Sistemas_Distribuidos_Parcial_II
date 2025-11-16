# Endpoints de la Capa Paciente

Este documento resume el estado actual de la Capa Paciente (implementaciones, contratos y pendientes) y ofrece instrucciones operativas breves para desarrolladores.

Estado actual (breve)
- Se han implementado endpoints de lectura y la infraestructura de autenticación JWT.
- No hay endpoints de mutación (crear/editar/cancelar citas), ni endpoints para medicaciones/alergias ni export/descarga de historia clínica.

Rutas implementadas (prefijo /api/patient)

- GET /me
  - Response: `PatientOut`
  - Devuelve datos públicos del usuario autenticado. Si existe un registro `User` en la BD con `id == token.sub` y `is_active`, devuelve el registro; en otro caso devuelve un fallback basado en el claim del token.

- GET /me/summary
  - Response: `PatientSummaryOut`
  - Retorna `patient` + `appointments` + `encounters` (listas simplificadas). Implementación obtiene hasta 10 entradas recientes de tablas `cita` y `encuentro` cuando `User.fhir_patient_id` está poblado.

- GET /me/appointments
  - Response: List[`AppointmentOut`]
  - Query params: `limit` (1..200, por defecto 100), `offset` (>=0), `estado` (opcional).
  - Implementación: consulta SQL textual sobre la tabla `cita` filtrando por `paciente_id` tomado desde `User.fhir_patient_id`.

- GET /me/appointments/{appointment_id}
  - Response: `AppointmentOut` o 404 si la cita no existe o no pertenece al paciente.

- GET /me/encounters/{encounter_id}
  - Response: `EncounterOut` o 404 si no existe o no pertenece al paciente.

Schemas y modelos relevantes
- `backend/src/schemas/` contiene `PatientOut`, `PatientSummaryOut`, `AppointmentOut`, `EncounterOut`.
- `backend/src/models/user.py` incluye el campo `fhir_patient_id` (relación User ↔ paciente). Este campo debe estar poblado para que las consultas a `cita` y `encuentro` devuelvan datos.

Nota importante sobre autenticación
- Todas las rutas requieren un access token JWT válido en la cabecera `Authorization: Bearer <token>`.
- El token debe llevar `sub` con el `users.id` (UUID) para búsquedas DB-backed; si no existe un `User` correspondiente, muchos endpoints devuelven fallback o listas vacías.

Operaciones y ejemplos de llamadas (uso en cluster)

- Generar token dentro del pod (ejemplo):

```bash
# Ejecutar en el pod backend para obtener un token de prueba
kubectl exec -n clinical-database -it <backend-pod> -- python3 -c "from src.auth.jwt import create_access_token; print(create_access_token(subject='829c5351-26f3-4073-a232-7d645a627139', extras={'role':'patient'})))"
```

- Obtener lista de citas (ejemplo):

```bash
curl -s -H "Authorization: Bearer $TOKEN" http://backend-service:8000/api/patient/me/appointments
```

- Obtener detalle de una cita (ejemplo):

```bash
curl -s -H "Authorization: Bearer $TOKEN" http://backend-service:8000/api/patient/me/appointments/2
```

Próximos pasos recomendados

1) Implementar POST `/api/patient/me/appointments` (skeleton) para permitir a pacientes solicitar citas. Validación mínima sugerida: `fecha_hora`, `duracion_minutos`, `motivo`; persistir en `cita` con estado inicial (`SOLICITADA`).

2) Añadir fixtures/seed SQL (opcional) para que entornos de CI/dev dispongan de un `User` con `fhir_patient_id` y datos `cita`/`encuentro` de ejemplo. Esto facilita pruebas de integración reproducibles cuando se reactive testing.

3) Implementar endpoints de lectura para medicaciones/allergies si existen tablas relevantes, o definir el modelo y su almacenamiento antes de exponerlos.

4) Diseñar export/serialización (PDF o FHIR export) y control de consentimientos en una tarea separada (implica revisión legal y requisitos de auditoría).

Notas finales

- El código de rutas y controladores está en `backend/src/routes/patient.py` y `backend/src/controllers/patient.py`.
- Si quieres que implemente ya la tarea 1) (POST /me/appointments skeleton) la puedo crear con tests locales/fixtures o sin tests, según prefieras. Si eliges que lo haga sin tests, lo implementaré y documentaré el endpoint.

Nuevos endpoints de mutación (implementados)

Se han añadido las siguientes rutas para que un paciente autenticado pueda gestionar sus citas:

- POST /me/appointments
  - Propósito: crear/solicitar una nueva cita para el paciente autenticado.
  - Auth: Bearer JWT (token con `sub` = users.id y `role` = "patient").
  - Request JSON (schema `AppointmentCreate`):
    - `fecha_hora`: string ISO8601 (ej. "2025-11-30T10:30:00")
    - `duracion_minutos`: integer
    - `motivo`: string
  - Response: `AppointmentOut` (JSON) con campos: `cita_id` (int), `fecha_hora`, `duracion_minutos`, `estado` (por defecto `programada`), `motivo`.
  - Códigos HTTP:
    - 200 OK: cita creada correctamente.
    - 400 Bad Request: usuario no vinculado a registro `paciente` (no existe `User.fhir_patient_id`).
    - 401 Unauthorized: token ausente o inválido.
    - 500 Internal Server Error: error del servidor al persistir.

- PATCH /me/appointments/{appointment_id}
  - Propósito: actualizar campos editables de una cita existente (hora, duración, motivo, estado).
  - Request JSON (schema `AppointmentUpdate`): cualquiera de los campos opcionales: `fecha_hora`, `duracion_minutos`, `motivo`, `estado`.
  - Response: `AppointmentOut` con la representación actualizada.
  - Códigos HTTP:
    - 200 OK: actualizado correctamente.
    - 401 Unauthorized: token ausente o inválido.
    - 400 Bad Request: usuario no vinculado.
    - 404 Not Found: cita no encontrada o no pertenece al paciente.

- DELETE /me/appointments/{appointment_id}
  - Propósito: cancelar (soft-cancel) una cita; el controlador marca `estado = 'cancelada'` y devuelve la cita actualizada.
  - Response: `AppointmentOut` con `estado: "cancelada"`.
  - Códigos HTTP:
    - 200 OK: cancelada correctamente.
    - 401/400/404: como en los casos anteriores según la situación.

Notas de implementación

- Para cumplir con la restricción de esquema en la base distribuida (Citus) la implementación de `create_patient_appointment` busca `paciente.documento_id` antes de hacer el INSERT y lo incluye en la inserción (PK distribuida), evitando errores por constraints.
- Los handlers validan que exista un `User` con `id == token.sub` y que `User.fhir_patient_id` / relación paciente estén poblados cuando corresponda; si no, la ruta POST rechaza con 400.

Ejemplos curl (cluster interno / servicio)

Obtener token (ejemplo de uso de la cuenta seed en Minikube):

```bash
curl -s -X POST -d "username=patient1&password=secret" http://localhost:8000/api/auth/token
# -> respuesta JSON con access_token
```

Crear cita (POST):

```bash
TOKEN="<ACCESS_TOKEN>"
curl -s -X POST http://backend-service:8000/api/patient/me/appointments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fecha_hora":"2025-11-30T10:30:00","duracion_minutos":30,"motivo":"Consulta"}'
```

Actualizar cita (PATCH):

```bash
curl -s -X PATCH http://backend-service:8000/api/patient/me/appointments/42 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"motivo":"Cambio de motivo","fecha_hora":"2025-11-30T11:00:00"}'
```

Cancelar cita (DELETE):

```bash
curl -s -X DELETE http://backend-service:8000/api/patient/me/appointments/42 \
  -H "Authorization: Bearer $TOKEN"
```

Tests y estado actual

- Se añadió un test unitario (mockeando DB y controladores) que cubre crear, actualizar y cancelar una cita: `backend/tests/test_patient_mutations.py`.
- Resultado actual en esta sesión: el test unitario pasó (1 passed). Hay DeprecationWarnings por librerías externas, no afectan el resultado.

Próximos pasos recomendados (documentación)

- Extraer ejemplos y contratos a `doc/patient_endpoints.md` (hecho en esta edición).
- Añadir un script e2e `scripts/test_patient_end2end.sh` que use la cuenta seed (`patient1`) para automatizar login -> crear -> listar y guardar salidas en `doc/`.

