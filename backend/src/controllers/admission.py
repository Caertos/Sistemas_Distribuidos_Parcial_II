from typing import Optional, Dict, Any
import json
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timezone


def _ensure_aware_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    try:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return dt


def _get_documento_for_patient(db: Session, paciente_id: int) -> Optional[int]:
    try:
        q = text("SELECT documento_id FROM paciente WHERE paciente_id = :pid LIMIT 1")
        r = db.execute(q, {"pid": paciente_id}).mappings().first()
        if not r:
            return None
        return r.get("documento_id")
    except Exception:
        return None


def create_admission(db: Session, admitted_by: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Crea una admisión y (opcionalmente) registra signos vitales iniciales.

    payload debe contener paciente_id y campos opcionales.
    Retorna dict con campos básicos de la admisión o None en error.
    """
    paciente_id = payload.get("paciente_id")
    if not paciente_id:
        return None

    documento_id = _get_documento_for_patient(db, paciente_id)
    if not documento_id:
        return None

    # Normalize datetime fields
    if payload.get("fecha_admision"):
        payload["fecha_admision"] = _ensure_aware_utc(payload.get("fecha_admision"))

    try:
        q = text(
            "INSERT INTO admision (admission_id, documento_id, paciente_id, cita_id, fecha_admision, admitido_por, motivo_consulta, prioridad, presion_arterial_sistolica, presion_arterial_diastolica, frecuencia_cardiaca, frecuencia_respiratoria, temperatura, saturacion_oxigeno, peso, altura, nivel_dolor, nivel_conciencia, sintomas_principales, notas_enfermeria, created_at) VALUES (generar_codigo_admision(), :documento_id, :pid, :cita_id, :fecha_admision, :admitido_por, :motivo_consulta, :prioridad, :pas, :pad, :fc, :fr, :temp, :sat, :peso, :altura, :nivel_dolor, :nivel_conciencia, :sintomas, :notas, NOW()) RETURNING admission_id, fecha_admision, estado_admision, prioridad, motivo_consulta"
        )
        params = {
            "documento_id": documento_id,
            "pid": paciente_id,
            "cita_id": payload.get("cita_id"),
            "fecha_admision": payload.get("fecha_admision"),
            "admitido_por": admitted_by,
            "motivo_consulta": payload.get("motivo_consulta"),
            "prioridad": payload.get("prioridad") or "normal",
            "pas": payload.get("presion_arterial_sistolica"),
            "pad": payload.get("presion_arterial_diastolica"),
            "fc": payload.get("frecuencia_cardiaca"),
            "fr": payload.get("frecuencia_respiratoria"),
            "temp": payload.get("temperatura"),
            "sat": payload.get("saturacion_oxigeno"),
            "peso": payload.get("peso"),
            "altura": payload.get("altura"),
            "nivel_dolor": payload.get("nivel_dolor"),
            "nivel_conciencia": payload.get("nivel_conciencia"),
            "sintomas": payload.get("sintomas_principales"),
            "notas": payload.get("notas_enfermeria"),
        }
        row = db.execute(q, params).mappings().first()
        try:
            db.commit()
        except Exception:
            pass
        if not row:
            return None

        admission_id = row.get("admission_id")

        # If the admission is linked to a cita, mark the cita as admitted (so doctors won't see it as pending)
        try:
            if payload.get("cita_id"):
                q_update_cita = text("UPDATE cita SET admission_id = :aid, estado_admision = 'admitida', fecha_admision = :fecha_admision WHERE documento_id = :did AND cita_id = :cid RETURNING cita_id")
                db.execute(q_update_cita, {"aid": admission_id, "fecha_admision": row.get("fecha_admision"), "did": documento_id, "cid": payload.get("cita_id")})
                try:
                    db.commit()
                except Exception:
                    pass
        except Exception:
            # Non-fatal: continue
            pass

        return {
            "admission_id": admission_id,
            "paciente_id": paciente_id,
            "fecha_admision": row.get("fecha_admision"),
            "estado_admision": row.get("estado_admision"),
            "prioridad": row.get("prioridad"),
            "motivo_consulta": row.get("motivo_consulta"),
        }
    except Exception:
        return None


def get_admission_by_id(db: Session, admission_id: str) -> Optional[Dict[str, Any]]:
    try:
        q = text("SELECT * FROM admision WHERE admission_id = :aid LIMIT 1")
        row = db.execute(q, {"aid": admission_id}).mappings().first()
        if not row:
            return None
        # Convert dates to ISO strings where applicable
        out = dict(row)
        if out.get("fecha_admision"):
            try:
                out["fecha_admision"] = _ensure_aware_utc(out.get("fecha_admision")).isoformat()
            except Exception:
                pass
        return out
    except Exception:
        return None



def mark_admitted(db: Session, admission_id: str, admitted_by: str) -> Optional[Dict[str, Any]]:
    """Marca una admisión como 'admitida' y actualiza la cita relacionada si existe."""
    try:
        # obtener admision
        q = text("SELECT documento_id, paciente_id, cita_id, fecha_admision FROM admision WHERE admission_id = :aid LIMIT 1")
        a = db.execute(q, {"aid": admission_id}).mappings().first()
        if not a:
            return None
        did = a.get("documento_id")
        # actualizar admision
        q2 = text("UPDATE admision SET estado_admision = 'admitida', admitido_por = :admitido_por, updated_at = NOW() WHERE admission_id = :aid AND documento_id = :did RETURNING admission_id, estado_admision, fecha_admision")
        r = db.execute(q2, {"admitido_por": admitted_by, "aid": admission_id, "did": did}).mappings().first()
        try:
            db.commit()
        except Exception:
            pass
        if not r:
            return None

        # Si existe cita vinculada, marcarla como admitida
        try:
            if a.get("cita_id"):
                q3 = text("UPDATE cita SET estado_admision = 'admitida', admission_id = :aid, admitido_por = :admitido_por, fecha_admision = :fecha_admision WHERE documento_id = :did AND cita_id = :cid RETURNING cita_id")
                db.execute(q3, {"aid": admission_id, "admitido_por": admitted_by, "fecha_admision": r.get("fecha_admision"), "did": did, "cid": a.get("cita_id")})
                try:
                    db.commit()
                except Exception:
                    pass
        except Exception:
            pass

        return dict(r)
    except Exception:
        return None


def mark_discharged(db: Session, admission_id: str, discharged_by: str, notas: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Marca una admisión como 'atendida' (alta) y registra notas si se proporcionan."""
    try:
        q = text("SELECT documento_id FROM admision WHERE admission_id = :aid LIMIT 1")
        a = db.execute(q, {"aid": admission_id}).mappings().first()
        if not a:
            return None
        did = a.get("documento_id")
        q2 = text("UPDATE admision SET estado_admision = 'atendida', updated_at = NOW(), observaciones = COALESCE(observaciones, '') || CHR(10) || :notas WHERE admission_id = :aid AND documento_id = :did RETURNING admission_id, estado_admision")
        r = db.execute(q2, {"notas": notas or "", "aid": admission_id, "did": did}).mappings().first()
        try:
            db.commit()
        except Exception:
            pass
        if not r:
            return None
        return dict(r)
    except Exception:
        return None


def refer_patient(db: Session, admission_id: str, referred_by: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Crea una tarea de derivación para un paciente y deja registro en admisión."""
    try:
        # obtener admision para documento_id y paciente
        q = text("SELECT documento_id, paciente_id FROM admision WHERE admission_id = :aid LIMIT 1")
        a = db.execute(q, {"aid": admission_id}).mappings().first()
        if not a:
            return None
        did = a.get("documento_id")
        pid = a.get("paciente_id")

        entrada = {"motivo": payload.get("motivo"), "destino": payload.get("destino"), "notas": payload.get("notas"), "referido_por": referred_by}
        q2 = text("INSERT INTO tarea (documento_id, paciente_id, titulo, descripcion, estado, tipo_tarea, entrada, created_at) VALUES (:did, :pid, :titulo, :desc, 'solicitada', 'derivacion', :entrada::jsonb, NOW()) RETURNING tarea_id, estado")
        r = db.execute(q2, {"did": did, "pid": pid, "titulo": f"Derivación {admission_id}", "desc": payload.get("notas") or payload.get("motivo") or "Derivación", "entrada": json.dumps(entrada)})
        try:
            db.commit()
        except Exception:
            pass
        row = r.mappings().first()
        if not row:
            return None
        # Opcional: agregar nota en admision.observaciones
        try:
            q3 = text("UPDATE admision SET observaciones = COALESCE(observaciones, '') || CHR(10) || :nota, updated_at = NOW() WHERE admission_id = :aid AND documento_id = :did")
            db.execute(q3, {"nota": f"Derivación creada: {row.get('tarea_id')}", "aid": admission_id, "did": did})
            try:
                db.commit()
            except Exception:
                pass
        except Exception:
            pass
        return dict(row)
    except Exception:
        return None


def create_vital_sign(db: Session, admitted_by: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    paciente_id = payload.get("paciente_id")
    if not paciente_id:
        return None
    documento_id = _get_documento_for_patient(db, paciente_id)
    if not documento_id:
        return None

    fecha = payload.get("fecha")
    if fecha:
        fecha = _ensure_aware_utc(fecha)

    try:
        q = text(
            "INSERT INTO signos_vitales (documento_id, paciente_id, encuentro_id, fecha, presion_sistolica, presion_diastolica, frecuencia_cardiaca, frecuencia_respiratoria, temperatura, saturacion_oxigeno, peso, talla, created_at) VALUES (:documento_id, :pid, :enc, :fecha, :ps, :pd, :fc, :fr, :temp, :sat, :peso, :talla, NOW()) RETURNING signo_id, fecha"
        )
        params = {
            "documento_id": documento_id,
            "pid": paciente_id,
            "enc": payload.get("encuentro_id") or payload.get("encounter_id"),
            "fecha": fecha,
            "ps": payload.get("presion_sistolica") or payload.get("presion_arterial_sistolica"),
            "pd": payload.get("presion_diastolica") or payload.get("presion_arterial_diastolica"),
            "fc": payload.get("frecuencia_cardiaca"),
            "fr": payload.get("frecuencia_respiratoria"),
            "temp": payload.get("temperatura") or payload.get("temperature"),
            "sat": payload.get("saturacion_oxigeno"),
            "peso": payload.get("peso"),
            "talla": payload.get("talla") or payload.get("altura"),
        }
        row = db.execute(q, params).mappings().first()
        try:
            db.commit()
        except Exception:
            pass
        if not row:
            return None
        return {"signo_id": row.get("signo_id"), "fecha": row.get("fecha")}
    except Exception:
        return None


def add_nursing_note(db: Session, admitted_by: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    paciente_id = payload.get("paciente_id")
    nota = payload.get("nota")
    admission_id = payload.get("admission_id")
    if not paciente_id or not nota:
        return None
    documento_id = _get_documento_for_patient(db, paciente_id)
    if not documento_id:
        return None

    try:
        if admission_id:
            # Append note to admision.notas_enfermeria
            q = text("UPDATE admision SET notas_enfermeria = COALESCE(notas_enfermeria, '') || CHR(10) || :nota, updated_at = NOW() WHERE admission_id = :aid AND documento_id = :did RETURNING admission_id, notas_enfermeria")
            r = db.execute(q, {"nota": nota, "aid": admission_id, "did": documento_id}).mappings().first()
            try:
                db.commit()
            except Exception:
                pass
            if not r:
                return None
            return {"admission_id": r.get("admission_id"), "notas_enfermeria": r.get("notas_enfermeria")}
        else:
            # Create a 'cuidado' record as a nursing note (fallback)
            q2 = text("INSERT INTO cuidado (documento_id, paciente_id, tipo_cuidado, descripcion, fecha, created_at) VALUES (:did, :pid, :tipo, :desc, NOW(), NOW()) RETURNING cuidado_id")
            r2 = db.execute(q2, {"did": documento_id, "pid": paciente_id, "tipo": "nota_enfermeria", "desc": nota}).mappings().first()
            try:
                db.commit()
            except Exception:
                pass
            if not r2:
                return None
            return {"cuidado_id": r2.get("cuidado_id")}
    except Exception:
        return None


def administer_medication(db: Session, administered_by: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Registra una administración de medicamento como un registro de `cuidado`.

    payload debe incluir paciente_id, nombre_medicamento, dosis y notas opcionales.
    """
    paciente_id = payload.get("paciente_id")
    nombre = payload.get("nombre_medicamento") or payload.get("nombre")
    dosis = payload.get("dosis")
    if not paciente_id or not nombre:
        return None
    documento_id = _get_documento_for_patient(db, paciente_id)
    if not documento_id:
        return None

    descripcion = f"Administración: {nombre} {dosis or ''}. Notes: {payload.get('notas') or ''}"
    try:
        q = text("INSERT INTO cuidado (documento_id, paciente_id, tipo_cuidado, descripcion, fecha, profesional_id, created_at) VALUES (:did, :pid, :tipo, :desc, NOW(), NULL, NOW()) RETURNING cuidado_id")
        r = db.execute(q, {"did": documento_id, "pid": paciente_id, "tipo": "administracion_medicamento", "desc": descripcion}).mappings().first()
        try:
            db.commit()
        except Exception:
            pass
        if not r:
            return None
        return {"cuidado_id": r.get("cuidado_id"), "descripcion": descripcion}
    except Exception:
        return None


def update_demographics(db: Session, paciente_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    documento_id = _get_documento_for_patient(db, paciente_id)
    if not documento_id:
        return None
    # Build dynamic SET
    sets = []
    params = {"pid": paciente_id, "did": documento_id}
    if payload.get("nombre") is not None:
        sets.append("nombre = :nombre")
        params["nombre"] = payload.get("nombre")
    if payload.get("apellido") is not None:
        sets.append("apellido = :apellido")
        params["apellido"] = payload.get("apellido")
    if payload.get("sexo") is not None:
        sets.append("sexo = :sexo")
        params["sexo"] = payload.get("sexo")
    if payload.get("fecha_nacimiento") is not None:
        # ensure datetime -> date or keep as is
        params["fecha_nacimiento"] = payload.get("fecha_nacimiento")
        sets.append("fecha_nacimiento = :fecha_nacimiento")
    if payload.get("contacto") is not None:
        sets.append("contacto = :contacto")
        params["contacto"] = payload.get("contacto")
    if payload.get("ciudad") is not None:
        sets.append("ciudad = :ciudad")
        params["ciudad"] = payload.get("ciudad")

    if not sets:
        # nothing to update
        return None

    try:
        set_clause = ", ".join(sets)
        q = text(f"UPDATE paciente SET {set_clause} WHERE documento_id = :did AND paciente_id = :pid RETURNING paciente_id, documento_id, nombre, apellido, sexo, fecha_nacimiento, contacto, ciudad")
        row = db.execute(q, params).mappings().first()
        try:
            db.commit()
        except Exception:
            pass
        if not row:
            return None
        out = dict(row)
        return out
    except Exception:
        return None
