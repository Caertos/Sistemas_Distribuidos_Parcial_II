from fastapi import APIRouter, Response, status, Depends, Request
from typing import Optional
from src.auth.roles import require_admin
from src.auth.permissions import require_auditor_read_only
from src.controllers import auditor as auditor_ctrl
from src.services import audit_service
from src.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/logs", dependencies=[Depends(require_auditor_read_only)])
def list_audit_logs(service: Optional[str] = None, tail: int = 200, db: Session = Depends(get_db)):
    """Listar logs de auditoría (acceso: admin y auditor en modo lectura)."""
    return auditor_ctrl.list_logs(db=db, service=service, tail=tail)


@router.get("/logs/{log_id}", dependencies=[Depends(require_auditor_read_only)])
def get_audit_log(log_id: int, db: Session = Depends(get_db)):
    """Obtener detalle de un log de auditoría."""
    return auditor_ctrl.get_log(db=db, log_id=log_id)


@router.get("/export", dependencies=[require_admin])
def export_audit(request: Request, format: str = "csv", service: Optional[str] = None, db: Session = Depends(get_db)):
    """Exportar logs de auditoría en CSV o PDF. (stub)

    Nota: la exportación está reservada a `admin`. Registramos la operación en
    la tabla de auditoría si la DB está disponible, y en fallback escribimos un
    fichero CSV en `logs/audit_exports.csv`.
    """
    # obtener identidad del request (require_admin garantiza admin)
    state_user = getattr(request.state, "user", None) or {}
    user_id = state_user.get("user_id")
    role = state_user.get("role")

    # generar el contenido de export
    content = auditor_ctrl.export_audit(format=format, service=service)

    # registrar la operación (no bloquear la respuesta en caso de error)
    try:
        audit_service.record_export_operation(user_id=user_id, role=role, export_format=format, service=service, db=db)
    except Exception:
        # no romper la exportación si falla el registro
        pass

    if format == "csv":
        return Response(content=content, media_type="text/csv")
    if format == "pdf":
        return Response(content=content, media_type="application/pdf")
    return Response(status_code=status.HTTP_400_BAD_REQUEST)
