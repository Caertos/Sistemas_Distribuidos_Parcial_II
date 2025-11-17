"""Rutas mínimas para la Capa Profesional / Médico (practitioner).

Estos endpoints son skeletons (stubs) que devuelven respuestas de ejemplo o 501
cuando la funcionalidad completa no está implementada aún. Sirven para pruebas
de permisos y para integrar el router en la API principal.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.auth import permissions as perms
from src.database import get_db

router = APIRouter()


@router.get("/patients/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db), user=Depends(perms.require_practitioner_assigned)):
    """Obtener datos básicos de un paciente desde la tabla `paciente`.

    Protegido para roles `practitioner` y `admin`. Si la consulta DB falla o no
    devuelve resultados (entorno de pruebas), se devuelve un ejemplo mínimo.
    """
    try:
        q = text("SELECT paciente_id, documento_id, nombre, apellido, sexo, fecha_nacimiento, contacto, ciudad FROM paciente WHERE paciente_id = :pid LIMIT 1")
        row = db.execute(q, {"pid": patient_id}).mappings().first()
        if row:
            out = dict(row)
            # Normalizar fecha a ISO si existe
            if out.get("fecha_nacimiento"):
                try:
                    out["fecha_nacimiento"] = out["fecha_nacimiento"].isoformat()
                except Exception:
                    pass
            return out
    except Exception:
        # Non-fatal: caemos al ejemplo
        pass

    # Fallback de ejemplo para entornos de prueba
    return {"paciente_id": patient_id, "nombre": "Ejemplo", "apellido": "Paciente", "documento_id": None}


@router.get("/appointments")
def list_appointments(admitted: Optional[bool] = Query(True), limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), user=Depends(perms.require_practitioner_or_admin)):
    """Listar citas admitidas para que el practitioner las atienda.

    Por defecto filtra por `estado_admision = 'admitida'`. Si la consulta falla,
    se devuelve un conjunto de ejemplo para permitir tests locales.
    """
    try:
        if admitted:
            q = text("SELECT cita_id, paciente_id, fecha_hora, duracion_minutos, estado, motivo, estado_admision FROM cita WHERE estado_admision = 'admitida' ORDER BY fecha_hora DESC LIMIT :limit")
            rows = db.execute(q, {"limit": limit}).mappings().all()
        else:
            q = text("SELECT cita_id, paciente_id, fecha_hora, duracion_minutos, estado, motivo, estado_admision FROM cita ORDER BY fecha_hora DESC LIMIT :limit")
            rows = db.execute(q, {"limit": limit}).mappings().all()

        items = []
        for r in rows:
            item = dict(r)
            if item.get("fecha_hora"):
                try:
                    item["fecha_hora"] = item["fecha_hora"].isoformat()
                except Exception:
                    pass
            item["admitted"] = (item.get("estado_admision") == "admitida")
            items.append(item)
        if items:
            return {"count": len(items), "items": items}
    except Exception:
        # Fallthrough to sample data
        pass

    # Sample fallback (kept for tests/local dev)
    sample = [
        {"id": 1, "patient_id": "P-001", "time": "2025-11-20T10:00:00Z", "admitted": True},
        {"id": 2, "patient_id": "P-002", "time": "2025-11-20T11:00:00Z", "admitted": False},
    ]
    results = [s for s in sample if s["admitted"] == admitted]
    return {"count": len(results), "items": results}


@router.post("/encounters")
def create_encounter(payload: dict, user=Depends(perms.require_practitioner_or_admin)):
    """Crear encuentro clínico (pendiente implementación completa)."""
    raise HTTPException(status_code=501, detail="Encounter creation not implemented yet")


@router.get("/encounters/{encounter_id}")
def get_encounter(encounter_id: int, user=Depends(perms.require_practitioner_or_admin)):
    raise HTTPException(status_code=501, detail="Get encounter not implemented yet")


@router.post("/observations")
def create_observation(payload: dict, user=Depends(perms.require_practitioner_or_admin)):
    raise HTTPException(status_code=501, detail="Observation creation not implemented yet")


@router.post("/medications")
def create_medication(payload: dict, user=Depends(perms.require_practitioner_or_admin)):
    raise HTTPException(status_code=501, detail="Medication creation not implemented yet")
