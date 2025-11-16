from fastapi import APIRouter, Request, Depends, HTTPException, Path, Query
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from src.schemas import PatientOut
from src.schemas import AppointmentOut, EncounterOut, AppointmentCreate
from src.database import get_db
from src.models.user import User
from src.controllers.patient import public_user_dict_from_model
from src.controllers.patient import (
    get_patient_summary_from_model,
    get_patient_appointments_from_model,
    get_patient_encounter_by_id,
    get_patient_appointment_by_id,
    create_patient_appointment,
)
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



@router.get("/me/appointments", response_model=List[AppointmentOut])
def get_my_appointments(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    estado: Optional[str] = Query(None),
):
    """Lista de citas del paciente autenticado.

    Soporta paginación (limit, offset) y filtro por `estado`.
    """
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = state_user.get("user_id")
    # Logging estructurado mínimo
    try:
        logger.info("patient.me.appointments requested", extra={"user_id": user_id, "limit": limit, "offset": offset, "estado": estado})
    except Exception:
        pass
    try:
        u = db.query(User).filter(User.id == str(user_id)).first()
    except Exception:
        u = None

    if u:
        if hasattr(u, "is_active") and not u.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return get_patient_appointments_from_model(u, db, limit=limit, offset=offset, estado=estado)

    # Fallback: no user loaded -> devolver lista vacía
    return []



@router.post("/me/appointments", response_model=AppointmentOut)
def create_my_appointment(request: Request, payload: AppointmentCreate, db: Session = Depends(get_db)):
    """Permite al paciente autenticado solicitar/crear una cita mínima.

    Validación mínima: el usuario debe tener `fhir_patient_id` vinculado.
    """
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = state_user.get("user_id")
    try:
        u = db.query(User).filter(User.id == str(user_id)).first()
    except Exception:
        u = None

    if not u:
        raise HTTPException(status_code=400, detail="User not linked to a patient record")
    if hasattr(u, "is_active") and not u.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    created = create_patient_appointment(u, db, payload.fecha_hora, payload.duracion_minutos, payload.motivo)
    if not created:
        raise HTTPException(status_code=500, detail="Could not create appointment")
    return created



@router.get("/me/appointments/{appointment_id}", response_model=AppointmentOut)
def get_my_appointment_detail(request: Request, appointment_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    """Detalle de una cita si pertenece al paciente autenticado."""
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = state_user.get("user_id")
    try:
        logger.info("patient.me.appointment_detail requested", extra={"user_id": user_id, "appointment_id": appointment_id})
    except Exception:
        pass
    try:
        u = db.query(User).filter(User.id == str(user_id)).first()
    except Exception:
        u = None

    if u:
        if hasattr(u, "is_active") and not u.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        app = get_patient_appointment_by_id(u, db, appointment_id)
        if not app:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return app

    raise HTTPException(status_code=401, detail="Not authenticated")


@router.get("/me/encounters/{encounter_id}", response_model=EncounterOut)
def get_my_encounter(request: Request, encounter_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    """Detalle de un encuentro si pertenece al paciente autenticado."""
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
        enc = get_patient_encounter_by_id(u, db, encounter_id)
        if not enc:
            raise HTTPException(status_code=404, detail="Encounter not found")
        return enc

    raise HTTPException(status_code=401, detail="Not authenticated")
