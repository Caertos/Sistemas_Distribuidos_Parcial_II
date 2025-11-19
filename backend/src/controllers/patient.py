from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.models.user import User
import io
from datetime import datetime, timedelta, timezone
import logging


def _ensure_aware_utc(dt: datetime) -> Optional[datetime]:
    """Normaliza un datetime a timezone-aware en UTC.

    - Si dt es None -> retorna None
    - Si dt ya tiene tzinfo -> lo convierte a UTC
    - Si dt es naive -> asume UTC y asigna timezone.utc
    """
    if dt is None:
        return None
    try:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return dt

# Usamos reportlab para generar PDFs de forma profesional (texto, layout básico)
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
except Exception:
    canvas = None
    # A4 en puntos (72 dpi) aproximado
    A4 = (595.2755905511812, 841.8897637795277)
    mm = 2.8346456693

# Intento de importar platypus para PDF con mejor estilo (Paragraph, Table, etc.)
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
except Exception:
    SimpleDocTemplate = None


def public_user_dict_from_model(user: User) -> Dict[str, Any]:
    """Serializa un objeto User a un dict público (excluye campos sensibles)."""
    return {
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
    pid = None
    try:
        pid = int(user.fhir_patient_id) if user.fhir_patient_id else None
    except Exception:
        pid = None

    patient = public_user_dict_from_model(user)

    # Obtener citas reutilizando la función existente
    try:
        appointments = get_patient_appointments_from_model(user, db)
    except Exception:
        appointments = []

    # Obtener encuentros (encounter) en forma simplificada
    encounters: List[Dict[str, Any]] = []
    if pid is not None:
        try:
            q = text(
                "SELECT encuentro_id, fecha, motivo, diagnostico FROM encuentro WHERE paciente_id = :pid ORDER BY fecha DESC LIMIT 100"
            )
            res = db.execute(q, {"pid": pid}).mappings().all()
            for row in res:
                try:
                    encounters.append({
                        "encuentro_id": row.get("encuentro_id"),
                        "fecha": _ensure_aware_utc(row.get("fecha")).isoformat() if row.get("fecha") else None,
                        "motivo": row.get("motivo"),
                        "diagnostico": row.get("diagnostico"),
                    })
                except Exception:
                    continue
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            encounters = []

    return {
        "patient": patient,
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
                "fecha_hora": _ensure_aware_utc(row["fecha_hora"]).isoformat() if row["fecha_hora"] else None,
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
            "fecha_hora": _ensure_aware_utc(row["fecha_hora"]).isoformat() if row["fecha_hora"] else None,
            "duracion_minutos": row["duracion_minutos"],
            "estado": row["estado"],
            "motivo": row["motivo"],
        }
    except Exception:
        return None


def _fetch_patient_citas(db: Session, pid: int) -> List[Dict[str, Any]]:
    """Helper interno: obtiene fecha_hora/duracion_minutos/estado de las citas del paciente."""
    try:
        q = text(
            "SELECT cita_id, fecha_hora, duracion_minutos, estado FROM cita WHERE paciente_id = :pid"
        )
        res = db.execute(q, {"pid": pid}).mappings().all()
        rows = []
        for r in res:
            rows.append({
                "cita_id": r.get("cita_id"),
                "fecha_hora": _ensure_aware_utc(r.get("fecha_hora")),
                "duracion_minutos": r.get("duracion_minutos"),
                "estado": r.get("estado"),
            })
        return rows
    except Exception:
        return []


def is_timeslot_available(db: Session, paciente_id: int, fecha_hora: datetime, duracion_minutos: Optional[int]) -> bool:
    """Verifica solapamientos de citas para un paciente.

    Retorna True si no hay conflictos (considera citas cuyo estado != 'cancelada').
    """
    try:
        existing = _fetch_patient_citas(db, paciente_id)
    except Exception:
        return True

    # Normalize incoming datetime to timezone-aware UTC
    new_start = _ensure_aware_utc(fecha_hora)
    new_end = new_start + timedelta(minutes=(duracion_minutos or 0))

    for e in existing:
        if not e.get("fecha_hora"):
            continue
        if e.get("estado") == "cancelada":
            continue
        ex_start = e.get("fecha_hora")
        ex_dur = e.get("duracion_minutos") or 0
        ex_end = ex_start + timedelta(minutes=ex_dur)
        # Overlap if start < other_end and end > other_start
        if (new_start < ex_end) and (new_end > ex_start):
            return False
    return True


def can_cancel_appointment(db: Session, paciente_id: int, cita_id: int, min_hours_before_cancel: int = 24) -> bool:
    """Evalúa si una cita puede cancelarse según la política de ventana mínima.

    Retorna True si se permite cancelar.
    """
    try:
        q = text("SELECT fecha_hora, estado FROM cita WHERE paciente_id = :pid AND cita_id = :cid LIMIT 1")
        row = db.execute(q, {"pid": paciente_id, "cid": cita_id}).mappings().first()
        if not row:
            return False
        if row.get("estado") == "cancelada":
            return False
        fecha = _ensure_aware_utc(row.get("fecha_hora"))
        now = datetime.now(timezone.utc)
        if fecha - now < timedelta(hours=min_hours_before_cancel):
            return False
        return True
    except Exception:
        return False


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

    if pid is None:
        return []

    meds: List[Dict[str, Any]] = []

    candidates = [
        ("SELECT medicacion_id, nombre, dosis, frecuencia, inicio, fin, via, prescriptor, estado, reacciones, medicamento_id FROM medicacion WHERE paciente_id = :pid ORDER BY medicacion_id DESC LIMIT 100", 'modern'),
        ("SELECT medicacion_id, nombre, dosis, frecuencia, inicio, fin, via, prescriptor, estado, reacciones, medicamento_id FROM medicaciones WHERE paciente_id = :pid ORDER BY medicacion_id DESC LIMIT 100", 'modern'),
        ("SELECT medicacion_id, nombre, dosis, frecuencia FROM medicacion WHERE paciente_id = :pid ORDER BY medicacion_id DESC LIMIT 100", 'minimal'),
        ("SELECT medicacion_id, nombre, dosis, frecuencia FROM medicaciones WHERE paciente_id = :pid ORDER BY medicacion_id DESC LIMIT 100", 'minimal'),
        ("SELECT medicamento_id, nombre_medicamento, dosis, frecuencia, fecha_inicio, fecha_fin, via_administracion, prescriptor_id, estado, notas FROM public.medicamento WHERE paciente_id = :pid ORDER BY medicamento_id DESC LIMIT 100", 'legacy'),
    ]

    for sql, _kind in candidates:
        try:
            q = text(sql)
            res = db.execute(q, {"pid": pid}).mappings().all()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            continue

        if not res:
            continue

        for row in res:
            try:
                inicio = row.get("inicio") or row.get("fecha_inicio")
                fin = row.get("fin") or row.get("fecha_fin")
                # Normalizar prescriptor a string para cumplir con el esquema de respuesta
                pres_val = row.get("prescriptor") or row.get("prescriptor_id") or row.get("prescrito_por")
                prescriptor = None
                try:
                    if pres_val is not None:
                        prescriptor = str(pres_val)
                except Exception:
                    prescriptor = None

                med = {
                    "medicamento_id": row.get("medicacion_id") or row.get("medicamento_id"),
                    "nombre": row.get("nombre") or row.get("nombre_medicamento"),
                    "dosis": row.get("dosis"),
                    "frecuencia": row.get("frecuencia"),
                    "inicio": (_ensure_aware_utc(inicio).isoformat() if _ensure_aware_utc(inicio) else None),
                    "fin": (_ensure_aware_utc(fin).isoformat() if _ensure_aware_utc(fin) else None),
                    "via": row.get("via") or row.get("via_administracion") or row.get("vía"),
                    "prescriptor": prescriptor,
                    "estado": row.get("estado"),
                    "reacciones": row.get("reacciones") if isinstance(row.get("reacciones"), list) else ([row.get("reacciones")] if row.get("reacciones") else None),
                }
                meds.append(med)
            except Exception:
                continue

        if meds:
            return meds

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

    if pid is None:
        return []

    alrs: List[Dict[str, Any]] = []

    candidates = [
        ("SELECT alergia_id, agente, severidad, nota, onset, resolved_at, clinical_status, reacciones FROM alergia WHERE paciente_id = :pid ORDER BY alergia_id DESC LIMIT 100", 'modern'),
        ("SELECT alergia_id, agente, severidad, nota, onset, resolved_at, clinical_status, reacciones FROM alergias WHERE paciente_id = :pid ORDER BY alergia_id DESC LIMIT 100", 'modern'),
        ("SELECT alergia_id, agente, severidad, nota FROM alergia WHERE paciente_id = :pid ORDER BY alergia_id DESC LIMIT 100", 'minimal'),
        ("SELECT alergia_id, agente, severidad, nota FROM alergias WHERE paciente_id = :pid ORDER BY alergia_id DESC LIMIT 100", 'minimal'),
        ("SELECT alergia_id, descripcion_sustancia, severidad, manifestacion, fecha_inicio, estado FROM public.alergia_intolerancia WHERE paciente_id = :pid ORDER BY alergia_id DESC LIMIT 100", 'legacy'),
    ]

    for sql, _kind in candidates:
        try:
            q = text(sql)
            res = db.execute(q, {"pid": pid}).mappings().all()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            continue

        if not res:
            continue

        for row in res:
            try:
                onset = row.get("onset") or row.get("fecha") or row.get("fecha_inicio")
                alr = {
                    "alergia_id": row.get("alergia_id"),
                    "agente": row.get("agente") or row.get("descripcion_sustancia"),
                    "severidad": row.get("severidad"),
                    "nota": row.get("nota"),
                    "onset": _ensure_aware_utc(onset),
                    "resolved_at": _ensure_aware_utc(row.get("resolved_at")),
                    "clinical_status": row.get("clinical_status") or row.get("estado"),
                    "reacciones": row.get("reacciones") if isinstance(row.get("reacciones"), list) else ([row.get("reacciones")] if row.get("reacciones") else None),
                }
                alrs.append(alr)
            except Exception:
                continue

        if alrs:
            return alrs

    return alrs


def create_patient_appointment(user: User, db: Session, fecha_hora, duracion_minutos: Optional[int], motivo: Optional[str], profesional_id: Optional[int]=None) -> Optional[Dict[str, Any]]:
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

        # Normalize incoming datetime to timezone-aware UTC
        try:
            fecha_hora = _ensure_aware_utc(fecha_hora)
        except Exception:
            pass

        # Validar disponibilidad antes de insertar
        try:
            if not is_timeslot_available(db, pid, fecha_hora, duracion_minutos):
                return {"error": "conflict"}
        except Exception:
            # En caso de error en validación, continuar e intentar insertar
            pass

        # Insertar cita incluyendo documento_id para respetar PK y constraints
        q = text(
            "INSERT INTO cita (documento_id, paciente_id, profesional_id, fecha_hora, duracion_minutos, estado, motivo) VALUES (:documento_id, :pid, :profesional_id, :fecha_hora, :duracion_minutos, :estado, :motivo) RETURNING cita_id, fecha_hora, duracion_minutos, estado, motivo"
        )
        params = {
            "documento_id": documento_id,
            "pid": pid,
            "profesional_id": profesional_id,
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
        # Normalize provided datetime to UTC
        try:
            fecha_hora = _ensure_aware_utc(fecha_hora)
        except Exception:
            pass
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
    # Verificar política de cancelación (e.g., no permitir cancelaciones en menos de 24 horas)
    pid = None
    try:
        pid = int(user.fhir_patient_id) if user.fhir_patient_id else None
    except Exception:
        pid = None

    if pid is None:
        return None

    try:
        if not can_cancel_appointment(db, pid, cita_id, min_hours_before_cancel=24):
            return None
    except Exception:
        # En caso de error al validar, evitar cancelar por seguridad
        return None

    return update_patient_appointment(user, db, cita_id, estado="cancelada")


def generate_patient_summary_export(user: User, db: Session, fmt: str = "pdf"):
    """Genera una exportación del resumen del paciente.

    Retorna una tupla (payload, media_type, filename).
    - Si fmt == 'fhir' -> retorna un dict (bundle) y media_type 'application/fhir+json'
    - Si fmt == 'pdf'  -> retorna bytes y media_type 'application/pdf'
    """
    # Obtener resumen existente (reusar lógica ya implementada)
    summary = get_patient_summary_from_model(user, db)

    # Asegurar identificador mínimo
    pid = summary.get("patient", {}).get("id") or "unknown"

    if fmt and fmt.lower() == "fhir":
        # Construcción simple de Bundle FHIR con el Patient básico
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": str(pid),
                        "name": [{"text": summary.get("patient", {}).get("full_name") or ""}],
                        "telecom": [{"system": "email", "value": summary.get("patient", {}).get("email") or ""}],
                    }
                }
            ],
        }
        filename = f"patient_{pid}.json"
        return (bundle, "application/fhir+json", filename)

    # Generar PDF profesional con reportlab si está disponible
    filename = f"patient_{pid}.pdf"
    if canvas is None:
        # ReportLab no disponible: volver al placeholder binario
        pdf_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
        return (pdf_bytes, "application/pdf", filename)

    # Intentar generar PDF con platypus para un layout más rico si está disponible
    if SimpleDocTemplate is not None:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        normal = styles['Normal']
        heading = styles.get('Heading2') or ParagraphStyle('h2', parent=styles['Heading1'], fontSize=14, spaceAfter=6)
        small = ParagraphStyle('small', parent=normal, fontSize=9, textColor=colors.grey)

        story = []
        # Título
        story.append(Paragraph(f"Resumen del paciente: {summary.get('patient', {}).get('username', pid)}", heading))
        story.append(Spacer(1, 6))

        # Datos del paciente
        patient = summary.get('patient', {})
        story.append(Paragraph(f"<b>ID:</b> {patient.get('id','')}", normal))
        story.append(Paragraph(f"<b>Nombre:</b> {patient.get('full_name') or ''}", normal))
        story.append(Paragraph(f"<b>Email:</b> {patient.get('email') or ''}", normal))
        story.append(Spacer(1, 8))

        # Citas - usar tabla si hay datos
        appts = summary.get('appointments', [])
        story.append(Paragraph("Citas recientes:", styles.get('Heading3') or heading))
        if not appts:
            story.append(Paragraph("(sin citas)", small))
        else:
            data_table = [["Fecha", "Estado", "Motivo"]]
            for a in appts[:50]:
                fecha = a.get('fecha_hora') or ''
                estado = a.get('estado') or ''
                motivo = a.get('motivo') or ''
                data_table.append([fecha, estado, motivo])
            t = Table(data_table, colWidths=[70*mm, 40*mm, 60*mm])
            t.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f3f4f6')),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ]))
            story.append(t)
        story.append(Spacer(1, 8))

        # Encuentros
        encs = summary.get('encounters', [])
        story.append(Paragraph("Encuentros recientes:", styles.get('Heading3') or heading))
        if not encs:
            story.append(Paragraph("(sin encuentros)", small))
        else:
            for e in encs[:50]:
                fecha = e.get('fecha') or e.get('fecha_hora') or ''
                titulo = e.get('motivo') or e.get('diagnostico') or 'Encuentro'
                story.append(Paragraph(f"<b>{titulo}</b> — {fecha}", normal))
                nota = e.get('diagnostico') or e.get('resumen') or ''
                if nota:
                    # Paragraph maneja wrapping
                    story.append(Paragraph(nota.replace('\n', '<br/>'), normal))
                story.append(Spacer(1,4))

        # Pie
        story.append(Spacer(1, 12))
        story.append(Paragraph("Generado por el sistema - Resumen paciente", small))

        try:
            doc.build(story)
            buffer.seek(0)
            pdf_bytes = buffer.read()
            return (pdf_bytes, "application/pdf", filename)
        except Exception:
            # si falla platypus, caer al canvas simple
            pass

    # Fallback: canvas básico (compatibilidad)
    buffer = io.BytesIO()
    # Crear canvas A4
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Encabezado
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30 * mm, height - 30 * mm, f"Resumen del paciente: {summary.get('patient', {}).get('username', pid)}")

    # Datos del paciente
    c.setFont("Helvetica", 11)
    y = height - 40 * mm
    patient = summary.get("patient", {})
    lines = [
        f"ID: {patient.get('id', '')}",
        f"Nombre: {patient.get('full_name') or ''}",
        f"Email: {patient.get('email') or ''}",
    ]
    for line in lines:
        c.drawString(30 * mm, y, line)
        y -= 7 * mm

    # Citas recientes
    y -= 4 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30 * mm, y, "Citas recientes:")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    appts = summary.get("appointments", [])
    if not appts:
        c.drawString(35 * mm, y, "(sin citas)")
        y -= 6 * mm
    else:
        for a in appts[:10]:
            text = f"- {a.get('fecha_hora') or ''} | {a.get('estado') or ''} | {a.get('motivo') or ''}"
            c.drawString(35 * mm, y, text)
            y -= 6 * mm
            if y < 30 * mm:
                c.showPage()
                y = height - 30 * mm

    # Encuentros recientes
    y -= 4 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30 * mm, y, "Encuentros recientes:")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    encs = summary.get("encounters", [])
    if not encs:
        c.drawString(35 * mm, y, "(sin encuentros)")
        y -= 6 * mm
    else:
        for e in encs[:10]:
            text = f"- {e.get('fecha') or ''} | {e.get('motivo') or ''} | {e.get('diagnostico') or ''}"
            c.drawString(35 * mm, y, text)
            y -= 6 * mm
            if y < 30 * mm:
                c.showPage()
                y = height - 30 * mm

    # Pie de página
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(30 * mm, 15 * mm, "Generado por el sistema - Resumen paciente")

    c.showPage()
    c.save()
    buffer.seek(0)
    pdf_bytes = buffer.read()
    return (pdf_bytes, "application/pdf", filename)
