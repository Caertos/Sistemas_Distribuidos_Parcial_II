
# Informe de tests — suite completa

**Fecha:** 2025-11-17

## Resumen ejecutivo

- Tests ejecutados: **37**
- Pasaron: **31**
- Fallaron: **6**
- Comando usado: `pytest -q backend/tests backend/tests_patient`

---

## Fallos (detallado)

1) backend/tests_patient/test_patient_medications_allergies.py :: test_get_medications_and_allergies
  - Qué comprueba: rutas `/api/patient/me/medications` y `/api/patient/me/allergies` devuelven listas de medicamentos/alergias.
  - Esperado: HTTP 200 y listas con al menos un elemento (el test parchea controladores para devolver datos ficticios).
  - Resultado: FAILED — IndexError: lista vacía (la respuesta fue `[]`).
  - Nota: el test aplica monkeypatch a los controladores y a las referencias en el módulo de rutas; la respuesta vacía sugiere que la inyección del usuario o los mocks no se aplicaron en el contexto de la petición.

2) backend/tests_patient/test_patient_mutations.py :: test_create_update_cancel_appointment
  - Qué comprueba: endpoints POST/PATCH/DELETE de citas para el paciente (con dependencias parcheadas).
  - Esperado: POST -> 201, PATCH/DELETE -> 200.
  - Resultado: FAILED — La creación devolvió 400 con body {"detail":"User not linked to a patient record"}.
  - Nota: indica que el token/usuario utilizado por el TestClient no tiene `fhir_patient_id` vinculado o que la dependencia fake DB no entregó un usuario esperado.

3) backend/tests_patient/test_patient_read_endpoints.py :: test_get_summary_and_lists
  - Qué comprueba: `/api/patient/me/summary`, `/api/patient/me/appointments`, `/api/patient/me/appointments/{id}` con controladores parcheados.
  - Esperado: 200 en todos los endpoints y datos en JSON.
  - Resultado: FAILED — la petición a `/api/patient/me/appointments/1` devolvió 401 Not authenticated.
  - Nota: sugiere problemas con la inyección/lectura del token o con `request.state.user` en el middleware durante la prueba.

4) backend/tests_patient/test_practitioner_assignment.py :: test_practitioner_assigned_allowed
  - Qué comprueba: dependencia `require_practitioner_assigned` permite el acceso cuando el profesional está asignado al paciente.
  - Esperado: 200
  - Resultado: FAILED — 500 Internal Server Error (excepción interna en la ruta).
  - Nota: hay una excepción no capturada en tiempo de ejecución; el traceback en la salida sugiere error al resolver claims/DB fake.

5) backend/tests_patient/test_practitioner_assignment.py :: test_practitioner_not_assigned_denied
  - Qué comprueba: acceso denegado (403) cuando no existe asignación.
  - Resultado: FAILED — 500 Internal Server Error (en vez de 403).

6) backend/tests_patient/test_practitioner_assignment.py :: test_practitioner_without_fhir_id_denied
  - Qué comprueba: practitioner sin `fhir_practitioner_id` debe ser denegado.
  - Resultado: FAILED — 500 Internal Server Error (en vez de 403).

---

## Pasaron (resumen)

Los 31 tests que pasaron incluyen: crear/administer admission flows unitarios, E2E simulado, integración contra Postgres (test_admission_integration_db), endpoints de practitioner básicos, permisos generales y reglas de citas.

---

## Observaciones generales

- Muchos tests parchean funciones importadas en módulos de controladores y además parchean las referencias que los módulos de rutas guardaron al importarse; si se olvida parchear una de las dos referencias (controlador vs rutas), el test puede comportarse de forma inesperada.
- Algunos fallos parecen ser por contaminación/estado entre tests cuando se ejecutan en conjunto (ciertos tests pasaron al ejecutarse de forma individual). Recomendación: asegurar que cada test restaure `app.dependency_overrides` y no deje mocks globales, y usar fixtures que garanticen aislamiento total.
- Para los 3 tests que retornaron 500 (practitioner_assignment), necesito ejecutar esos tests en modo -s para capturar el traceback completo y corregir la excepción o ajustar los fakes.

---

*** Fin del informe actualizado

