backend/tests/test_admin_endpoints_unit.py::test_admin_create_and_get_user

Qué hace: prueba la creación de un usuario administrador y su posterior obtención vía endpoint admin.
Resultado esperado: creación exitosa (201 o similar) y GET devuelve los datos del usuario.
Resultado obtenido: PASSED.
backend/tests/test_admission_endpoints.py::test_create_admission_staff_happy_path

Qué hace: crea una admisión desde un staff (admissioner) en el flujo feliz.
Resultado esperado: admisión creada correctamente y respuesta con datos de admisión.
Resultado obtenido: PASSED.
backend/tests/test_admission_endpoints.py::test_create_vital_patient_happy_path

Qué hace: registra signos vitales de un paciente en el endpoint correspondiente (flujo feliz).
Resultado esperado: signos vitales aceptados y confirmación (200/201).
Resultado obtenido: PASSED.
backend/tests/test_admission_endpoints.py::test_administer_medication_staff_happy_path

Qué hace: simula administración de medicamento por personal de enfermería/admisioner.
Resultado esperado: registro de administración exitoso y respuesta con registro.
Resultado obtenido: PASSED.
backend/tests/test_admission_endpoints_unit.py::test_list_pending_admissions_access_control

Qué hace: verifica control de acceso al listado de admisiones pendientes.
Resultado esperado: sólo roles permitidos pueden ver la lista; respuesta correcta para esos roles.
Resultado obtenido: PASSED.
backend/tests/test_admission_endpoints_unit.py::test_mark_admitted_and_discharge_and_refer

Qué hace: marca una admisión como admitida, luego la da de alta o la deriva (refer).
Resultado esperado: cambios de estado aplicados correctamente en cada operación.
Resultado obtenido: PASSED.
backend/tests/test_admission_endpoints_unit.py::test_nursing_notes_and_med_admin

Qué hace: crea/actualiza notas de enfermería y registra administración de medicación.
Resultado esperado: operaciones aceptadas y persistidas (simulado por mocks/fakes).
Resultado obtenido: PASSED.
backend/tests/test_admission_flow_e2e.py::test_patient_admission_flow

Qué hace: E2E del flujo completo de admisión de paciente (integración más amplia).
Resultado esperado: end-to-end flow completado correctamente en un entorno que lo soporte.
Resultado obtenido: SKIPPED (esta prueba está marcada opt-in; para ejecutarla usar RUN_E2E=1).
backend/tests/test_admission_integration_db.py::test_admission_flow_with_postgres_container

Qué hace: integración que levanta un contenedor Postgres, popula DDL mínimo y prueba flujo de admisión con BD real.
Resultado esperado: la prueba debe pasar cuando Docker está disponible y RUN_INTEGRATION=1.
Resultado obtenido: SKIPPED (opt-in; para ejecutarla usar RUN_INTEGRATION=1).
backend/tests/test_admission_role.py::test_admission_role_allows_create

Qué hace: verifica que el rol adecuado puede crear admisiones.
Resultado esperado: los roles autorizados pueden crear; respuesta 201/200.
Resultado obtenido: PASSED.
backend/tests/test_admission_role.py::test_patient_cannot_create_admission

Qué hace: asegura que un usuario con rol patient no pueda crear admisiones.
Resultado esperado: denegación (403).
Resultado obtenido: PASSED.
backend/tests/test_admission_role.py::test_admin_can_create_admission

Qué hace: verifica que admin puede crear admisiones (bypass/restricción adecuada).
Resultado esperado: creación permitida para admin.
Resultado obtenido: PASSED.
backend/tests/test_patient_endpoints_unit.py::test_get_my_profile_with_db_user

Qué hace: GET /api/patient/me cuando existe el usuario en BD; valida mapeo a perfil.
Resultado esperado: devuelve perfil con datos del usuario.
Resultado obtenido: PASSED.
backend/tests/test_patient_endpoints_unit.py::test_get_my_profile_fallback_when_no_db

Qué hace: GET /api/patient/me cuando no hay usuario en BD; comprueba fallback al token.
Resultado esperado: devuelve datos basados en token (fallback) en vez de BD.
Resultado obtenido: PASSED.
backend/tests/test_patient_endpoints_unit.py::test_create_my_appointment_requires_patient_link

Qué hace: intenta crear cita desde paciente; comprueba que sólo pacientes vinculados pueden crear.
Resultado esperado: requiere vínculo (rechazo si no) o creación si vínculo existe.
Resultado obtenido: PASSED.
backend/tests_patient/test_appointments_rules.py::test_is_timeslot_available_conflict

Qué hace: valida la regla que detecta conflicto de franja horaria (no disponible).
Resultado esperado: retorna que no está disponible por conflicto.
Resultado obtenido: PASSED.
backend/tests_patient/test_appointments_rules.py::test_is_timeslot_available_no_conflict

Qué hace: valida que franja sin conflicto queda disponible.
Resultado esperado: retorna disponible.
Resultado obtenido: PASSED.
backend/tests_patient/test_appointments_rules.py::test_can_cancel_appointment_window_enforced

Qué hace: comprueba ventana de cancelación (política) para permitir/denegar cancelaciones.
Resultado esperado: deniega o permite según la ventana; en test se cubre la condición esperada.
Resultado obtenido: PASSED.
backend/tests_patient/test_appointments_rules.py::test_create_patient_appointment_respects_availability

Qué hace: al crear cita, respeta disponibilidad y no permite solapamientos.
Resultado esperado: creación OK si disponible, rechazo si no.
Resultado obtenido: PASSED.
backend/tests_patient/test_patient_export.py::test_generate_patient_summary_export_pdf

Qué hace: genera export PDF del resumen del paciente.
Resultado esperado: función/endpoint devuelve contenido/pdf simulado y status OK.
Resultado obtenido: PASSED.
backend/tests_patient/test_patient_export.py::test_generate_patient_summary_export_fhir

Qué hace: genera export en formato FHIR del resumen del paciente.
Resultado esperado: devuelve payload FHIR válido (simulado) y status OK.
Resultado obtenido: PASSED.
backend/tests_patient/test_patient_medications_allergies.py::test_get_medications_and_allergies

Qué hace: obtiene listas de medicamentos y alergias para el paciente (endpoints read).
Resultado esperado: devuelve listas JSON correctas.
Resultado obtenido: PASSED.
backend/tests_patient/test_patient_mutations.py::test_create_update_cancel_appointment

Qué hace: prueba crear, actualizar y cancelar una cita desde endpoints del paciente (mutaciones).
Resultado esperado: POST retorna creado (201), PATCH actualiza (200), DELETE cancela (200) y cuerpos esperados.
Resultado obtenido: PASSED.
backend/tests_patient/test_patient_read_endpoints.py::test_get_me_fallback

Qué hace: GET /api/patient/me con fallback cuando no hay usuario DB (similar a unit anterior).
Resultado esperado: devuelve id del sujeto desde token.
Resultado obtenido: PASSED.
backend/tests_patient/test_patient_read_endpoints.py::test_get_summary_and_lists

Qué hace: obtiene summary del paciente y listas (appointments, encounters) mediante endpoints.
Resultado esperado: respuestas con estructura esperada (summary, listas).
Resultado obtenido: PASSED.
backend/tests_patient/test_permissions.py::test_assert_not_patient_raises_401_on_none

Qué hace: verifica helper/dependency que exige no ser paciente; case cuando request.user es None → 401.
Resultado esperado: 401 (unauthenticated).
Resultado obtenido: PASSED.
backend/tests_patient/test_permissions.py::test_assert_not_patient_raises_403_for_patient

Qué hace: misma dependencia cuando el rol es patient → 403.
Resultado esperado: 403.
Resultado obtenido: PASSED.
backend/tests_patient/test_permissions.py::test_assert_not_patient_allows_other_roles

Qué hace: aseguran que otros roles (admin/practitioner) pasan la restricción.
Resultado esperado: permite (no excep).
Resultado obtenido: PASSED.
backend/tests_patient/test_permissions.py::test_deny_patient_dependency_with_dummy_request

Qué hace: valida la dependencia deny_patient con una request dummy.
Resultado esperado: comportamiento esperado según rol/datos.
Resultado obtenido: PASSED.
backend/tests_patient/test_practitioner_assignment.py::test_practitioner_assigned_allowed

Qué hace: verifica que un practitioner asignado a una paciente puede ver datos (consulta de asignación).
Resultado esperado: acceso permitido (200).
Resultado obtenido: PASSED.
backend/tests_patient/test_practitioner_assignment.py::test_practitioner_not_assigned_denied

Qué hace: mismo caso cuando practitioner no está asignado → debe denegar acceso.
Resultado esperado: 403 Forbidden.
Resultado obtenido: PASSED.
backend/tests_patient/test_practitioner_assignment.py::test_practitioner_without_fhir_id_denied

Qué hace: practitioner sin fhir_practitioner_id no puede acceder; valida negativa.
Resultado esperado: 403.
Resultado obtenido: PASSED.
backend/tests_patient/test_practitioner_assignment.py::test_admin_bypasses_assignment

Qué hace: admin debe saltarse la restricción de asignación y poder ver los datos.
Resultado esperado: acceso permitido (200) para admin.
Resultado obtenido: PASSED.
backend/tests_patient/test_practitioner_endpoints.py::test_practitioner_sees_only_admitted_by_default

Qué hace: GET /api/practitioner/appointments por practitioner devuelve solo citas admitidas por defecto.
Resultado esperado: lista con admitted=True y count coherente.
Resultado obtenido: PASSED.
backend/tests_patient/test_practitioner_endpoints.py::test_admin_can_access_practitioner_endpoints

Qué hace: admin puede acceder al endpoint de practitioner (bypass).
Resultado esperado: status 200.
Resultado obtenido: PASSED.
backend/tests_patient/test_practitioner_endpoints.py::test_patient_cannot_access_practitioner_endpoints

Qué hace: paciente no debe poder acceder a endpoints de practitioner.
Resultado esperado: 403 Forbidden.
Resultado obtenido: PASSED.
backend/tests_patient/test_practitioner_endpoints.py::test_unauthenticated_request_is_401

Qué hace: petición sin token al endpoint practitioner debe devolver 401.
Resultado esperado: 401 Unauthorized.
Resultado obtenido: PASSED.

backend/tests/test_auth_login.py::test_login_success

Qué hace: realiza POST JSON a `/api/auth/login` con usuario y contraseña válidos (se inyecta sesión DB falsa con usuario hasheado). Verifica que la respuesta incluya `access_token` y `refresh_token` y que el `access_token` decodificado contenga los claims esperados.
Resultado esperado: status 200; respuesta con `access_token` (JWT) y `refresh_token`; el JWT debe contener `sub` igual al id del usuario, `role` igual a user_type y `username`.
Resultado obtenido: PASSED.
backend/tests/test_auth_login.py::test_login_invalid_credentials

Qué hace: realiza POST JSON a `/api/auth/login` con credenciales inválidas (sin usuario en la DB) y comprueba que el endpoint rechaza el intento.
Resultado esperado: status 401 Unauthorized cuando las credenciales son inválidas.
Resultado obtenido: PASSED.