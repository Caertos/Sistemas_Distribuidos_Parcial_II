"""
Logging and Audit Package
Sistema de logging y auditoría para la API FHIR
"""

from .audit_logger import (
    AuditLogger,
    audit_logger,
    AuditAction,
    AuditLevel,
    audit_fhir_operation,
    audit_auth_event,
    audit_system_event
)

from .structured_logger import (
    StructuredLogger,
    LogLevel,
    structured_logger,
    log_request,
    log_response,
    log_error,
    log_performance
)

from .middleware import (
    LoggingMiddleware,
    AuditMiddleware,
    RequestLoggingMiddleware
)

from .formatters import (
    JSONFormatter,
    FHIRFormatter,
    AuditFormatter
)

__all__ = [
    # Audit logging
    "AuditLogger",
    "audit_logger", 
    "AuditAction",
    "AuditLevel",
    "audit_fhir_operation",
    "audit_auth_event", 
    "audit_system_event",
    
    # Structured logging
    "StructuredLogger",
    "LogLevel",
    "structured_logger",
    "log_request",
    "log_response",
    "log_error",
    "log_performance",
    
    # Middleware
    "LoggingMiddleware",
    "AuditMiddleware", 
    "RequestLoggingMiddleware",
    
    # Formatters
    "JSONFormatter",
    "FHIRFormatter",
    "AuditFormatter"
]