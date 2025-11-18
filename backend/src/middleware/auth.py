from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from typing import List
import logging
from src.auth.jwt import verify_token
from src.config import settings

logger = logging.getLogger("backend.auth")


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware ASGI para validar JWT en requests entrantes.

    - Excluye rutas en `allow_list`
    - Si token válido, añade `request.state.user = {user_id, role}`
    - Si inválido o ausente devuelve 401
    """

    def __init__(self, app, allow_list: List[str] = None):
        super().__init__(app)
        self.allow_list = allow_list or ["/health", "/api/auth/token"]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Permitir explícitamente la raíz '/' como pública - algunos entornos
        # pueden presentar la petición con formas que impidan coincidir con
        # la `allow_list` tal como está configurada. Hacer un bypass directo
        # para evitar que la página de inicio requiera token.
        if path == "/":
            return await call_next(request)
        # Entry point for auth dispatch
        # allow public paths
        # Support two forms in allow_list:
        # - exact match (e.g. '/')
        # - prefix match using trailing '*' (e.g. '/static*')
        for prefix in self.allow_list:
            try:
                if prefix.endswith("*"):
                    if path.startswith(prefix[:-1]):
                        return await call_next(request)
                else:
                    if path == prefix:
                        return await call_next(request)
            except Exception:
                # if any malformed prefix, skip it
                continue

        auth_header = request.headers.get("authorization")
        token = None

        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]

        # Fallback: permitir token en cookie llamada 'access_token' para clientes
        # que almacenan el JWT en cookie (ej. HttpOnly). Esto es una conveniencia;
        # usar cookies requiere considerar CSRF en endpoints state-changing.
        if not token:
            try:
                token = request.cookies.get('access_token')
            except Exception:
                token = None

        # Persist a small trace to disk (helps when stdout isn't showing per-request prints)
        try:
            with open('/tmp/auth_debug.log', 'a') as _f:
                _f.write(f"TOKEN_PRESENT={bool(token)} auth_header_present={bool(auth_header)}\n")
        except Exception:
            pass

        if not token:
            return JSONResponse({"detail": "Missing authorization"}, status_code=401)
        # Primero verificar el token; cualquier fallo aquí es fallo de auth
        logger.info(f"AuthMiddleware: received token prefix={(token or '')[:32]}...")
        try:
            payload = verify_token(token)
        except Exception as e:
            logger.exception(f"Token verification failed for path={path}: %s", e)
            # Dejar que el logger capture la excepción; no imprimir en stdout aquí.
            if getattr(settings, "debug", False):
                return JSONResponse({"detail": "Invalid or expired token", "error": str(e)}, status_code=401)
            return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)

        # Si llegamos aquí, token válido -> adjuntar identidad y continuar.
        user_id = payload.get("sub")
        role = payload.get("role", "user")
        request.state.user = {"user_id": user_id, "role": role}
        logger.info(f"Auth OK: path={path} user_id={user_id} role={role}")
        # No envolver call_next en el try/except de verificación; dejar
        # que errores del handler se propaguen y sean gestionados por FastAPI
        return await call_next(request)
