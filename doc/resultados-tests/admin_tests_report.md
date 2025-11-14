# Informe E2E Admin — ejecución final limpia

Fecha: 2025-11-14T17:36:00 — Resumen final

Resultado general: GREEN

Endpoints verificados (resumen)
- auth (/api/auth/token): 200 OK — token emitido para `admin1`.
- monitor/metrics (/api/admin/monitor/metrics): 200 OK.
- monitor/logs (/api/admin/monitor/logs): 200 OK.
- forbidden_non_admin: 403 OK.
- missing_auth: 401 OK.

Admin CRUD (flujo verificado)
- POST /api/admin/users → 201 Created (ej. id: 0af2f2fc-26c6-476f-a805-7b0cebc6304d)
- GET /api/admin/users/{id} → 200 OK
- PATCH /api/admin/users/{id} → 200 OK (partial update aplicado)
- DELETE /api/admin/users/{id} → 204 No Content
- GET after delete → 404 Not Found

Notas breves
- Se priorizó la operación PATCH en la documentación OpenAPI: la ruta PUT se mantiene por compatibilidad pero está marcada como deprecated en la especificación OpenAPI (summary/description + deprecated=True).
- Se corrigió el hashing para evitar el límite de bcrypt (ver cambios en `backend/src/auth/utils.py`).
- `UserOut.id` usa UUID y `UserUpdate` permite campos opcionales para updates parciales.

Artefactos
- Informe: `doc/resultados-tests/admin_tests_report.md` (este archivo)