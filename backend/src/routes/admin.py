from fastapi import APIRouter, Depends, Request, status
from typing import List
from sqlalchemy.orm import Session
from src.database import get_db
from src.auth.roles import require_role
from src.schemas import admin as schemas
from src.controllers import admin_users

router = APIRouter()


@router.post("/users", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED, dependencies=[require_role("admin")])
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    user = admin_users.create_user(db, username=payload.username, email=payload.email, full_name=payload.full_name, password=payload.password, user_type=payload.user_type, is_superuser=payload.is_superuser)
    return user


@router.get("/users", response_model=List[schemas.UserOut], dependencies=[require_role("admin")])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return admin_users.list_users(db, skip=skip, limit=limit)


@router.get("/users/{user_id}", response_model=schemas.UserOut, dependencies=[require_role("admin")])
def get_user(user_id: str, db: Session = Depends(get_db)):
    u = admin_users.get_user(db, user_id)
    if not u:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="User not found")
    return u


@router.patch(
    "/users/{user_id}",
    response_model=schemas.UserOut,
    dependencies=[require_role("admin")],
    summary="Parcialmente actualizar un usuario",
    description="Aplica actualizaciones parciales sobre un usuario (soporta campos opcionales).",
)
@router.put(
    "/users/{user_id}",
    response_model=schemas.UserOut,
    dependencies=[require_role("admin")],
    deprecated=True,
    summary="(DEPRECATED) Reemplazar usuario completo",
    description="Ruta mantenida por compatibilidad pero marcada como obsoleta. Preferir PATCH para updates parciales.",
)
def update_user(user_id: str, payload: schemas.UserUpdate, db: Session = Depends(get_db)):
    u = admin_users.get_user(db, user_id)
    if not u:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="User not found")
    data = payload.dict(exclude_unset=True)
    u = admin_users.update_user(db, u, data)
    return u


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[require_role("admin")])
def delete_user(user_id: str, db: Session = Depends(get_db)):
    u = admin_users.get_user(db, user_id)
    if not u:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="User not found")
    admin_users.delete_user(db, u)
    return {}


@router.post("/users/{user_id}/role", response_model=schemas.UserOut, dependencies=[require_role("admin")])
def assign_role(user_id: str, payload: schemas.RoleAssign, db: Session = Depends(get_db)):
    u = admin_users.get_user(db, user_id)
    if not u:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="User not found")
    u = admin_users.assign_role(db, u, role=payload.role, is_superuser=payload.is_superuser)
    return u


# Infra, DB ops and monitoring endpoints will call services (stubbed-safe implementations).
@router.post("/infra/deploy", dependencies=[require_role("admin")])
def infra_deploy(req: schemas.ActionRequest):
    from src.services import admin_infra

    res = admin_infra.deploy_service(req.target, req.options)
    return res


@router.post("/infra/stop", dependencies=[require_role("admin")])
def infra_stop(req: schemas.ActionRequest):
    from src.services import admin_infra

    res = admin_infra.stop_service(req.target, req.options)
    return res


@router.post("/infra/rebuild", dependencies=[require_role("admin")])
def infra_rebuild(req: schemas.ActionRequest):
    from src.services import admin_infra

    res = admin_infra.rebuild_image(req.target, req.options)
    return res


@router.post("/db/backup", dependencies=[require_role("admin")])
def db_backup(req: schemas.BackupRequest):
    from src.services import admin_db

    res = admin_db.create_backup(req.name, req.include_data)
    return res


@router.post("/db/restore", dependencies=[require_role("admin")])
def db_restore(req: schemas.RestoreRequest):
    from src.services import admin_db

    res = admin_db.restore_backup(req.backup_name, req.force)
    return res


@router.post("/db/migrate", dependencies=[require_role("admin")])
def db_migrate():
    from src.services import admin_db

    res = admin_db.run_migrations()
    return res


@router.get("/monitor/metrics", dependencies=[require_role(("admin", "auditor"))])
def metrics(query: schemas.MetricQuery = None):
    from src.services import admin_monitoring

    q = query or schemas.MetricQuery()
    return admin_monitoring.get_metrics(q.since_minutes, q.metrics)


@router.get("/monitor/logs", dependencies=[require_role(("admin", "auditor"))])
def logs(service: str = None, tail: int = 200):
    from src.services import admin_monitoring

    return admin_monitoring.get_logs(service=service, tail=tail)


@router.get("/monitor/audit", dependencies=[require_role(("admin", "auditor"))])
def audit_reports():
    from src.services import admin_monitoring

    return admin_monitoring.get_audit_reports()
