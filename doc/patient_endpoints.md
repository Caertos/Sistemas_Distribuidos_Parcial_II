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

Estado de tests / runner
- Los artefactos de tests y debug fueron deshabilitados/retirados del repositorio por decisión del propietario. No existe runner activo ni workflow de pytest en este branch.

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

