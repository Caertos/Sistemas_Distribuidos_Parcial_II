from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text


def list_logs(db: Optional[Session] = None, service: Optional[str] = None, tail: int = 200) -> List[Dict[str, Any]]:
    """Obtener logs desde la tabla `auditoria` distribuida por `documento_id`.

    Si la DB no está disponible o la tabla no existe, devuelve un fallback
    estático (para entornos de desarrollo).
    """
    if db is not None:
        try:
            if service:
                q = text("SELECT id, documento_id, ts AS when, user_id AS who, username, role, action, resource, resource_id, details, format, service, note FROM auditoria WHERE service = :service ORDER BY ts DESC LIMIT :limit")
                rows = db.execute(q, {"service": service, "limit": tail}).mappings().all()
            else:
                q = text("SELECT id, documento_id, ts AS when, user_id AS who, username, role, action, resource, resource_id, details, format, service, note FROM auditoria ORDER BY ts DESC LIMIT :limit")
                rows = db.execute(q, {"limit": tail}).mappings().all()
            return [dict(r) for r in rows]
        except Exception:
            # fallback
            pass

    # fallback
    sample = [
        {"id": 1, "service": service or "api", "message": "User login", "who": "user:123", "when": "2025-11-17T10:00:00Z"},
        {"id": 2, "service": service or "api", "message": "Accessed patient record", "who": "user:auditor1", "when": "2025-11-17T10:05:00Z"},
    ]
    return sample[:tail]


def get_log(db: Optional[Session] = None, log_id: int = 0) -> Dict[str, Any]:
    if db is not None:
        try:
            q = text("SELECT id, documento_id, ts AS when, user_id AS who, username, role, action, resource, resource_id, details, format, service, note FROM auditoria WHERE id = :id LIMIT 1")
            r = db.execute(q, {"id": log_id}).mappings().first()
            if r:
                return dict(r)
        except Exception:
            pass

    # fallback
    if log_id == 1:
        return {"id": 1, "service": "api", "message": "User login", "who": "user:123", "when": "2025-11-17T10:00:00Z"}
    if log_id == 2:
        return {"id": 2, "service": "api", "message": "Accessed patient record", "who": "user:auditor1", "when": "2025-11-17T10:05:00Z"}
    raise HTTPException(status_code=404, detail="Log not found")


def export_audit(db: Optional[Session] = None, format: str = "csv", service: Optional[str] = None, limit: int = 1000) -> bytes:
    rows = []
    if db is not None:
        try:
            if service:
                q = text("SELECT id, documento_id, ts AS when, user_id AS who, username, role, action, resource, resource_id, details, format, service, note FROM auditoria WHERE service = :service ORDER BY ts DESC LIMIT :limit")
                rows = db.execute(q, {"service": service, "limit": limit}).mappings().all()
            else:
                q = text("SELECT id, documento_id, ts AS when, user_id AS who, username, role, action, resource, resource_id, details, format, service, note FROM auditoria ORDER BY ts DESC LIMIT :limit")
                rows = db.execute(q, {"limit": limit}).mappings().all()
        except Exception:
            rows = []

    if not rows:
        rows = list_logs(None, service=service, tail=min(100, limit))

    if format == "csv":
        header = ["id", "documento_id", "when", "who", "username", "role", "action", "resource", "resource_id", "format", "service", "note"]
        csv = ",".join(header) + "\n"
        for r in rows:
            values = [str(r.get(k, "")) for k in header]
            values = [v.replace(",", ";") for v in values]
            csv += ",".join(values) + "\n"
        return csv.encode("utf-8")

    if format == "pdf":
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            import io

            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=letter)
            y = 750
            line_height = 12
            c.setFont("Helvetica", 10)
            c.drawString(30, y + 20, "Audit export")
            for r in rows:
                line = f"{r.get('id')} {r.get('when')} {r.get('who')} {r.get('action')} {r.get('resource')}"
                c.drawString(30, y, line)
                y -= line_height
                if y < 40:
                    c.showPage()
                    y = 750
            c.save()
            buf.seek(0)
            return buf.read()
        except Exception:
            return b"%PDF-1.4\n% Fake PDF content\n"

    raise HTTPException(status_code=400, detail="Unsupported format")
