from datetime import datetime
import os
from typing import Optional, Any
from sqlalchemy import text


def _ensure_logs_dir() -> str:
    logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def record_export_operation(user_id: Optional[str], role: Optional[str], export_format: str, service: Optional[str] = None, db: Optional[Any] = None, note: Optional[str] = None):
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
            INSERT INTO auditoria (ts, user_id, role, action, resource, format, service, note)
            VALUES (:ts, :user_id, :role, :action, :resource, :format, :service, :note)
            """)
            db.execute(q, {
                "ts": ts,
                "user_id": user_id,
                "role": role,
                "action": "export",
                "resource": "audit_logs",
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
