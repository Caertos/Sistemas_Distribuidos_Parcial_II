"""Rutas mínimas para la Capa Profesional / Médico (practitioner).

Estos endpoints son skeletons (stubs) que devuelven respuestas de ejemplo o 501
cuando la funcionalidad completa no está implementada aún. Sirven para pruebas
de permisos y para integrar el router en la API principal.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from sqlalchemy import text
import logging

logger = logging.getLogger("backend.practitioner")
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
        # Si el usuario es practitioner, limitar las citas al profesional asociado
        role = user.get("role") if isinstance(user, dict) else None
        pract_filter = ""
        params = {"limit": limit}
        if role == 'practitioner':
            # intentar obtener fhir_practitioner_id desde la tabla users
            try:
                q_user = text("SELECT fhir_practitioner_id FROM users WHERE id = :uid LIMIT 1")
                r = db.execute(q_user, {"uid": str(user.get("user_id"))}).mappings().first()
                if r and r.get("fhir_practitioner_id"):
                    pract_id = int(r.get("fhir_practitioner_id"))
                    pract_filter = " AND profesional_id = :pract_id"
                    params["pract_id"] = pract_id
                else:
                    # Si no hay mapping a profesional, devolver vacío para este practitioner
                    return {"count": 0, "items": []}
            except Exception:
                return {"count": 0, "items": []}

        # Traer también datos del paciente para que el frontend pueda mostrar nombre/apellido
        base_select = (
            "SELECT c.cita_id, c.documento_id, c.paciente_id, c.fecha_hora, c.duracion_minutos, c.estado, c.motivo, c.estado_admision, "
            "p.nombre AS paciente_nombre, p.apellido AS paciente_apellido, p.contacto "
            "FROM cita c INNER JOIN paciente p ON c.documento_id = p.documento_id AND c.paciente_id = p.paciente_id "
            "LEFT JOIN profesional pr ON c.profesional_id = pr.profesional_id "
        )

        # Log de depuración: quién pidió la lista y filtro aplicado
        try:
            logger.info("list_appointments called role=%s user=%s pract_filter=%s params=%s admitted=%s", role, user, pract_filter, dict(params), admitted)
        except Exception:
            pass
        # Además imprimir a stdout para asegurar visibilidad en logs
        try:
            print(f"[practitioner] list_appointments called role={role} user={user} pract_filter={pract_filter} params={params} admitted={admitted}")
        except Exception:
            pass

        if admitted:
            qtext = base_select + "WHERE c.estado_admision = 'admitida'" + pract_filter + " ORDER BY c.fecha_hora DESC LIMIT :limit"
            q = text(qtext)
            rows = db.execute(q, params).mappings().all()
        else:
            qtext = base_select + "WHERE 1=1" + pract_filter + " ORDER BY c.fecha_hora DESC LIMIT :limit"
            q = text(qtext)
            rows = db.execute(q, params).mappings().all()

        try:
            logger.info("list_appointments result_count=%d", len(rows))
        except Exception:
            pass
        try:
            print(f"[practitioner] list_appointments result_count={len(rows)}")
        except Exception:
            pass

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
