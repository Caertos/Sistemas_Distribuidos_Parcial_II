"""
Logging Middleware
Middleware para logging automático de requests/responses y auditoría
"""

import time
import json
from uuid import uuid4
from typing import Callable, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import StreamingResponse

from app.logging.structured_logger import structured_logger
from app.logging.audit_logger import audit_logger, AuditAction, AuditLevel
from app.config.settings import settings


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging de requests y responses HTTP"""
    
    def __init__(self, app: FastAPI, log_requests: bool = True, log_responses: bool = True):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Procesar request y response con logging"""
        
        # Generar ID único para el request
        request_id = str(uuid4())
        request.state.request_id = request_id
        
        # Obtener información del usuario si está disponible
        user_id = None
        username = None
        if hasattr(request.state, "user"):
            user = request.state.user
            user_id = str(user.id) if user else None
            username = user.username if user else None
        
        start_time = time.time()
        
        # Log del request
        if self.log_requests:
            await self._log_request(request, request_id, user_id, username)
        
        # Procesar request
        try:
            response = await call_next(request)
            
            # Calcular duración
            duration_ms = (time.time() - start_time) * 1000
            
            # Log del response
            if self.log_responses:
                await self._log_response(request, response, request_id, duration_ms, user_id, username)
            
            return response
            
        except Exception as e:
            # Log de error
            duration_ms = (time.time() - start_time) * 1000
            await self._log_error(request, e, request_id, duration_ms, user_id, username)
            raise
    
    async def _log_request(
        self, 
        request: Request, 
        request_id: str, 
        user_id: Optional[str], 
        username: Optional[str]
    ):
        """Log del request HTTP"""
        
        # Filtrar headers sensibles
        headers = dict(request.headers)
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[REDACTED]"
        
        # Información del request
        request_info = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": headers,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "user_id": user_id,
            "username": username,
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length")
        }
        
        structured_logger.info("HTTP Request", **request_info)
    
    async def _log_response(
        self, 
        request: Request, 
        response: Response, 
        request_id: str, 
        duration_ms: float,
        user_id: Optional[str], 
        username: Optional[str]
    ):
        """Log del response HTTP"""
        
        # Información del response
        response_info = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "user_id": user_id,
            "username": username,
            "response_size": response.headers.get("content-length"),
            "content_type": response.headers.get("content-type")
        }
        
        # Determinar nivel de log basado en status code
        if response.status_code >= 500:
            structured_logger.error("HTTP Response", **response_info)
        elif response.status_code >= 400:
            structured_logger.warning("HTTP Response", **response_info)
        else:
            structured_logger.info("HTTP Response", **response_info)
    
    async def _log_error(
        self, 
        request: Request, 
        error: Exception, 
        request_id: str, 
        duration_ms: float,
        user_id: Optional[str], 
        username: Optional[str]
    ):
        """Log de error en el request"""
        
        error_info = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "duration_ms": round(duration_ms, 2),
            "user_id": user_id,
            "username": username
        }
        
        structured_logger.log_error_with_traceback(
            error, 
            "Request processing failed", 
            **error_info
        )


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware para auditoría automática de operaciones FHIR"""
    
    def __init__(self, app: FastAPI, audit_all: bool = False):
        super().__init__(app)
        self.audit_all = audit_all
        
        # Endpoints que requieren auditoría
        self.audit_endpoints = {
            # FHIR endpoints
            "/fhir/R4/Patient": "Patient",
            "/fhir/R4/Practitioner": "Practitioner", 
            "/fhir/R4/Observation": "Observation",
            "/fhir/R4/Condition": "Condition",
            "/fhir/R4/MedicationRequest": "MedicationRequest",
            "/fhir/R4/DiagnosticReport": "DiagnosticReport",
            
            # Auth endpoints
            "/auth/login": "Authentication",
            "/auth/logout": "Authentication",
            "/auth/register": "Authentication",
            "/auth/change-password": "Authentication"
        }
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Procesar request con auditoría"""
        
        # Verificar si requiere auditoría
        should_audit = self._should_audit_request(request)
        
        if not should_audit:
            return await call_next(request)
        
        # Información del usuario
        user_id = None
        username = None
        user_roles = None
        
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            user_id = str(user.id)
            username = user.username
            # Obtener roles si están disponibles
            if hasattr(user, 'roles'):
                user_roles = [role.name for role in user.roles]
        
        # Determinar tipo de recurso y acción
        resource_type = self._get_resource_type(request)
        action = self._get_audit_action(request)
        resource_id = self._extract_resource_id(request)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Auditar operación exitosa
            await audit_logger.log_fhir_operation(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                username=username,
                request=request,
                response=response,
                duration_ms=duration_ms,
                message=f"Successful {action.value} operation"
            )
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Auditar operación fallida
            await audit_logger.log_fhir_operation(
                action=AuditAction.ERROR,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                username=username,
                request=request,
                duration_ms=duration_ms,
                message=f"Failed {action.value} operation: {str(e)}",
                metadata={"original_action": action.value, "error": str(e)}
            )
            
            raise
    
    def _should_audit_request(self, request: Request) -> bool:
        """Determinar si el request requiere auditoría"""
        
        if self.audit_all:
            return True
        
        path = request.url.path
        
        # Verificar endpoints específicos
        for endpoint_prefix, _ in self.audit_endpoints.items():
            if path.startswith(endpoint_prefix):
                return True
        
        return False
    
    def _get_resource_type(self, request: Request) -> str:
        """Extraer tipo de recurso del path"""
        
        path = request.url.path
        
        # Verificar endpoints FHIR
        for endpoint_prefix, resource_type in self.audit_endpoints.items():
            if path.startswith(endpoint_prefix):
                return resource_type
        
        # Para paths FHIR, extraer del path
        if "/fhir/R4/" in path:
            parts = path.split("/")
            if len(parts) >= 4:
                return parts[3]  # /fhir/R4/ResourceType/...
        
        return "Unknown"
    
    def _get_audit_action(self, request: Request) -> AuditAction:
        """Determinar acción de auditoría basada en método HTTP"""
        
        method = request.method.upper()
        path = request.url.path
        
        # Casos especiales
        if "/auth/login" in path:
            return AuditAction.LOGIN
        elif "/auth/logout" in path:
            return AuditAction.LOGOUT
        elif "/auth/register" in path:
            return AuditAction.CREATE
        elif "/auth/change-password" in path:
            return AuditAction.PASSWORD_CHANGE
        
        # Mapeo por método HTTP
        action_map = {
            "GET": AuditAction.READ,
            "POST": AuditAction.CREATE,
            "PUT": AuditAction.UPDATE,
            "PATCH": AuditAction.UPDATE,
            "DELETE": AuditAction.DELETE
        }
        
        return action_map.get(method, AuditAction.READ)
    
    def _extract_resource_id(self, request: Request) -> Optional[str]:
        """Extraer ID del recurso del path si está disponible"""
        
        path = request.url.path
        parts = path.split("/")
        
        # Para paths FHIR: /fhir/R4/ResourceType/id
        if "/fhir/R4/" in path and len(parts) >= 5:
            return parts[4]
        
        return None


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware combinado para logging completo"""
    
    def __init__(
        self, 
        app: FastAPI, 
        enable_request_logging: bool = True,
        enable_audit_logging: bool = True,
        enable_performance_logging: bool = True
    ):
        super().__init__(app)
        self.enable_request_logging = enable_request_logging
        self.enable_audit_logging = enable_audit_logging
        self.enable_performance_logging = enable_performance_logging
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Dispatcher principal con logging completo"""
        
        # Generar request ID
        request_id = str(uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        try:
            # Request logging
            if self.enable_request_logging:
                structured_logger.log_request(request, request_id)
            
            # Procesar request
            response = await call_next(request)
            
            # Performance logging
            duration_ms = (time.time() - start_time) * 1000
            
            if self.enable_performance_logging:
                structured_logger.log_performance_metrics(
                    metric_name="http_request_duration",
                    value=duration_ms,
                    unit="ms",
                    labels={
                        "method": request.method,
                        "endpoint": request.url.path,
                        "status_code": str(response.status_code)
                    }
                )
            
            # Response logging
            if self.enable_request_logging:
                structured_logger.log_response(response, request_id, duration_ms)
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Error logging
            structured_logger.log_error_with_traceback(
                e, 
                "Request processing failed",
                request_id=request_id
            )
            
            raise


# Context manager para operaciones con logging automático
@asynccontextmanager
async def logged_operation(
    operation_name: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Context manager para logging automático de operaciones"""
    
    start_time = time.time()
    
    context = {
        "operation": operation_name,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "user_id": user_id,
        "metadata": metadata or {}
    }
    
    structured_logger.info(f"Starting {operation_name}", **context)
    
    try:
        yield context
        
        # Operación exitosa
        duration_ms = (time.time() - start_time) * 1000
        context["duration_ms"] = duration_ms
        context["success"] = True
        
        structured_logger.info(f"Completed {operation_name}", **context)
        
    except Exception as e:
        # Operación fallida
        duration_ms = (time.time() - start_time) * 1000
        context.update({
            "duration_ms": duration_ms,
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })
        
        structured_logger.error(f"Failed {operation_name}", **context)
        raise