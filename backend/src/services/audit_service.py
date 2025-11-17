from datetime import datetime
import os
import json
from typing import Optional, Any
from sqlalchemy import text


def _ensure_logs_dir() -> str:
    logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def record_export_operation(user_id: Optional[str], role: Optional[str], export_format: str, service: Optional[str] = None, db: Optional[Any] = None, note: Optional[str] = None, documento_id: Optional[int] = 0):
    """Registra una operación de exportación en fallback local y, si hay DB, intenta insert en tabla de auditoría.

    - user_id, role: identidad del solicitante
    - export_format: 'csv' o 'pdf'
    - service: origen/área (p.ej. 'api')
    - db: sesión SQLAlchemy opcional para intentar un INSERT
    - note: texto libre
    """
    ts = datetime.utcnow().isoformat() + "Z"

    # Intentar inserción en DB si se proporciona una sesión
    if db is not None:
        try:
            # Intentamos insertar en una tabla `auditoria` si existe; la consulta es defensiva
            q = text("""
            INSERT INTO auditoria (documento_id, ts, user_id, role, action, resource, resource_id, format, service, note)
            VALUES (:documento_id, :ts, :user_id, :role, :action, :resource, :resource_id, :format, :service, :note)
            """)
            db.execute(q, {
                "documento_id": documento_id or 0,
                "ts": ts,
                "user_id": user_id,
                "role": role,
                "action": "export",
                "resource": "audit_logs",
                "resource_id": None,
                "format": export_format,
                "service": service,
                "note": note,
            })
            try:
                db.commit()
            except Exception:
                # commit puede fallar si la tabla no existe; ignorar y seguir con el fallback
                pass
        except Exception:
            # No hacemos fallar la request por el logging; caemos al fallback local
            pass

    # Fallback local: append CSV
    logs_dir = _ensure_logs_dir()
    path = os.path.join(logs_dir, "audit_exports.csv")
    header = "ts,user_id,role,action,resource,format,service,note\n"
    line = f"{ts},{user_id or ''},{role or ''},export,audit_logs,{export_format},{service or ''},{(note or '').replace(',', ';')}\n"
    try:
        need_header = not os.path.exists(path)
        with open(path, "a") as fh:
            if need_header:
                fh.write(header)
            fh.write(line)
    except Exception:
        # No rompemos la ejecución si falla escribir el fallback
        pass


def record_access(user_id: Optional[str], username: Optional[str], role: Optional[str], action: str, resource: Optional[str], resource_id: Optional[str] = None, service: Optional[str] = None, db: Optional[Any] = None, documento_id: Optional[int] = 0, details: Optional[dict] = None, ip: Optional[str] = None, user_agent: Optional[str] = None):
    """Registra un acceso / operación simple en la tabla `auditoria`.

    No eleva excepciones si falla; intenta insertar en DB si se pasa `db`,
    o crea un fallback en `logs/audit_exports.csv`.
    """
    ts = datetime.utcnow().isoformat() + "Z"
    details = details or {}

    if db is not None:
        try:
            q = text("""
            INSERT INTO auditoria (documento_id, ts, user_id, username, role, action, resource, resource_id, details, format, service, ip, user_agent, note)
            VALUES (:documento_id, :ts, :user_id, :username, :role, :action, :resource, :resource_id, :details::jsonb, NULL, :service, :ip, :user_agent, NULL)
            """)
            db.execute(q, {
                "documento_id": documento_id or 0,
                "ts": ts,
                "user_id": user_id,
                "username": username,
                "role": role,
                "action": action,
                "resource": resource,
                "resource_id": resource_id,
                "details": json.dumps(details),
                "service": service,
                "ip": ip,
                "user_agent": user_agent,
            })
            try:
                db.commit()
            except Exception:
                pass
        except Exception:
            # ignore DB errors and fallback to file
            pass

    # fallback append to CSV-like file
    try:
        logs_dir = _ensure_logs_dir()
        path = os.path.join(logs_dir, "audit_access.csv")
        header = "ts,user_id,username,role,action,resource,resource_id,service,ip,user_agent,details\n"
        line = f"{ts},{user_id or ''},{username or ''},{role or ''},{action or ''},{resource or ''},{(resource_id or '').replace(',', ';')},{service or ''},{ip or ''},{(user_agent or '').replace(',', ';')},{json.dumps(details).replace(',', ';')}\n"
        need_header = not os.path.exists(path)
        with open(path, "a") as fh:
            if need_header:
                fh.write(header)
            fh.write(line)
    except Exception:
        pass

