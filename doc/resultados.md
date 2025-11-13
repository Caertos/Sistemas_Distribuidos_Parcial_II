# Resultados de pruebas internas en Minikube

Fecha: 13 de noviembre de 2025

Objetivo:
- Verificar desde dentro del clúster que el backend responde correctamente a las rutas críticas de autenticación:
  1) GET /health
  2) POST /api/auth/token (form data OAuth2 password) usando credenciales `admin1` / `secret`
  3) GET /api/secure/me usando el token recibido

Nota: Este informe documenta únicamente los resultados de las pruebas internas; no incluye detalles del despliegue.

Comando ejecutado (se usó un pod temporal con la imagen `curlimages/curl`):

```sh
kubectl -n clinical-database run --rm -i --tty tmp-curl --image=curlimages/curl --restart=Never -- sh -c '
  echo "== GET /health ==";
  curl -s -i http://backend-service:8000/health;
  echo;
  echo "== POST /api/auth/token ==";
  resp=$(curl -s -X POST http://backend-service:8000/api/auth/token -d "username=admin1&password=secret" -H "Accept: application/json");
  echo "$resp";
  echo;
  token=$(echo "$resp" | sed -n "s/.*\"access_token\":\"\([^\"]*\)\".*/\1/p");
  echo "== EXTRACTED TOKEN ==";
  echo "$token";
  echo;
  echo "== GET /api/secure/me ==";
  curl -s -i -H "Authorization: Bearer $token" http://backend-service:8000/api/secure/me;
  echo;
  echo "done"'
```

Salida obtenida (recortada a las partes relevantes):

== GET /health ==

HTTP/1.1 200 OK
date: Thu, 13 Nov 2025 19:31:49 GMT
server: uvicorn
content-length: 15
content-type: application/json

{"status":"ok"}

== POST /api/auth/token ==

{"access_token":"<TOKEN_REEMPLAZADO_POR_SEGURIDAD>","token_type":"bearer"}

== EXTRACTED TOKEN ==

<TOKEN_REEMPLAZADO_POR_SEGURIDAD>

== GET /api/secure/me ==

HTTP/1.1 200 OK
date: Thu, 13 Nov 2025 19:31:50 GMT
server: uvicorn
content-length: 74
content-type: application/json

{"user":{"user_id":"253d4433-2c01-4b19-bf6a-25ba649fc90e","role":"admin"}}

Observaciones y conclusiones:
- /health devolvió 200 OK y el payload {"status":"ok"}.
- El endpoint `/api/auth/token` (OAuth2 password flow) respondió un JSON con `access_token` y `token_type: bearer` al enviar las credenciales `admin1`/`secret`.
- El token extraído fue aceptado por el endpoint protegido `/api/secure/me` y devolvió la información del usuario con `user_id` y `role: admin`.

Resultado general: la autenticación y el middleware JWT funcionan correctamente desde dentro del clúster. Las rutas críticas probadas (login y endpoint protegido) devolvieron respuestas esperadas.

Siguientes pasos recomendados (opcionales):
- Repetir la prueba con un cliente HTTP que valide la expiración del token y el manejo de tokens inválidos.
- Automatizar estas verificaciones en un pequeño job de CI/CD o en un `kubectl run --restart=Never` que ejecute pruebas de humo periódicas.
- Si se va a publicar la imagen fuera de Minikube, usar tags versionados y revisar gestión de secretos.

---
Informe generado automáticamente por la prueba ejecutada el 13-11-2025.
