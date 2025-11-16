from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.models.user import User


def public_user_dict_from_model(user: User) -> Dict[str, Any]:
    """Serializa un objeto User a un dict público (excluye campos sensibles)."""
    return {
        # Asegurar que el id se serializa como cadena para evitar errores de
        # validación en Pydantic v2 (UUID != str strict typing).
        "id": str(user.id) if getattr(user, "id", None) is not None else None,
        "username": getattr(user, "username", ""),
        "email": getattr(user, "email", ""),
        "full_name": getattr(user, "full_name", None),
        "fhir_patient_id": getattr(user, "fhir_patient_id", None),
        "created_at": getattr(user, "created_at", None),
    }


def get_patient_summary_from_model(user: User, db: Session) -> Dict[str, Any]:
    """Construye un resumen del paciente consultando tablas principales.

    Devuelve estructuras simplificadas para appointments y encounters.
    """
    # Intentar obtener paciente_id desde user.fhir_patient_id
    pid = None
    try:
        pid = int(user.fhir_patient_id) if user.fhir_patient_id else None
    except Exception:
        pid = None

    appointments: List[Dict[str, Any]] = []
    encounters: List[Dict[str, Any]] = []

    if pid is not None:
        # Obtener últimas 10 citas
        try:
            q = text(
                "SELECT cita_id, fecha_hora, duracion_minutos, estado, motivo FROM cita WHERE paciente_id = :pid ORDER BY fecha_hora DESC LIMIT 10"
            )
            res = db.execute(q, {"pid": pid}).mappings().all()
            for row in res:
                appointments.append({
                    "cita_id": row["cita_id"],
                    "fecha_hora": row["fecha_hora"].isoformat() if row["fecha_hora"] else None,
                    "duracion_minutos": row["duracion_minutos"],
                    "estado": row["estado"],
                    "motivo": row["motivo"],
                })
        except Exception:
            appointments = []

        # Obtener últimos 10 encuentros
        try:
            q2 = text(
                "SELECT encuentro_id, fecha, motivo, diagnostico FROM encuentro WHERE paciente_id = :pid ORDER BY fecha DESC LIMIT 10"
            )
            res2 = db.execute(q2, {"pid": pid}).mappings().all()
            for row in res2:
                encounters.append({
                    "encuentro_id": row["encuentro_id"],
                    "fecha": row["fecha"].isoformat() if row["fecha"] else None,
                    "motivo": row["motivo"],
                    "diagnostico": row["diagnostico"],
                })
        except Exception:
            encounters = []

    return {
        "patient": public_user_dict_from_model(user),
        "appointments": appointments,
        "encounters": encounters,
    }


def get_patient_appointments_from_model(user: User, db: Session, limit: int = 100, offset: int = 0, estado: Optional[str] = None) -> List[Dict[str, Any]]:
    """Devuelve la lista de citas (appointments) para el paciente asociado al usuario.

    Soporta paginación (limit/offset) y filtrado por estado.
    Retorna lista vacía si no hay paciente asociado o si ocurre un error.
    """
    pid = None
    try:
        pid = int(user.fhir_patient_id) if user.fhir_patient_id else None
    except Exception:
        pid = None

    appointments: List[Dict[str, Any]] = []
    if pid is None:
        return appointments

    try:
        # Construir query con filtro opcional por estado
        if estado:
            q = text(
                "SELECT cita_id, fecha_hora, duracion_minutos, estado, motivo FROM cita WHERE paciente_id = :pid AND estado = :estado ORDER BY fecha_hora DESC LIMIT :limit OFFSET :offset"
            )
            params = {"pid": pid, "estado": estado, "limit": limit, "offset": offset}
        else:
            q = text(
                "SELECT cita_id, fecha_hora, duracion_minutos, estado, motivo FROM cita WHERE paciente_id = :pid ORDER BY fecha_hora DESC LIMIT :limit OFFSET :offset"
            )
            params = {"pid": pid, "limit": limit, "offset": offset}

        res = db.execute(q, params).mappings().all()
        for row in res:
            appointments.append({
                "cita_id": row["cita_id"],
                "fecha_hora": row["fecha_hora"].isoformat() if row["fecha_hora"] else None,
                "duracion_minutos": row["duracion_minutos"],
                "estado": row["estado"],
                "motivo": row["motivo"],
            })
    except Exception:
        appointments = []

    return appointments


def get_patient_appointment_by_id(user: User, db: Session, cita_id: int) -> Optional[Dict[str, Any]]:
    """Devuelve una cita por id si pertenece al paciente asociado al usuario.

    Retorna None si no existe o si no pertenece al paciente.
    """
    pid = None
    try:
        pid = int(user.fhir_patient_id) if user.fhir_patient_id else None
    except Exception:
        pid = None

    if pid is None:
        return None

    try:
        q = text(
            "SELECT cita_id, fecha_hora, duracion_minutos, estado, motivo FROM cita WHERE paciente_id = :pid AND cita_id = :cid LIMIT 1"
        )
        row = db.execute(q, {"pid": pid, "cid": cita_id}).mappings().first()
        if not row:
            return None
        return {
            "cita_id": row["cita_id"],
            "fecha_hora": row["fecha_hora"].isoformat() if row["fecha_hora"] else None,
            "duracion_minutos": row["duracion_minutos"],
            "estado": row["estado"],
            "motivo": row["motivo"],
        }
    except Exception:
        return None


def get_patient_encounter_by_id(user: User, db: Session, encounter_id: int) -> Optional[Dict[str, Any]]:
    """Devuelve un encuentro por id si pertenece al paciente asociado al usuario.

    Retorna None si no existe o si no pertenece al paciente.
    """
    pid = None
    try:
        pid = int(user.fhir_patient_id) if user.fhir_patient_id else None
    except Exception:
        pid = None

    if pid is None:
        return None

    try:
        q = text(
            "SELECT encuentro_id, fecha, motivo, diagnostico FROM encuentro WHERE paciente_id = :pid AND encuentro_id = :eid LIMIT 1"
        )
        row = db.execute(q, {"pid": pid, "eid": encounter_id}).mappings().first()
        if not row:
            return None
        return {
            "encuentro_id": row["encuentro_id"],
            "fecha": row["fecha"].isoformat() if row["fecha"] else None,
            "motivo": row["motivo"],
            "diagnostico": row["diagnostico"],
        }
    except Exception:
        return None


def get_patient_medications_from_model(user: User, db: Session) -> List[Dict[str, Any]]:
    """Devuelve la lista de medicamentos para el paciente asociado al usuario.

    Si no existe la tabla o ocurre un error, retorna lista vacía.
    """
    pid = None
    try:
        pid = int(user.fhir_patient_id) if user.fhir_patient_id else None
    except Exception:
        pid = None

    meds: List[Dict[str, Any]] = []
    if pid is None:
        return meds

    # Intentar consultar tablas comunes para medicaciones. Si falla, devolver []
    try:
        # Intentamos nombre singular y plural por compatibilidad
        q = text(
            "SELECT medicacion_id, nombre, dosis, frecuencia FROM medicacion WHERE paciente_id = :pid ORDER BY medicacion_id DESC LIMIT 100"
        )
        res = db.execute(q, {"pid": pid}).mappings().all()
        if not res:
            # intentar tabla plural
            q2 = text(
                "SELECT medicacion_id, nombre, dosis, frecuencia FROM medicaciones WHERE paciente_id = :pid ORDER BY medicacion_id DESC LIMIT 100"
            )
            res = db.execute(q2, {"pid": pid}).mappings().all()

        for row in res:
            meds.append({
                "medicamento_id": row.get("medicacion_id") or row.get("medicamento_id"),
                "nombre": row.get("nombre"),
                "dosis": row.get("dosis"),
                "frecuencia": row.get("frecuencia"),
            })
    except Exception:
        meds = []

    return meds


def get_patient_allergies_from_model(user: User, db: Session) -> List[Dict[str, Any]]:
    """Devuelve la lista de alergias para el paciente asociado al usuario.

    Si no existe la tabla o ocurre un error, retorna lista vacía.
    """
    pid = None
    try:
        pid = int(user.fhir_patient_id) if user.fhir_patient_id else None
    except Exception:
        pid = None

    alrs: List[Dict[str, Any]] = []
    if pid is None:
        return alrs

    try:
        q = text(
            "SELECT alergia_id, agente, severidad, nota FROM alergia WHERE paciente_id = :pid ORDER BY alergia_id DESC LIMIT 100"
        )
        res = db.execute(q, {"pid": pid}).mappings().all()
        if not res:
            q2 = text(
                "SELECT alergia_id, agente, severidad, nota FROM alergias WHERE paciente_id = :pid ORDER BY alergia_id DESC LIMIT 100"
            )
            res = db.execute(q2, {"pid": pid}).mappings().all()

        for row in res:
            alrs.append({
                "alergia_id": row.get("alergia_id"),
                "agente": row.get("agente"),
                "severidad": row.get("severidad"),
                "nota": row.get("nota"),
            })
    except Exception:
        alrs = []

    return alrs


def create_patient_appointment(user: User, db: Session, fecha_hora, duracion_minutos: Optional[int], motivo: Optional[str]) -> Optional[Dict[str, Any]]:
    """Crea una nueva cita en la tabla `cita` para el paciente ligado al usuario.

    Retorna el dict de la cita creada, o None si no es posible crearla.
    """
    pid = None
    try:
        pid = int(user.fhir_patient_id) if user.fhir_patient_id else None
    except Exception:
        pid = None

    if pid is None:
        return None

    try:
        # Obtener documento_id del paciente (requerido por esquema Citus)
        q_doc = text("SELECT documento_id FROM paciente WHERE paciente_id = :pid LIMIT 1")
        doc_row = db.execute(q_doc, {"pid": pid}).mappings().first()
        if not doc_row or not doc_row.get("documento_id"):
            # No hay paciente asociado con documento_id conocido
            return None
        documento_id = doc_row["documento_id"]

        # Insertar cita incluyendo documento_id para respetar PK y constraints
        q = text(
            "INSERT INTO cita (documento_id, paciente_id, fecha_hora, duracion_minutos, estado, motivo) VALUES (:documento_id, :pid, :fecha_hora, :duracion_minutos, :estado, :motivo) RETURNING cita_id, fecha_hora, duracion_minutos, estado, motivo"
        )
        params = {
            "documento_id": documento_id,
            "pid": pid,
            "fecha_hora": fecha_hora,
            "duracion_minutos": duracion_minutos,
            # Usar estado por defecto compatible con la constraint del esquema
            "estado": "programada",
            "motivo": motivo,
        }
        row = db.execute(q, params).mappings().first()
        # Commit to persist (in case caller manages transaction)
        try:
            db.commit()
        except Exception:
            # Ignore commit errors here; caller may handle connection
            pass
        if not row:
            return None
        return {
            "cita_id": row["cita_id"],
            "fecha_hora": row["fecha_hora"].isoformat() if row["fecha_hora"] else None,
            "duracion_minutos": row["duracion_minutos"],
            "estado": row["estado"],
            "motivo": row["motivo"],
        }
    except Exception:
        return None


def update_patient_appointment(user: User, db: Session, cita_id: int, fecha_hora=None, duracion_minutos: Optional[int]=None, motivo: Optional[str]=None, estado: Optional[str]=None) -> Optional[Dict[str, Any]]:
    """Actualiza campos permitidos de una cita si pertenece al paciente.

    Retorna la cita actualizada o None si no se puede actualizar.
    """
    pid = None
    try:
        pid = int(user.fhir_patient_id) if user.fhir_patient_id else None
    except Exception:
        pid = None

    if pid is None:
        return None

    # Construir SET dinámico
    sets = []
    params = {"pid": pid, "cid": cita_id}
    if fecha_hora is not None:
        sets.append("fecha_hora = :fecha_hora")
        params["fecha_hora"] = fecha_hora
    if duracion_minutos is not None:
        sets.append("duracion_minutos = :duracion_minutos")
        params["duracion_minutos"] = duracion_minutos
    if motivo is not None:
        sets.append("motivo = :motivo")
        params["motivo"] = motivo
    if estado is not None:
        sets.append("estado = :estado")
        params["estado"] = estado

    if not sets:
        # Nothing to update
        return get_patient_appointment_by_id(user, db, cita_id)

    try:
        set_clause = ", ".join(sets)
        q = text(f"UPDATE cita SET {set_clause} WHERE paciente_id = :pid AND cita_id = :cid RETURNING cita_id, fecha_hora, duracion_minutos, estado, motivo")
        row = db.execute(q, params).mappings().first()
        try:
            db.commit()
        except Exception:
            pass
        if not row:
            return None
        return {
            "cita_id": row["cita_id"],
            "fecha_hora": row["fecha_hora"].isoformat() if row["fecha_hora"] else None,
            "duracion_minutos": row["duracion_minutos"],
            "estado": row["estado"],
            "motivo": row["motivo"],
        }
    except Exception:
        return None


def cancel_patient_appointment(user: User, db: Session, cita_id: int) -> Optional[Dict[str, Any]]:
    """Marca una cita como cancelada si pertenece al paciente.

    Retorna la cita actualizada o None si no se puede cancelar.
    """
    # Reusar update con estado 'cancelada'
    return update_patient_appointment(user, db, cita_id, estado="cancelada")
