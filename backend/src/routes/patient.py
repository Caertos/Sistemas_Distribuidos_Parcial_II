from fastapi import APIRouter, Request, Depends, HTTPException
import logging
from sqlalchemy.orm import Session
from src.schemas import PatientOut
from src.database import get_db
from src.models.user import User
from src.controllers.patient import public_user_dict_from_model
from src.controllers.patient import get_patient_summary_from_model
from src.schemas import PatientSummaryOut

router = APIRouter()
logger = logging.getLogger("backend.patient")


@router.get("/me", response_model=PatientOut)
def get_my_profile(request: Request, db: Session = Depends(get_db)):
    """Devuelve el perfil mínimo del paciente autenticado.

    Intenta cargar información completa desde la BD; si no existe el usuario en la
    BD, devuelve una representación mínima basada en el claim del token (fallback).
    """
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = state_user.get("user_id")

    # Logging mínimo para auditoría/trazabilidad
    try:
        logger.info("patient.me requested", extra={"user_id": user_id, "path": request.url.path})
    except Exception:
        # No dejar que el logger rompa la ruta
        pass

    # Intentar cargar desde la BD (si la sesión DB funciona y existe el usuario)
    try:
        u = db.query(User).filter(User.id == str(user_id)).first()
    except Exception:
        u = None

    if u:
        # Rechazar si el usuario existe pero está inactivo
        if hasattr(u, "is_active") and not u.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return public_user_dict_from_model(u)

    # Fallback: devolver datos mínimos a partir del token
    return {
        "id": str(user_id),
        "username": state_user.get("role") or str(user_id),
        "email": "",
        "full_name": None,
        "fhir_patient_id": None,
        "created_at": None,
    }



@router.get("/me/summary", response_model=PatientSummaryOut)
def get_my_summary(request: Request, db: Session = Depends(get_db)):
    """Resumen mínimo del paciente (patient + lists)."""
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = state_user.get("user_id")
    try:
        u = db.query(User).filter(User.id == str(user_id)).first()
    except Exception:
        u = None

    if u:
        if hasattr(u, "is_active") and not u.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return get_patient_summary_from_model(u, db)

    return {
        "patient": {
            "id": str(user_id),
            "username": state_user.get("role") or str(user_id),
            "email": "",
            "full_name": None,
            "fhir_patient_id": None,
            "created_at": None,
        },
        "appointments": [],
        "encounters": [],
    }
