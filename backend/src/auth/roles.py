from fastapi import Request, HTTPException, status, Depends
from typing import Callable


def require_role(required_role: str) -> Callable:
    """Devuelve una dependencia que comprueba que `request.state.user.role` contiene el role requerido."""

    async def _checker(request: Request):
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        role = user.get("role")
        if role != required_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return Depends(_checker)
