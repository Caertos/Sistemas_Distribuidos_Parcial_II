
# Informe de tests — suite completa

**Fecha:** 2025-11-17

## Resumen ejecutivo

- Tests coleccionados: **37**
- Pasaron: **35**
- Saltaron (skipped): **2**
- Fallaron: **0**
- Comando usado: `PYTHONPATH=backend .venv/bin/pytest -vv backend/tests backend/tests_patient`

---

## Resultado por test (verbose)

Lista completa de tests con su resultado (salida verbosa de pytest):

```
backend/tests/test_admin_endpoints_unit.py::test_admin_create_and_get_user PASSED
backend/tests/test_admission_endpoints.py::test_create_admission_staff_happy_path PASSED
backend/tests/test_admission_endpoints.py::test_create_vital_patient_happy_path PASSED
backend/tests/test_admission_endpoints.py::test_administer_medication_staff_happy_path PASSED
backend/tests/test_admission_endpoints_unit.py::test_list_pending_admissions_access_control PASSED
backend/tests/test_admission_endpoints_unit.py::test_mark_admitted_and_discharge_and_refer PASSED
backend/tests/test_admission_endpoints_unit.py::test_nursing_notes_and_med_admin PASSED
backend/tests/test_admission_flow_e2e.py::test_patient_admission_flow SKIPPED
backend/tests/test_admission_integration_db.py::test_admission_flow_with_postgres_container SKIPPED
backend/tests/test_admission_role.py::test_admission_role_allows_create PASSED
backend/tests/test_admission_role.py::test_patient_cannot_create_admission PASSED
backend/tests/test_admission_role.py::test_admin_can_create_admission PASSED
backend/tests/test_patient_endpoints_unit.py::test_get_my_profile_with_db_user PASSED
backend/tests/test_patient_endpoints_unit.py::test_get_my_profile_fallback_when_no_db PASSED
backend/tests/test_patient_endpoints_unit.py::test_create_my_appointment_requires_patient_link PASSED
backend/tests_patient/test_appointments_rules.py::test_is_timeslot_available_conflict PASSED
backend/tests_patient/test_appointments_rules.py::test_is_timeslot_available_no_conflict PASSED
backend/tests_patient/test_appointments_rules.py::test_can_cancel_appointment_window_enforced PASSED
backend/tests_patient/test_appointments_rules.py::test_create_patient_appointment_respects_availability PASSED
backend/tests_patient/test_patient_export.py::test_generate_patient_summary_export_pdf PASSED
backend/tests_patient/test_patient_export.py::test_generate_patient_summary_export_fhir PASSED
backend/tests_patient/test_patient_medications_allergies.py::test_get_medications_and_allergies PASSED
backend/tests_patient/test_patient_mutations.py::test_create_update_cancel_appointment PASSED
backend/tests_patient/test_patient_read_endpoints.py::test_get_me_fallback PASSED
backend/tests_patient/test_patient_read_endpoints.py::test_get_summary_and_lists PASSED
backend/tests_patient/test_permissions.py::test_assert_not_patient_raises_401_on_none PASSED
backend/tests_patient/test_permissions.py::test_assert_not_patient_raises_403_for_patient PASSED
backend/tests_patient/test_permissions.py::test_assert_not_patient_allows_other_roles PASSED
backend/tests_patient/test_permissions.py::test_deny_patient_dependency_with_dummy_request PASSED
backend/tests_patient/test_practitioner_assignment.py::test_practitioner_assigned_allowed PASSED
backend/tests_patient/test_practitioner_assignment.py::test_practitioner_not_assigned_denied PASSED
backend/tests_patient/test_practitioner_assignment.py::test_practitioner_without_fhir_id_denied PASSED
backend/tests_patient/test_practitioner_assignment.py::test_admin_bypasses_assignment PASSED
backend/tests_patient/test_practitioner_endpoints.py::test_practitioner_sees_only_admitted_by_default PASSED
backend/tests_patient/test_practitioner_endpoints.py::test_admin_can_access_practitioner_endpoints PASSED
backend/tests_patient/test_practitioner_endpoints.py::test_patient_cannot_access_practitioner_endpoints PASSED
backend/tests_patient/test_practitioner_endpoints.py::test_unauthenticated_request_is_401 PASSED
```

---

## Observaciones

- Estado actual: la suite completa se ejecutó y no dejó fallos (35 passed, 2 skipped). Los cambios realizados en `conftest.py` y la eliminación de clientes a nivel de módulo en varios tests mitigaron la contaminación entre pruebas.
- Tests de integración y E2E están marcados como opt-in (skipped por defecto):
  - `backend/tests/test_admission_integration_db.py` (RUN_INTEGRATION=1 para ejecutar)
  - `backend/tests/test_admission_flow_e2e.py` (RUN_E2E=1 para ejecutar)
- Recomendación: completar la refactorización de los tests legacy para eliminar la necesidad de inyectar un `shared_client` desde `conftest.py`. Añadir un fixture `client` en `conftest.py` permitiría un patrón uniforme.

---

## Comandos útiles

Ejecutar suite completa (por defecto integración/E2E SKIPPED):

```bash
PYTHONPATH=backend .venv/bin/pytest -vv backend/tests backend/tests_patient
```

Ejecutar integración (opt-in):

```bash
RUN_INTEGRATION=1 PYTHONPATH=backend .venv/bin/pytest backend/tests/test_admission_integration_db.py -q
```

Ejecutar E2E local (opt-in):

```bash
RUN_E2E=1 PYTHONPATH=backend .venv/bin/pytest backend/tests/test_admission_flow_e2e.py -q
```

---

*** Fin del informe actualizado

