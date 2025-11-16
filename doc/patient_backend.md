Patient backend — estado rápido
Fecha: 2025-11-16

Resumen corto
- Implementado esquema Pydantic: `backend/src/schemas/patient.py` (PatientOut).
- Añadido helper de serialización: `backend/src/controllers/patient.py` (public_user_dict_from_model).
- Ruta añadida: GET `/api/patient/me` en `backend/src/routes/patient.py` (registrada en `backend/src/routes/api.py` bajo `/api/patient/me`).
- Test mínimo: `backend/tests/test_patient.py` (happy path fallback cuando no hay usuario en BD).

Despliegue
- Backend desplegado en Minikube; Postgres-Citus desplegado y poblado con datos de ejemplo.
- Servicio expuesto (NodePort) durante pruebas: ejemplo `http://192.168.49.2:32283` (puede variar según minikube).

Verificaciones realizadas (rápidas)
- GET /api/patient/me sin token -> 401 Unauthorized (correcto).
- GET /api/patient/me con token válido (subject no en BD) -> 200 y devuelve id del token + campos públicos (fallback).

Tests ejecutados (breve)
- Prueba: token inválido
	- En qué consiste: llamar `GET /api/patient/me` con un Authorization: Bearer <token inválido>.
	- Resultado esperado: 401 Unauthorized.
	- Resultado obtenido: 401 Unauthorized — PASÓ.

- Prueba: usuario inactivo
	- En qué consiste: marcar el usuario `paciente1` como `is_active=false` en la BD y luego obtener un token con `/api/auth/token` (credenciales seed) y llamar `GET /api/patient/me` con ese token.
	- Resultado esperado: 401 Unauthorized (el endpoint debe rechazar usuarios inactivos).
	- Resultado obtenido: 401 Unauthorized — PASÓ.

Próximos pasos (prioridad alta)
1. Serialización segura: asegurar que no se expongan `hashed_password`, refresh tokens ni flags sensibles.
2. Logging/auditoría mínima en el endpoint (user_id, path, timestamp).
3. Tests adicionales: token inválido, usuario inactivo, respuesta con usuario real desde BD.
4. Documentación de contrato (doc/patient_endpoints.md) y ejemplos curl.
5. Endpoints específicos: implementados (esta iteración)
	 - GET `/api/patient/me/appointments` -> devuelve lista de `AppointmentOut`.
	 - GET `/api/patient/me/encounters/{encounter_id}` -> devuelve detalle `EncounterOut`.

Contratos rápidos (endpoints nuevos)

- GET /api/patient/me/appointments
	- Auth: Bearer JWT (subject = UUID del usuario, role patient) o middleware que pone request.state.user
	- Response: 200 OK, body: JSON array de AppointmentOut
		- AppointmentOut: {"cita_id": int, "fecha_hora": ISO8601 | null, "duracion_minutos": int | null, "estado": str | null, "motivo": str | null}
	- 401 si no autenticado o usuario inactivo.

- GET /api/patient/me/encounters/{encounter_id}
	- Auth: Bearer JWT
	- Response: 200 OK, body: EncounterOut
		- EncounterOut: {"encuentro_id": int, "fecha": ISO8601 | null, "motivo": str | null, "diagnostico": str | null}
	- 404 si el encuentro no existe o no pertenece al paciente; 401 si no autenticado/inactivo.

Ejemplo de prueba (usar `testmap.txt`):

1) Obtener UUID de un usuario paciente (p.ej. `paciente2`):
	 kubectl exec -n clinical-database citus-coordinator-0 -- psql -U postgres -d hce_distribuida -t -c "SELECT id FROM users WHERE username='paciente2' LIMIT 1;" | tr -d ' \n\r'

2) Generar token dentro del pod backend y llamar endpoint:
	 kubectl exec -n clinical-database <backend-pod> -- python3 -c "from src.auth.jwt import create_access_token; import urllib.request; t=create_access_token(subject='<UUID>', extras={'role':'patient'}); req=urllib.request.Request('http://backend-service:8000/api/patient/me/appointments', headers={'Authorization': f'Bearer {t}'}); print(urllib.request.urlopen(req).read().decode())"

Notas de verificación
- Las nuevas rutas usan la misma política de autorización y checks `is_active` que `/me` y `/me/summary`.
- Mantener `testmap.txt` como referencia antes de probar (mapeos temporales en BD, tokens generados dentro del pod, rollback si se actualiza `users.fhir_patient_id`).

Notas
- El endpoint ya intenta cargar el usuario desde la BD si la sesión está disponible; si no, devuelve un fallback que facilita pruebas rápidas.
- Mantendré este archivo corto — iremos ampliándolo conforme avancemos con más endpoints y tests.

Manual API test run (ejecución local usando TestClient)
Fecha: 2025-11-16

Se ejecutaron llamadas directas contra la aplicación usando `fastapi.testclient.TestClient` (modo local, sin servidor HTTP externo). Se generó un token JWT con subject `manual-test-uid-1` para simular un paciente NO presente en la BD (fallback path). A continuación los casos, respuestas observadas y notas.

Resultados:

- Caso: GET /api/patient/me (sin token)
	- Esperado: 401 Missing auth
	- Obtenido: 401
	- Respuesta: {"detail": "Missing authorization"}

- Caso: GET /api/patient/me (con token, usuario no en BD)
	- Esperado: 200 con fallback (id tomado del token)
	- Obtenido: 200
	- Respuesta:
		{
			"id": "manual-test-uid-1",
			"username": "patient",
			"email": "",
			"full_name": null,
			"fhir_patient_id": null,
			"created_at": null
		}

- Caso: GET /api/patient/me/summary (con token)
	- Esperado: 200 con patient + listas vacías (fallback)
	- Obtenido: 200
	- Respuesta:
		{
			"patient": { ... },
			"appointments": [],
			"encounters": []
		}

- Caso: GET /api/patient/me/appointments (con token)
	- Esperado: 200 (lista, posiblemente vacía)
	- Obtenido: 200
	- Respuesta: []

- Caso: GET /api/patient/me/appointments/99999 (con token)
	- Esperado: 401 o 404 (usuario no en BD)
	- Obtenido: 401
	- Respuesta: {"detail": "Not authenticated"}

- Caso: GET /api/patient/me/encounters/1 (con token)
	- Esperado: 401 o 404 (usuario no en BD)
	- Obtenido: 401
	- Respuesta: {"detail": "Not authenticated"}

- Caso: POST /api/patient/me/appointments (crear) con payload mínimo
	- Payload enviado: {"fecha_hora": "2025-12-01T09:00:00", "duracion_minutos": 30, "motivo": "Prueba creación"}
	- Esperado: 400/500 (dependiendo si existe `fhir_patient_id` y la BD está accesible). Como el usuario no está vinculado, el endpoint debe rechazar.
	- Obtenido: 400
	- Respuesta: {"detail": "User not linked to a patient record"}

Notas y conclusiones rápidas:
- El comportamiento observado coincide con el diseño: cuando `User` no existe en BD el sistema devuelve fallback para GET /me y summary, y devuelve listas vacías para appointments/encounters.
- Los endpoints de detalle y creación requieren que `User.fhir_patient_id` esté poblado y que exista/sea accesible la tabla `cita`/`encuentro` en la BD para devolver datos o insertar registros.
- La POST de creación devuelve 400 en ausencia de vinculación entre `User` y `paciente` — esto es correcto según la implementación reciente.


Registro de pruebas ejecutadas (end-to-end) — 2025-11-16
----------------------------------------------------
Resumen: desplegué un entorno limpio usando `./setup.sh` (arranca Minikube, despliega Postgres-Citus y backend), ejecuté el script de población y probé login + creación/listado de citas con el usuario seed `patient1`.

Entorno y seed:
- Namespace: `clinical-database` (Minikube)
- Usuario seed: username `patient1`, id `11111111-1111-1111-1111-111111111111`, password `secret` (insertado por el script de población).

Pasos ejecutados (comandos clave):
1) Abrir port-forward al backend (temporal):
   kubectl -n clinical-database port-forward deployment/backend-deployment 8000:8000 &

2) Obtener token (POST /api/auth/token):
   curl -s -X POST -d "username=patient1&password=secret" http://localhost:8000/api/auth/token
   -> Resultado: HTTP 200 con `access_token` y `refresh_token`.

3) Crear cita (POST /api/patient/me/appointments) usando el access_token:
   curl -s -X POST http://localhost:8000/api/patient/me/appointments \
     -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
     -d '{"fecha_hora":"2025-11-30T10:30:00","duracion_minutos":30,"motivo":"Prueba post-despliegue"}'

4) Listar citas del paciente autenticado (GET /api/patient/me/appointments):
   curl -s http://localhost:8000/api/patient/me/appointments -H "Authorization: Bearer <TOKEN>"

Salidas observadas (resumen):
- Token obtenido: respuesta 200 con `access_token` (JWT). Claim `sub` corresponde al UUID del usuario seed y contiene `role: patient` y `documento_id: '1'`.
- Respuesta creación de cita: HTTP 200, body:
  {"cita_id": 2, "fecha_hora": "2025-11-30T10:30:00Z", "duracion_minutos": 30, "estado": "programada", "motivo": "Prueba post-despliegue"}
- Respuesta listado de citas: array con la cita nueva (cita_id 2) y la cita seed existente (cita_id 1).

Resultado de la prueba: PASS — la ruta de creación de citas funciona end-to-end con el seed determinista y el backend desplegado en Minikube. Se verificó que el controller ahora añade `documento_id` al INSERT en `cita` (evita errores por la constraint de PK en Citus).

Notas operacionales:
- El port-forward usado se cerró al finalizar las pruebas; si se desea interactuar manualmente puedes volver a abrirlo con el comando indicado.
- Si deseas, puedo añadir un script pequeño `scripts/test_patient_end2end.sh` que automatice login → crear cita → listar citas y guarde resultados en `doc/`.

Fin del registro de pruebas.
