from typing import Dict, Any, List
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
