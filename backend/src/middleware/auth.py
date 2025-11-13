from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from typing import List
from src.auth.jwt import verify_token
from src.config import settings


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
        # allow public paths
        for prefix in self.allow_list:
            if path == prefix or path.startswith(prefix.rstrip("*")):
                return await call_next(request)

        auth_header = request.headers.get("authorization")
        if not auth_header:
            return JSONResponse({"detail": "Missing authorization"}, status_code=401)

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse({"detail": "Invalid authorization header"}, status_code=401)

        token = parts[1]
        try:
            payload = verify_token(token)
            user_id = payload.get("sub")
            role = payload.get("role", "user")
            # attach minimal identity
            request.state.user = {"user_id": user_id, "role": role}
            return await call_next(request)
        except Exception as e:
            # En modo debug incluimos el mensaje de error para facilitar debugging
            if getattr(settings, "debug", False):
                return JSONResponse({"detail": "Invalid or expired token", "error": str(e)}, status_code=401)
            return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)
