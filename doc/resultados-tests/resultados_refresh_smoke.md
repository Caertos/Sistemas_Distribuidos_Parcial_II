# Resultados smoke test: refresh token (rotación) y logout

Fecha: 13 de noviembre de 2025

Objetivo
- Ejecutar un test rápido en Minikube que verifique: emisión de access+refresh, acceso a ruta protegida, rotación de refresh token y logout (revocación).

Resumen ejecutivo
- Se ejecutó un port-forward al `Service` del backend y se realizaron las siguientes pruebas:
  1. POST /api/auth/token con credenciales seed (admin1/secret) → 200 OK, se recibió access_token y refresh_token.
  2. GET /api/secure/me con Authorization: Bearer <access_token> → 200 OK, devuelve datos del usuario.
  3. POST /api/auth/refresh con Authorization: Bearer <access_token> y body {refresh_token} → 200 OK, devuelve nuevo access_token y nuevo refresh_token (rotación).
  4. POST /api/auth/logout con Authorization: Bearer <access_token> y body {refresh_token_nuevo} → 200 OK, respuesta {"detail":"logged out"}.
  5. Comprobación en BD (`refresh_tokens`) mostró que el refresh antiguo quedó marcado `revoked = true` y el refresh nuevo también quedó `revoked = true` tras logout.

Comandos y salidas clave

- Levantar port-forward (local):

```bash
kubectl -n clinical-database port-forward svc/backend-service 8000:8000 &
```

- Solicitar tokens (respuesta guardada en /tmp/token_resp.json):

```bash
curl -sS -X POST -d "username=admin1&password=secret" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  http://127.0.0.1:8000/api/auth/token -o /tmp/token_resp.json -w "HTTP_STATUS:%{http_code}\n"
# HTTP_STATUS:200
```

- Resumen (tokens; redacted):

  - access_token: eyJhbGciOiJIUzI1NiIsInR5... (redacted)
  - refresh_token: ik_HSDh8geb_UtVdWAt_HiE... (redacted)

- Petición a ruta protegida `/api/secure/me`:

```bash
curl -sS -H "Authorization: Bearer <access_token>" http://127.0.0.1:8000/api/secure/me -w "HTTP_STATUS:%{http_code}\n" -o /tmp/me_resp.json
# HTTP_STATUS:200
cat /tmp/me_resp.json
# Ejemplo de salida: {"user": {"user_id":"253d4433-...","role":"admin", ...}}
```

- Rotación: POST `/api/auth/refresh` (se envió Authorization también porque el despliegue en el clúster actualmente exige auth en middleware):

```bash
curl -sS -X POST -H "Authorization: Bearer <access_token>" -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token_antiguo>"}' \
  http://127.0.0.1:8000/api/auth/refresh -o /tmp/refresh_resp.json -w "HTTP_STATUS:%{http_code}\n"
# HTTP_STATUS:200
```

- Logout: POST `/api/auth/logout` con el refresh token nuevo:

```bash
curl -sS -X POST -H "Authorization: Bearer <access_token>" -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token_nuevo>"}' \
  http://127.0.0.1:8000/api/auth/logout -o /tmp/logout_resp.json -w "HTTP_STATUS:%{http_code}\n"
# HTTP_STATUS:200
cat /tmp/logout_resp.json
# {"detail":"logged out"}
```

Comprobaciones en la base de datos (coordinador Citus/Postgres)

- Consultas ejecutadas (coordinador):

```sql
SELECT id, token_hash, revoked, created_at
FROM refresh_tokens
ORDER BY id DESC
LIMIT 10;
```

- Resultados (ejemplo extraído tras la ejecución):

| id | token_hash (trunc) | revoked | created_at |
|----|--------------------|---------|------------|
| 6  | e6dabfd3...        | t       | 2025-11-13 21:48:24+00 |
| 5  | 8b562912...        | t       | 2025-11-13 21:46:57+00 |
| 4  | e6038843...        | t       | 2025-11-13 21:31:53+00 |
| 3  | e2e705b1...        | t       | 2025-11-13 21:31:31+00 |
| 2  | e79783f1...        | f       | 2025-11-13 21:07:14+00 |

- Interpretación:
  - Tras la rotación, el refresh anterior aparece marcado `revoked = t` (revocado).
  - Después del logout, el refresh correspondiente se marca también `revoked = t`.

Observaciones y notas

- Middleware y despliegue: aunque en el código local se añadió `/api/auth/refresh` y `/api/auth/logout` a la `allow_list`, el backend desplegado en Minikube aún exigía Authorization en las peticiones (probablemente porque el pod ejecutaba una imagen anterior). Por eso, en las llamadas de prueba se incluyó la cabecera `Authorization: Bearer <access_token>` y las llamadas funcionaron correctamente.

- Tipo de refresh: la implementación usa refresh tokens opacos (se almacena solo el hash SHA-256). En la BD aparecen los `token_hash` y flags `revoked`.

Conclusión

El flujo de emisión, rotación y revocación de refresh tokens funcionó correctamente en el clúster:

- Emisión: OK
- Acceso con access token: OK
- Rotación (exchange) del refresh token: OK (el refresh anterior quedó revocado)
- Logout (revocación): OK (el refresh usado se marcó `revoked = true`)

Recomendaciones

- Para evitar confusiones operacionales, reconstruir y desplegar la imagen del backend con el cambio de `allow_list` aplicado (ya está en el repo) para que `/api/auth/refresh` y `/api/auth/logout` no requieran Authorization si esa es la política deseada.
- Mantener la creación de la tabla `refresh_tokens` en el populate o migraciones (ya se agregó `postgres-citus/init/03-auth-tokens.sql` y se ejecutó desde `populate_db_k8s.sh`).
- Añadir pruebas automáticas (pytest) para cobertura de autenticación y un job de smoke test en CI que ejecute este flujo.

Archivos generados durante la prueba (local /tmp):
- /tmp/token_resp.json
- /tmp/me_resp.json
- /tmp/refresh_resp.json
- /tmp/logout_resp.json

Fin del informe.
