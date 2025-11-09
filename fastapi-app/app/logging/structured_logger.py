"""
Structured Logger  
Sistema de logging estructurado para la aplicación FHIR
"""

import json
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Union
from uuid import uuid4
from functools import wraps
import asyncio

from fastapi import Request, Response

from app.config.settings import settings


class LogLevel(str, Enum):
    """Niveles de logging"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredLogger:
    """Logger estructurado con formato JSON"""
    
    def __init__(self, name: str = "structured", component: str = "api"):
        self.logger = logging.getLogger(name)
        self.component = component
        self.logger.setLevel(getattr(logging, settings.log_level.upper()))
        
        # Configurar handlers si no existen
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Configurar handlers de logging"""
        import os
        from logging.handlers import RotatingFileHandler
        
        # Crear directorio de logs
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Handler para archivo general
        file_handler = RotatingFileHandler(
            filename=os.path.join(log_dir, "application.log"),
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10,
            encoding="utf-8"
        )
        
        # Handler para errores
        error_handler = RotatingFileHandler(
            filename=os.path.join(log_dir, "errors.log"),
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        
        # Formatter JSON personalizado
        from .formatters import JSONFormatter
        json_formatter = JSONFormatter()
        
        file_handler.setFormatter(json_formatter)
        error_handler.setFormatter(json_formatter)
        
        # Handler de consola en desarrollo
        if settings.debug:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(json_formatter)
            self.logger.addHandler(console_handler)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
    
    def _create_log_entry(
        self,
        level: LogLevel,
        message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Crear entrada de log estructurada"""
        
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.value,
            "component": self.component,
            "message": message,
            "logger_name": self.logger.name
        }
        
        # Agregar contexto adicional
        if kwargs:
            entry.update(kwargs)
        
        return entry
    
    def debug(self, message: str, **kwargs):
        """Log nivel DEBUG"""
        entry = self._create_log_entry(LogLevel.DEBUG, message, **kwargs)
        self.logger.debug(json.dumps(entry, ensure_ascii=False))
    
    def info(self, message: str, **kwargs):
        """Log nivel INFO"""
        entry = self._create_log_entry(LogLevel.INFO, message, **kwargs)
        self.logger.info(json.dumps(entry, ensure_ascii=False))
    
    def warning(self, message: str, **kwargs):
        """Log nivel WARNING"""
        entry = self._create_log_entry(LogLevel.WARNING, message, **kwargs)
        self.logger.warning(json.dumps(entry, ensure_ascii=False))
    
    def error(self, message: str, **kwargs):
        """Log nivel ERROR"""
        entry = self._create_log_entry(LogLevel.ERROR, message, **kwargs)
        self.logger.error(json.dumps(entry, ensure_ascii=False))
    
    def critical(self, message: str, **kwargs):
        """Log nivel CRITICAL"""
        entry = self._create_log_entry(LogLevel.CRITICAL, message, **kwargs)
        self.logger.critical(json.dumps(entry, ensure_ascii=False))
    
    def log_request(
        self,
        request: Request,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ):
        """Log de request HTTP"""
        
        if not request_id:
            request_id = str(uuid4())
        
        context = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "user_id": user_id,
            "event_type": "http_request"
        }
        context.update(kwargs)
        
        self.info("HTTP Request", **context)
        return request_id
    
    def log_response(
        self,
        response: Response,
        request_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        user_id: Optional[str] = None,
        **kwargs
    ):
        """Log de response HTTP"""
        
        context = {
            "request_id": request_id,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "duration_ms": duration_ms,
            "user_id": user_id,
            "event_type": "http_response"
        }
        context.update(kwargs)
        
        if response.status_code >= 400:
            self.warning("HTTP Response", **context)
        else:
            self.info("HTTP Response", **context)
    
    def log_fhir_operation(
        self,
        operation: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        **kwargs
    ):
        """Log operación FHIR específica"""
        
        context = {
            "request_id": request_id,
            "fhir_operation": operation,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "duration_ms": duration_ms,
            "success": success,
            "event_type": "fhir_operation"
        }
        context.update(kwargs)
        
        if success:
            self.info(f"FHIR {operation} {resource_type}", **context)
        else:
            self.error(f"FHIR {operation} {resource_type} failed", **context)
    
    def log_auth_event(
        self,
        event: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        success: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs
    ):
        """Log evento de autenticación"""
        
        context = {
            "auth_event": event,
            "user_id": user_id,
            "username": username,
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "event_type": "authentication"
        }
        context.update(kwargs)
        
        if success:
            self.info(f"Auth: {event}", **context)
        else:
            self.warning(f"Auth Failed: {event}", **context)
    
    def log_database_operation(
        self,
        operation: str,
        table: Optional[str] = None,
        duration_ms: Optional[float] = None,
        affected_rows: Optional[int] = None,
        success: bool = True,
        **kwargs
    ):
        """Log operación de base de datos"""
        
        context = {
            "db_operation": operation,
            "table": table,
            "duration_ms": duration_ms,
            "affected_rows": affected_rows,
            "success": success,
            "event_type": "database"
        }
        context.update(kwargs)
        
        if success:
            self.debug(f"DB: {operation}", **context)
        else:
            self.error(f"DB Failed: {operation}", **context)
    
    def log_performance_metrics(
        self,
        metric_name: str,
        value: float,
        unit: str = "ms",
        labels: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """Log métricas de rendimiento"""
        
        context = {
            "metric_name": metric_name,
            "metric_value": value,
            "metric_unit": unit,
            "metric_labels": labels or {},
            "event_type": "performance"
        }
        context.update(kwargs)
        
        self.info(f"Metric: {metric_name} = {value}{unit}", **context)
    
    def log_error_with_traceback(
        self,
        error: Exception,
        message: str = "An error occurred",
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ):
        """Log error con traceback completo"""
        import traceback
        
        context = {
            "request_id": request_id,
            "user_id": user_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "event_type": "error"
        }
        context.update(kwargs)
        
        self.error(message, **context)


# Instancia global
structured_logger = StructuredLogger()


# Funciones de conveniencia
def log_request(
    request: Request,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs
) -> str:
    """Función de conveniencia para log de request"""
    return structured_logger.log_request(request, request_id, user_id, **kwargs)


def log_response(
    response: Response,
    request_id: Optional[str] = None,
    duration_ms: Optional[float] = None,
    user_id: Optional[str] = None,
    **kwargs
):
    """Función de conveniencia para log de response"""
    structured_logger.log_response(response, request_id, duration_ms, user_id, **kwargs)


def log_error(
    error: Exception,
    message: str = "An error occurred",
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs
):
    """Función de conveniencia para log de errores"""
    structured_logger.log_error_with_traceback(error, message, request_id, user_id, **kwargs)


def log_performance(
    metric_name: str,
    value: float,
    unit: str = "ms",
    labels: Optional[Dict[str, str]] = None,
    **kwargs
):
    """Función de conveniencia para métricas de rendimiento"""
    structured_logger.log_performance_metrics(metric_name, value, unit, labels, **kwargs)


# Decorador para logging automático de funciones
def log_function_call(
    logger: Optional[StructuredLogger] = None,
    log_args: bool = False,
    log_result: bool = False
):
    """Decorador para logging automático de llamadas a funciones"""
    
    if logger is None:
        logger = structured_logger
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            context = {
                "function": func_name,
                "event_type": "function_call"
            }
            
            if log_args:
                context["args"] = str(args)
                context["kwargs"] = str(kwargs)
            
            logger.debug(f"Calling {func_name}", **context)
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                context.update({
                    "duration_ms": duration_ms,
                    "success": True
                })
                
                if log_result and result is not None:
                    context["result"] = str(result)[:500]  # Limitar tamaño
                
                logger.debug(f"Completed {func_name}", **context)
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                context.update({
                    "duration_ms": duration_ms,
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                
                logger.error(f"Failed {func_name}", **context)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            context = {
                "function": func_name,
                "event_type": "function_call"
            }
            
            if log_args:
                context["args"] = str(args)
                context["kwargs"] = str(kwargs)
            
            logger.debug(f"Calling {func_name}", **context)
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                context.update({
                    "duration_ms": duration_ms,
                    "success": True
                })
                
                if log_result and result is not None:
                    context["result"] = str(result)[:500]
                
                logger.debug(f"Completed {func_name}", **context)
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                context.update({
                    "duration_ms": duration_ms,
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                
                logger.error(f"Failed {func_name}", **context)
                raise
        
        # Detectar si la función es async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator