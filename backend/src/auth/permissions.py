from fastapi import HTTPException
from typing import Optional


def assert_not_patient(state_user: Optional[dict]):
    """Lanza HTTPException(403) si el usuario es role 'patient'.

    state_user: dict esperado con clave 'role'. Si state_user es None se lanza 401.
    """
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    role = state_user.get("role")
    if role == "patient":
        raise HTTPException(status_code=403, detail="Patients are not allowed to modify clinical records")
