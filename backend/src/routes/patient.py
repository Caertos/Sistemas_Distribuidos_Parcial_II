from fastapi import APIRouter, Request, Depends, HTTPException, Path, Query
from sqlalchemy import text
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from src.schemas import PatientOut
from src.schemas import AppointmentOut, EncounterOut, AppointmentCreate
from src.schemas import AppointmentUpdate
from src.schemas import MedicationOut, AllergyOut
from src.database import get_db
from src.models.user import User
from src.controllers.patient import public_user_dict_from_model
from src.controllers.patient import (
    get_patient_summary_from_model,
    generate_patient_summary_export,
    get_patient_appointments_from_model,
    get_patient_encounter_by_id,
    get_patient_appointment_by_id,
    create_patient_appointment,
    update_patient_appointment,
    cancel_patient_appointment,
    get_patient_medications_from_model,
    get_patient_allergies_from_model,
)
from src.controllers.admission import (
    create_admission,
    get_admission_by_id,
    create_vital_sign,
    add_nursing_note,
    administer_medication,
    update_demographics,
    mark_admitted,
    mark_discharged,
    refer_patient,
)
from src.schemas.admission import (
    AdmissionCreate,
    AdmissionOut,
    VitalSignCreate,
    VitalSignOut,
    NursingNoteCreate,
    DemographicsUpdate,
    ReferralCreate,
    AdmissionActionResponse,
    TaskOut,
    MedicationAdminCreate,
)
from src.schemas.admission import AdmissionUrgentCreate
from fastapi import Depends
from src.auth.permissions import deny_patient_dependency, require_admission_or_admin
from src.schemas import PatientSummaryOut
from datetime import datetime, timedelta, timezone

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
    
@router.put("/me/demographics", response_model=dict)
def update_my_demographics(request: Request, payload: DemographicsUpdate, db: Session = Depends(get_db)):
    """Permite al paciente autenticado actualizar datos demográficos básicos.
    Requiere que el usuario esté vinculado a un registro paciente (fhir_patient_id).
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

    try:
        pid = int(u.fhir_patient_id) if u.fhir_patient_id else None
    except Exception:
        pid = None
    if not pid:
        raise HTTPException(status_code=400, detail="User not linked to a patient record")

    out = update_demographics(db, pid, payload.dict())
    if not out:
        raise HTTPException(status_code=404, detail="Patient record not found or nothing to update")
    return out



@router.post("/{patient_id}/admissions", dependencies=[Depends(require_admission_or_admin)], response_model=AdmissionOut, status_code=201)
def staff_create_admission(request: Request, patient_id: int, payload: AdmissionCreate, db: Session = Depends(get_db)):
    """Crear una admisión para un paciente (uso por personal de admisión/enfermería).
    Requiere rol distinto a 'patient'.
    """
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    admitted_by = state_user.get("username") or state_user.get("user_id")
    created = create_admission(db, admitted_by, payload.dict())
    if created is None:
        raise HTTPException(status_code=400, detail="Could not create admission: patient not found, missing documento_id or invalid data")
    return created



@router.get("/admissions/pending", dependencies=[Depends(require_admission_or_admin)], response_model=list)
def staff_list_pending_admissions(request: Request, db: Session = Depends(get_db)):
    """Lista de citas/solicitudes pendientes de admisión (cola de triage) para personal."""
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        q = text("SELECT * FROM vista_citas_pendientes_admision ORDER BY fecha_hora LIMIT 200")
        rows = db.execute(q).mappings().all()
        logger.info("staff_list_pending_admissions: vista rows=%d", len(rows))
        try:
            print(f"DEBUG: vista rows={len(rows)}")
        except Exception:
            pass
        return [dict(r) for r in rows]
    except Exception:
        # Fallback: si la vista no existe en la BD, limpiar la transacción
        # y consultar directamente la tabla `cita`.
        try:
            try:
                db.rollback()
            except Exception:
                # Si el rollback falla, no interrumpimos el flujo, intentamos la consulta de todos modos
                pass

            q2 = text(
                "SELECT c.cita_id, c.documento_id, c.paciente_id, c.fecha_hora, c.tipo_cita, c.motivo, c.estado, c.estado_admision, p.nombre, p.apellido, p.sexo, p.fecha_nacimiento, p.contacto, EXTRACT(YEAR FROM AGE(p.fecha_nacimiento)) as edad, pr.nombre as profesional_nombre, pr.apellido as profesional_apellido, pr.especialidad FROM cita c INNER JOIN paciente p ON c.documento_id = p.documento_id AND c.paciente_id = p.paciente_id LEFT JOIN profesional pr ON c.profesional_id = pr.profesional_id WHERE c.estado_admision = 'pendiente' OR c.estado_admision IS NULL ORDER BY c.fecha_hora LIMIT 200"
            )
            rows2 = db.execute(q2).mappings().all()
            logger.info("staff_list_pending_admissions: fallback rows=%d", len(rows2))
            try:
                print(f"DEBUG: fallback rows={len(rows2)}")
            except Exception:
                pass
            return [dict(r) for r in rows2]
        except Exception:
            return []



@router.post("/admissions/urgent", dependencies=[Depends(require_admission_or_admin)], response_model=AdmissionOut, status_code=201)
def staff_create_urgent_admission(request: Request, payload: AdmissionUrgentCreate, db: Session = Depends(get_db)):
    """Crear una admisión urgente usando `documento_id` y datos de triage/observación."""
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    admitted_by = state_user.get("username") or state_user.get("user_id")
    from src.controllers.admission import create_emergency_admission

    created = create_emergency_admission(db, admitted_by, payload.dict())
    if not created:
        raise HTTPException(status_code=400, detail="Could not create emergency admission")
    return created


@router.post("/admissions/{cita_id}/accept", dependencies=[Depends(require_admission_or_admin)], response_model=AdmissionActionResponse)
def staff_accept_cita(request: Request, cita_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    """Aceptar una cita pendiente: crear admisión vinculada y marcar la cita como admitida."""
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    accepted_by = state_user.get("username") or state_user.get("user_id")
    from src.controllers.admission import accept_cita

    out = accept_cita(db, accepted_by, cita_id)
    if not out:
        raise HTTPException(status_code=404, detail="Cita not found or could not be accepted")
    return out


@router.post("/admissions/{cita_id}/reject", dependencies=[Depends(require_admission_or_admin)])
def staff_reject_cita(request: Request, cita_id: int = Path(..., ge=1), payload: dict = None, db: Session = Depends(get_db)):
    """Marcar una cita como rechazada (opcionalmente incluir razón)."""
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    rejected_by = state_user.get("username") or state_user.get("user_id")
    reason = None
    try:
        if payload is None:
            payload = {}
        reason = payload.get("reason")
    except Exception:
        reason = None
    from src.controllers.admission import reject_cita

    out = reject_cita(db, rejected_by, cita_id, reason)
    if not out:
        raise HTTPException(status_code=404, detail="Cita not found or could not be rejected")
    return out


@router.get("/debug/admissions/pending")
def debug_list_pending_admissions(db: Session = Depends(get_db)):
    """Ruta debug (temporal) que devuelve directamente las citas
    pendientes consultando la tabla `cita` (sin requerir auth).
    Útil para diagnosticar por qué `/admissions/pending` puede devolver []
    cuando la vista faltante provoca transacciones abortadas.
    """
    try:
        q = text(
            "SELECT c.cita_id, c.documento_id, c.paciente_id, c.fecha_hora, c.tipo_cita, c.motivo, c.estado, c.estado_admision, p.nombre, p.apellido, p.sexo, p.fecha_nacimiento, p.contacto, EXTRACT(YEAR FROM AGE(p.fecha_nacimiento)) as edad, pr.nombre as profesional_nombre, pr.apellido as profesional_apellido, pr.especialidad FROM cita c INNER JOIN paciente p ON c.documento_id = p.documento_id AND c.paciente_id = p.paciente_id LEFT JOIN profesional pr ON c.profesional_id = pr.profesional_id WHERE c.estado_admision = 'pendiente' OR c.estado_admision IS NULL ORDER BY c.fecha_hora LIMIT 200"
        )
        rows = db.execute(q).mappings().all()
        logger.info("debug_list_pending_admissions: rows=%d", len(rows))
        try:
            print(f"DEBUG_ROUTE rows={len(rows)}")
        except Exception:
            pass
        return [dict(r) for r in rows]
    except Exception as e:
        logger.exception("debug_list_pending_admissions error")
        return {"error": str(e)}



@router.post("/admissions/{admission_id}/admit", dependencies=[Depends(require_admission_or_admin)], response_model=AdmissionActionResponse)
def staff_mark_admitted(request: Request, admission_id: str, db: Session = Depends(get_db)):
    """Marcar una admisión existente como 'admitida'."""
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    author = state_user.get("username") or state_user.get("user_id")
    out = mark_admitted(db, admission_id, author)
    if not out:
        raise HTTPException(status_code=404, detail="Admission not found or could not be updated")
    return out



@router.post("/admissions/{admission_id}/discharge", dependencies=[Depends(require_admission_or_admin)], response_model=AdmissionActionResponse)
def staff_mark_discharged(request: Request, admission_id: str, notas: Optional[str] = None, db: Session = Depends(get_db)):
    """Dar de alta (marcar atendida) una admisión."""
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    author = state_user.get("username") or state_user.get("user_id")
    out = mark_discharged(db, admission_id, author, notas)
    if not out:
        raise HTTPException(status_code=404, detail="Admission not found or could not be updated")
    return out



@router.post("/admissions/{admission_id}/refer", dependencies=[Depends(require_admission_or_admin)], response_model=TaskOut)
def staff_refer_patient(request: Request, admission_id: str, payload: ReferralCreate, db: Session = Depends(get_db)):
    """Crear una derivación (tarea) para el paciente asociado a la admisión."""
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    author = state_user.get("username") or state_user.get("user_id")
    out = refer_patient(db, admission_id, author, payload.dict())
    if not out:
        raise HTTPException(status_code=500, detail="Could not create referral task")
    return out


@router.get("/me/admissions", response_model=list)
def get_my_admissions(request: Request, db: Session = Depends(get_db)):
    """Listado de admisiones para el paciente autenticado (reutiliza la vista `vista_admisiones_completas`)."""
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
    try:
        pid = int(u.fhir_patient_id) if u.fhir_patient_id else None
    except Exception:
        pid = None
    if not pid:
        return []
    try:
        q = text("SELECT * FROM vista_admisiones_completas WHERE documento_id = (SELECT documento_id FROM paciente WHERE paciente_id = :pid LIMIT 1) AND paciente_id = :pid ORDER BY fecha_admision DESC LIMIT 100")
        rows = db.execute(q, {"pid": pid}).mappings().all()
        return [dict(r) for r in rows]
    except Exception:
        return []


@router.post("/me/vitals", response_model=VitalSignOut, status_code=201)
def create_my_vital(request: Request, payload: VitalSignCreate, db: Session = Depends(get_db)):
    """Registrar signos vitales para el paciente autenticado."""
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
    try:
        pid = int(u.fhir_patient_id) if u.fhir_patient_id else None
    except Exception:
        pid = None
    if not pid:
        raise HTTPException(status_code=400, detail="User not linked to a patient record")

    created = create_vital_sign(db, u.username or str(user_id), {**payload.dict(), "paciente_id": pid})
    if created is None:
        # likely patient not linked or DB error
        raise HTTPException(status_code=400, detail="Could not record vital sign: patient not found or invalid data")
    return created


@router.post("/{patient_id}/nursing-notes", dependencies=[Depends(require_admission_or_admin)], response_model=dict)
def staff_add_nursing_note(request: Request, patient_id: int, payload: NursingNoteCreate, db: Session = Depends(get_db)):
    """Agregar nota de enfermería (personal)."""
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    author = state_user.get("username") or state_user.get("user_id")
    out = add_nursing_note(db, author, {**payload.dict(), "paciente_id": patient_id})
    if out is None:
        raise HTTPException(status_code=400, detail="Could not add nursing note: patient not found or invalid data")
    return out


@router.post("/{patient_id}/med-admin", dependencies=[Depends(require_admission_or_admin)], response_model=dict)
def staff_administer_med(request: Request, patient_id: int, payload: MedicationAdminCreate, db: Session = Depends(get_db)):
    """Registrar administración de medicamento (personal)."""
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    author = state_user.get("username") or state_user.get("user_id")
    p = {**payload.dict()}
    p["paciente_id"] = patient_id
    out = administer_medication(db, author, p)
    if out is None:
        # Could be missing patient or DB error
        raise HTTPException(status_code=400, detail="Could not register medication administration: patient not found or invalid data")
    return out



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



@router.get("/me/summary/export")
def export_my_summary(request: Request, format: str = Query("pdf", pattern="^(pdf|fhir)$"), db: Session = Depends(get_db)):
    """Exporta el resumen del paciente autenticado en PDF o FHIR (JSON).

    Devuelve un attachment con Content-Disposition para descarga.
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

    payload, media_type, filename = generate_patient_summary_export(u, db, fmt=format)

    # Responder según el tipo
    from fastapi.responses import Response, JSONResponse

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if format and format.lower() == "fhir":
        return JSONResponse(content=payload, media_type=media_type, headers=headers)
    return Response(content=payload, media_type=media_type, headers=headers)



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


@router.get("/practitioners")
def list_practitioners(request: Request, db: Session = Depends(get_db)):
    """Lista de profesionales disponibles para que el paciente elija al crear una cita."""
    state_user = getattr(request.state, "user", None)
    if not state_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        rows = db.query(User).filter(User.user_type.in_(["practitioner", "doctor"]), User.is_active == True).all()
        out = []
        for u in rows:
            out.append({"id": u.fhir_practitioner_id or u.id, "name": u.full_name, "username": u.username})
        return out
    except Exception:
        return []



@router.get("/me/medications", response_model=List[MedicationOut])
def get_my_medications(request: Request, db: Session = Depends(get_db)):
    """Lista de medicaciones del paciente autenticado.

    Si la tabla no existe o no hay paciente asociado, devuelve [] (200).
    """
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
        return get_patient_medications_from_model(u, db)

    return []


@router.get("/me/allergies", response_model=List[AllergyOut])
def get_my_allergies(request: Request, db: Session = Depends(get_db)):
    """Lista de alergias del paciente autenticado.

    Si la tabla no existe o no hay paciente asociado, devuelve [] (200).
    """
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
        return get_patient_allergies_from_model(u, db)

    return []



@router.post("/me/appointments", response_model=AppointmentOut, status_code=201)
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

    # Validar fecha: no permitir citas en el pasado y requerir al menos 2 días de anticipación
    try:
        now = datetime.now(timezone.utc)
        min_allowed = now + timedelta(days=2)
        fh = payload.fecha_hora
        if fh is None:
            raise HTTPException(status_code=400, detail="fecha_hora is required")
        if fh.tzinfo is None:
            fh = fh.replace(tzinfo=timezone.utc)
        else:
            fh = fh.astimezone(timezone.utc)
        if fh < now:
            raise HTTPException(status_code=400, detail="Cannot create appointment in the past")
        if fh < min_allowed:
            raise HTTPException(status_code=400, detail="Appointments must be requested at least 2 days in advance")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid fecha_hora")

    created = create_patient_appointment(u, db, fh, payload.duracion_minutos, payload.motivo, profesional_id=getattr(payload, 'profesional_id', None))
    # created can be a dict with error indication
    if isinstance(created, dict) and created.get("error") == "conflict":
        raise HTTPException(status_code=409, detail="Appointment time conflicts with existing booking")
    if not created:
        raise HTTPException(status_code=500, detail="Could not create appointment")
    return created



@router.patch("/me/appointments/{appointment_id}", response_model=AppointmentOut)
def update_my_appointment(request: Request, appointment_id: int, payload: AppointmentUpdate, db: Session = Depends(get_db)):
    """Permite al paciente actualizar algunos campos de su cita (hora, duracion, motivo, estado)."""
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

    updated = update_patient_appointment(u, db, appointment_id, fecha_hora=payload.fecha_hora, duracion_minutos=payload.duracion_minutos, motivo=payload.motivo, estado=payload.estado)
    if not updated:
        raise HTTPException(status_code=404, detail="Appointment not found or not updatable")
    return updated



@router.delete("/me/appointments/{appointment_id}", response_model=AppointmentOut)
def cancel_my_appointment(request: Request, appointment_id: int, db: Session = Depends(get_db)):
    """Marca la cita del paciente como cancelada (soft-cancel)."""
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

    canceled = cancel_patient_appointment(u, db, appointment_id)
    if not canceled:
        raise HTTPException(status_code=404, detail="Appointment not found or not cancellable")
    return canceled



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
