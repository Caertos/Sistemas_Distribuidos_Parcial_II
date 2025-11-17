from fastapi import HTTPException
from typing import Optional
from fastapi import Request
import logging

logger = logging.getLogger("backend.auth.permissions")
from fastapi import Depends
from src.database import get_db
from sqlalchemy.orm import Session


def assert_not_patient(state_user: Optional[dict]):
    """Lanza HTTPException(403) si el usuario es role 'patient'.

    state_user: dict esperado con clave 'role'. Si state_user es None se lanza 401.
    """
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    role = state_user.get("role")
    if role == "patient":
        raise HTTPException(status_code=403, detail="Patients are not allowed to modify clinical records")


def deny_patient_dependency(request: Request):
    """Dependency para usar en routes: raise 401/403 según el estado del user en request.state.

    Uso: @router.post(..., dependencies=[Depends(deny_patient_dependency)])
    """
    state_user = getattr(request.state, "user", None)
    assert_not_patient(state_user)


def require_practitioner_or_admin(request: Request):
    """Dependency: sólo permite acceso a usuarios con role 'practitioner' o 'admin'.

    Nota: en una implementación real adicionalmente comprobaríamos que el
    practitioner está asignado al paciente consultado. Aquí retornamos el
    state_user para que el handler pueda usarlo.
    """
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    role = state_user.get("role")
    if role not in ("practitioner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions: practitioner or admin required")
    # En entornos de desarrollo donde no existan listas de asignación, permitir por defecto.
    logger.debug("Access granted to role=%s", role)
    return state_user


def require_practitioner_assigned(patient_id: int, request: Request, db: Session = Depends(get_db)):
    """Dependency que verifica que el practitioner del token esté asignado al paciente.

    Estrategia simple (suficiente para control de acceso inicial):
    - Obtener el fhir_practitioner_id del usuario autenticado (users.fhir_practitioner_id).
    - Buscar en tablas `cita` y `encuentro` si existe alguna fila donde paciente_id = :patient_id y profesional_id = :pract_id.
    - Si existe, permitir; si no, lanzar 403.

    Nota: Esta implementación usa consultas SQL textuales y requiere una sesión DB
    (pasada por FastAPI como dependencia `get_db`). Está pensada para ser una
    verificación inicial; puede ampliarse para chequear asignaciones explícitas
    en una tabla de asignaciones o reglas más complejas.
    """
    from sqlalchemy import text

    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    role = state_user.get("role")
    if role == "admin":
        return state_user
    if role != "practitioner":
        raise HTTPException(status_code=403, detail="Insufficient permissions: practitioner required")

    user_id = state_user.get("user_id")
    try:
        # Obtener fhir_practitioner_id del usuario
        q_user = text("SELECT fhir_practitioner_id FROM users WHERE id = :uid LIMIT 1")
        r = db.execute(q_user, {"uid": str(user_id)}).mappings().first()
        if not r or not r.get("fhir_practitioner_id"):
            raise HTTPException(status_code=403, detail="Practitioner identity not linked to profesional record")
        pract_id = int(r.get("fhir_practitioner_id"))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Could not verify practitioner identity")

    try:
        # Buscar coincidencias en cita o encuentro
        q = text("SELECT 1 FROM (SELECT profesional_id FROM cita WHERE paciente_id = :pid AND profesional_id = :pr LIMIT 1 UNION SELECT profesional_id FROM encuentro WHERE paciente_id = :pid AND profesional_id = :pr LIMIT 1) AS t LIMIT 1")
        found = db.execute(q, {"pid": patient_id, "pr": pract_id}).mappings().first()
        if not found:
            raise HTTPException(status_code=403, detail="Practitioner not assigned to this patient")
    except HTTPException:
        raise
    except Exception:
        # En caso de error de DB no permitir acceso por seguridad
        logger.exception("Error checking practitioner assignment for user=%s patient=%s", user_id, patient_id)
        raise HTTPException(status_code=500, detail="Error verifying practitioner assignment")

    return state_user


def require_admission_or_admin(request: Request):
    """Dependency: permite sólo roles 'admission' o 'admin'.

    Devuelve el state_user si tiene permisos, o lanza HTTPException(401/403).
    """
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    role = state_user.get("role")
    if role in ("admission", "admin"):
        logger.debug("Admission access granted to role=%s", role)
        return state_user
    raise HTTPException(status_code=403, detail="Insufficient permissions: admission or admin required")
