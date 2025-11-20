"""Rutas mínimas para la Capa Profesional / Médico (practitioner).

Estos endpoints son skeletons (stubs) que devuelven respuestas de ejemplo o 501
cuando la funcionalidad completa no está implementada aún. Sirven para pruebas
de permisos y para integrar el router en la API principal.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from typing import Optional
from sqlalchemy import text
import logging

logger = logging.getLogger("backend.practitioner")
from sqlalchemy.orm import Session
from src.auth import permissions as perms
from src.database import get_db
from src.schemas.admission import VitalSignCreate, VitalSignOut, MedicationAdminCreate
from src.controllers.admission import create_vital_sign, administer_medication

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
        # Siempre devolver el resultado real (incluso si está vacío) en lugar de caer
        # a datos de ejemplo. Esto evita que la UI muestre identificadores ficticios
        # cuando no existen filas reales.
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
def create_encounter(payload: dict, db: Session = Depends(get_db), user=Depends(perms.require_practitioner_or_admin)):
    """Crear encuentro clínico: inserta en `encuentro` y opcionalmente cierra/actualiza la cita asociada.

    Payload esperado (flexible): {
        "patient_id" | "paciente_id": int,
        "appointment_id" | "cita_id": int (opcional),
        "fecha": ISO datetime (opcional),
        "motivo": str (opcional),
        "diagnosis" | "diagnostico": str (opcional),
        "resumen" | "clinical_findings": str (opcional)
    }
    Retorna un objeto compatible con `EncounterOut`.
    """
    try:
        # Resolver identificadores flexibles
        paciente_id = payload.get('patient_id') or payload.get('paciente_id') or payload.get('patient')
        cita_id = payload.get('appointment_id') or payload.get('cita_id')
        fecha = payload.get('fecha')
        motivo = payload.get('motivo') or payload.get('reason') or payload.get('consulta')
        diagnostico = payload.get('diagnosis') or payload.get('diagnostico') or payload.get('diagnosis_text')
        resumen = payload.get('resumen') or payload.get('clinical_findings') or payload.get('treatment_plan') or payload.get('resumen_clinico')

        if not paciente_id:
            raise HTTPException(status_code=400, detail="patient_id (paciente_id) is required")

        # Obtener documento_id del paciente
        q_doc = text("SELECT documento_id FROM paciente WHERE paciente_id = :pid LIMIT 1")
        rdoc = db.execute(q_doc, {"pid": paciente_id}).mappings().first()
        if not rdoc or not rdoc.get('documento_id'):
            raise HTTPException(status_code=400, detail="Paciente no encontrado or missing documento_id")
        documento_id = rdoc.get('documento_id')

        # Intentar resolver profesional_id desde users (si existe)
        profesional_id = None
        try:
            if isinstance(user, dict) and user.get('user_id'):
                q_user = text("SELECT fhir_practitioner_id FROM users WHERE id = :uid LIMIT 1")
                ru = db.execute(q_user, {"uid": str(user.get('user_id'))}).mappings().first()
                if ru and ru.get('fhir_practitioner_id'):
                    try:
                        profesional_id = int(ru.get('fhir_practitioner_id'))
                    except Exception:
                        profesional_id = None
        except Exception:
            profesional_id = None

        # Insertar encuentro (flexible con columnas disponibles)
        q_ins = text(
            "INSERT INTO encuentro (documento_id, paciente_id, cita_id, fecha, motivo, diagnostico, resumen, profesional_id, created_at) "
            "VALUES (:did, :pid, :cid, :fecha, :motivo, :diagnostico, :resumen, :prof, NOW()) RETURNING encuentro_id, fecha, motivo, diagnostico"
        )
        params = {
            "did": documento_id,
            "pid": paciente_id,
            "cid": cita_id,
            "fecha": fecha,
            "motivo": motivo,
            "diagnostico": diagnostico,
            "resumen": resumen,
            "prof": profesional_id,
        }
        row = db.execute(q_ins, params).mappings().first()
        try:
            db.commit()
        except Exception:
            pass

        if not row:
            raise HTTPException(status_code=400, detail="Could not create encounter")

        encounter_id = row.get('encuentro_id')

        # Si se proporcionó cita_id, intentar marcarla como completada/atendida y vincular encuentro
        if cita_id:
            try:
                q_up = text("UPDATE cita SET estado = 'completada', estado_admision = 'atendida', encuentro_id = :eid, updated_at = NOW() WHERE cita_id = :cid AND documento_id = :did RETURNING cita_id")
                db.execute(q_up, {"eid": encounter_id, "cid": cita_id, "did": documento_id})
                try:
                    db.commit()
                except Exception:
                    pass
            except Exception:
                # No fatal: continuar
                try:
                    db.rollback()
                except Exception:
                    pass

        out = {"encuentro_id": encounter_id, "fecha": (row.get('fecha').isoformat() if row.get('fecha') else None), "motivo": row.get('motivo'), "diagnostico": row.get('diagnostico')}
        return out
    except HTTPException:
        raise
    except Exception as e:
        try:
            logger.exception("create_encounter failed")
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/encounters/{encounter_id}")
def get_encounter(encounter_id: int, user=Depends(perms.require_practitioner_or_admin)):
    raise HTTPException(status_code=501, detail="Get encounter not implemented yet")


@router.post("/observations", response_model=VitalSignOut, status_code=201)
def create_observation(request: Request, payload: VitalSignCreate, db: Session = Depends(get_db), user=Depends(perms.require_practitioner_or_admin)):
    """Registrar signo vital desde la interfaz del practitioner.

    Usa `create_vital_sign` en `controllers.admission` y retorna el registro creado.
    """
    # intentar extraer un identificador de autor legible
    author = None
    try:
        # `user` puede ser un dict con 'username' o 'user_id'
        if isinstance(user, dict):
            author = user.get("username") or user.get("user_id")
        else:
            author = getattr(user, "username", None)
    except Exception:
        author = None

    res = create_vital_sign(db, author or "practitioner", payload.dict())
    if not res:
        raise HTTPException(status_code=400, detail="Could not create vital sign")
    # Normalizar salida mínima a VitalSignOut
    out = {"signo_id": res.get("signo_id"), "paciente_id": payload.paciente_id, "fecha": res.get("fecha")}
    return out


@router.post("/medications", status_code=201)
def create_medication(request: Request, payload: MedicationAdminCreate, db: Session = Depends(get_db), user=Depends(perms.require_practitioner_or_admin)):
    """Registrar administración de medicamento desde practitioner.

    Usa `administer_medication` en `controllers.admission`.
    """
    author = None
    try:
        if isinstance(user, dict):
            author = user.get("username") or user.get("user_id")
        else:
            author = getattr(user, "username", None)
    except Exception:
        author = None

    res = administer_medication(db, author or "practitioner", payload.dict())
    if not res:
        raise HTTPException(status_code=400, detail="Could not register medication administration")
    return res
