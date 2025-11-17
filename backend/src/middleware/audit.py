from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import List
from starlette.responses import JSONResponse
import logging
from src.services import audit_service

logger = logging.getLogger("backend.audit")


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware para registrar accesos a recursos sensibles.

    - Registra accesos de tipo lectura (GET) a rutas bajo los prefijos
      configurados por defecto.
    - No bloquea la petición si el registro falla.
    """

    def __init__(self, app, prefixes: List[str] = None, require_header: bool = False):
        super().__init__(app)
        # rutas que queremos auditar (por defecto: patient/practitioner/admin)
        self.prefixes = prefixes or ["/api/patient", "/api/practitioner", "/api/admin", "/api/cita", "/api/encounter", "/api/encounters"]
        # if true, require presence of X-Documento-Id (or equivalent) header
        # to guarantee correct sharding/document association. If enabled and
        # header missing, middleware will return 428 Precondition Required.
        # Default can be overridden when adding middleware. We import settings
        # lazily to avoid forcing pydantic imports at module import time in tests.
        try:
            from src.config import settings as _settings

            cfg_default = getattr(_settings, "require_document_header", False)
        except Exception:
            cfg_default = False
        self.require_header = require_header or cfg_default

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # only consider configured prefixes
        do_audit = any(path.startswith(p) for p in self.prefixes)

        # Always call the route first to get its response
        response = await call_next(request)

        if not do_audit:
            return response

        # If header is required by policy, enforce presence of one of the known headers.
        if self.require_header:
            header_present = any(h in request.headers for h in ("x-documento-id", "x-document-id", "x-patient-id", "x-patientid"))
            if not header_present:
                return JSONResponse({"detail": "X-Documento-Id header is required for audited routes"}, status_code=428)

        # Only log successful GETs to avoid noisy logs
        method = request.method.upper()
        if method != "GET" or response.status_code >= 400:
            return response

        # Prepare audit data
        state_user = getattr(request.state, "user", None) or {}
        user_id = state_user.get("user_id")
        role = state_user.get("role")
        username = state_user.get("username") or None
        # Determine resource and resource_id heuristically from path
        try:
            parts = [p for p in path.split("/") if p]
            resource = parts[1] if len(parts) > 1 and parts[0] == 'api' else (parts[0] if parts else None)
            resource_id = None
            # try to find numeric segment as id
            for seg in reversed(parts):
                if seg.isdigit():
                    resource_id = seg
                    break
        except Exception:
            resource = path
            resource_id = None

        # extract small details: query string and path
        details = {"path": path, "query": dict(request.query_params)}
        ip = None
        try:
            ip = request.client.host
        except Exception:
            ip = None
        user_agent = request.headers.get("user-agent")

        # Infer documento_id from multiple possible locations:
        # - headers (X-Documento-Id, X-Document-Id, X-Patient-Id)
        # - path parameters populated by the router (request.scope['path_params'])
        # - query parameters (patient_id, documento_id, id)
        # - path heuristic (last numeric segment)
        documento_id = 0
        candidate = None

        # 1) header hints (common names)
        for h in ("x-documento-id", "x-document-id", "x-patient-id", "x-patientid"):
            v = request.headers.get(h)
            if v:
                candidate = v
                break

        # 2) path params (available after routing, we call call_next earlier)
        if candidate is None:
            try:
                path_params = request.scope.get("path_params") or {}
                for key in ("documento_id", "document_id", "patient_id", "practitioner_id", "id"):
                    if key in path_params and path_params.get(key) is not None:
                        candidate = path_params.get(key)
                        break
            except Exception:
                pass

        # 3) query params
        if candidate is None:
            for q in ("documento_id", "document_id", "patient_id", "practitioner_id", "id"):
                v = request.query_params.get(q)
                if v:
                    candidate = v
                    break

        # 4) fallback to numeric segment in path (existing heuristic)
        if candidate is None:
            try:
                if resource in ("patient", "practitioner") and resource_id is not None:
                    candidate = resource_id
                else:
                    # last numeric segment
                    for seg in reversed([p for p in path.split("/") if p]):
                        if seg.isdigit():
                            candidate = seg
                            break
            except Exception:
                candidate = None

        # Attempt to coerce to int for documento_id used by Citus distribution.
        if candidate is not None:
            try:
                documento_id = int(str(candidate))
            except Exception:
                # Candidate may be UUID or non-numeric; leave documento_id=0
                documento_id = 0

        # Attempt DB insert; create a session locally. Import SessionLocal lazily
        db = None
        try:
            from src.database import SessionLocal as _SessionLocal

            db = _SessionLocal()
            audit_service.record_access(user_id=user_id, username=username, role=role, action='read', resource=resource, resource_id=resource_id, service='api', db=db, documento_id=documento_id, details=details, ip=ip, user_agent=user_agent)
        except Exception:
            # If we couldn't obtain a DB session (missing driver, etc), still
            # call record_access with db=None so the audit_service can perform
            # a fallback write to disk. Log the original exception for tracing.
            logger.exception("Failed to obtain DB session for audit; using fallback file for path=%s user=%s", path, user_id)
            try:
                audit_service.record_access(user_id=user_id, username=username, role=role, action='read', resource=resource, resource_id=resource_id, service='api', db=None, documento_id=documento_id, details=details, ip=ip, user_agent=user_agent)
            except Exception:
                logger.exception("Fallback audit write also failed for path=%s user=%s", path, user_id)
        finally:
            try:
                if db:
                    db.close()
            except Exception:
                pass

        return response
