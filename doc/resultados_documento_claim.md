# Resultados: inclusión del claim `documento_id` en access token JWT

Fecha: 2025-11-16

Resumen
- Se implementó la inclusión del claim `documento_id` (valor: `user.fhir_patient_id` o `user.fhir_practitioner_id`) en los access tokens emitidos por el backend.
- Se preserva el claim durante la rotación/refresh del token.
- Se añadieron protecciones para evitar que `extras` sobrescriban claims reservados (`sub`, `exp`, `iat`).

Archivos modificados
- `backend/src/routes/auth.py`: se añade `documento_id` al dict `extras` pasado a `create_access_token` tanto en `/token` como en `/refresh`.
- `backend/src/auth/jwt.py`: `create_access_token` ahora incluye `iat`, `exp` y mezcla `extras` sin permitir sobrescritura de `sub`, `exp` o `iat`.
- `backend/tests/test_auth_documento_claim.py`: tests que verifican la presencia de `documento_id` y que los claims reservados no puedan ser sobrescritos.

Despliegue realizado
- Script ejecutado: `./setup.sh` (usa `scripts/dev/0-StartMinikube.sh`, `1-DeployCitusSql.sh`, `2-DeployBackend.sh`).
- Minikube levantado correctamente, imagenes construidas e imágenes locales cargadas en el Docker de Minikube.
- Base de datos poblada con datos de prueba. Credenciales generadas (ejemplos):
  - Administradores: admin1/secret, admin2/secret
  - Pacientes: paciente1/secret ... paciente10/secret

Ejecución de tests
- Se creó un virtualenv local y se instalaron dependencias del backend y `pytest`.
- Comando ejecutado para tests:

```bash
. .venv_test/bin/activate
PYTHONPATH=backend pytest -q
```

- Resultado de la suite de tests (local):
  - 6 passed, 9 warnings

Notas técnicas y consideraciones
- Privacidad: `documento_id` puede ser identificador personal. Recomendar revisar política de privacidad. Si es necesario, considerar enviar un identificador no reversible (hash salado) en lugar del documento real.
- TTL de tokens: mantener short TTL para access tokens (ej. 15 minutos) y usar refresh tokens opacos.
- Middleware: actualizar cualquier middleware que espere `fhir_patient_id` desde la BD para usar preferentemente el claim `documento_id` del token cuando esté presente.

Pasos siguientes recomendados
1. Abrir PR desde la rama `experimental` hacia `main` con los cambios.
2. Revisar y actualizar documentación interna / OpenAPI si se desea exponer que el token contiene `documento_id`.
3. Implementar tests de integración E2E que usen los endpoints `/api/auth/token` y `/api/auth/refresh` para validar el flujo completo (podría añadirse a `backend/run_admin_tests_e2e.py`).

Comandos útiles reproducibles

Levantar minikube y desplegar (ya usado):
```bash
bash setup.sh
```

Ejecutar tests localmente (recomendado desde la raíz del repo):
```bash
python3 -m venv .venv_test
source .venv_test/bin/activate
pip install -r backend/requirements.txt pytest httpx
PYTHONPATH=backend pytest -q
```

Conclusión
La implementación fue desplegada en Minikube y los tests unitarios añadidos pasan correctamente. El claim `documento_id` está disponible en los JWTs emitidos y preservado tras refresh.
