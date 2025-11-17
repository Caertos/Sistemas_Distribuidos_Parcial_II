from fastapi import Request, HTTPException, status, Depends
from typing import Callable, Iterable, Union


def require_role(required_role: Union[str, Iterable[str]]) -> Callable:
    """Devuelve una dependencia que comprueba que `request.state.user.role` contiene uno de los roles requeridos.

    `required_role` puede ser una cadena (p.ej. 'admin') o un iterable de cadenas
    (p.ej. ('admin', 'auditor')). La dependencia lanzará 401 si no hay user en
    `request.state.user` y 403 si el role del usuario no está autorizado.
    """

    # Normalizar a tuple para facilitar la comparación
    if isinstance(required_role, str):
        allowed = (required_role,)
    else:
        allowed = tuple(required_role)

    async def _checker(request: Request):
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        role = user.get("role")
        if role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return Depends(_checker)


# Conveniencias para importar en rutas
require_practitioner = require_role("practitioner")
require_admin = require_role("admin")
require_auditor = require_role("auditor")
