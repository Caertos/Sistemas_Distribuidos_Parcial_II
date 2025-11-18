Login frontend
=================

Archivos creados:
- `frontend/templates/login.html` - plantilla de login servida por backend.
- `frontend/static/js/auth.js` - utilidades para token (getStoredToken, isTokenValid, wrapFHIR, requireAuth).
- `frontend/static/js/login.js` - lógica de envío del formulario al endpoint `/api/auth/login`.
- `frontend/static/css/login.css` - estilos copiados/adaptados desde `frontend/OLD`.

Endpoints usados:
- `POST /api/auth/login` - body JSON `{ "username": "...", "password": "..." }`.
- `POST /api/auth/refresh` - para refresh tokens (no implementado en este PR pero el backend lo expone).

Valores almacenados en el cliente:
- `localStorage.authToken` - JWT crudo devuelto por backend.
- `localStorage.auth_token` - wrapper `FHIR-` para compatibilidad con código legacy.
- `localStorage.role` - rol del usuario según backend.
- `localStorage.username` - nombre de usuario.
- `localStorage.refreshToken` - refresh token (si está presente en la respuesta).

Redirección por rol (mapeo usado):
- `patient` / `paciente` -> `/patient`
- `practitioner` / `medic` / `medico` / `doctor` -> `/medic`
- `admin` / `administrador` -> `/admin`
- `auditor` -> `/admin`
- Si no hay rol -> `/dashboard`

Comprobar/Probar:
- Levantar backend y abrir `http://localhost:8000/login`.
- Usar las credenciales de prueba que tengas o las del archivo de tests (ej. `juan` / `s3cret`).
- Revisar `localStorage` en DevTools y comprobar `authToken` y `auth_token`.
- En caso de error, se mostrará el `detail` que envíe el backend.
