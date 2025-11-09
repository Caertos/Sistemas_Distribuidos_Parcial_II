"""
Audit Logger
Sistema de auditoría para operaciones FHIR y eventos de seguridad
"""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, asdict
from uuid import uuid4
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request, Response

from app.config.settings import settings
from app.config.database import get_async_session


class AuditAction(str, Enum):
    """Tipos de acciones auditables"""
    # FHIR Operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"
    BATCH = "batch"
    TRANSACTION = "transaction"
    
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"
    
    # Authorization
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHECK = "permission_check"
    
    # System Events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIG_CHANGE = "config_change"
    ERROR = "error"
    WARNING = "warning"


class AuditLevel(str, Enum):
    """Niveles de auditoría"""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"
    SECURITY = "security"


@dataclass
class AuditEvent:
    """Evento de auditoría estructurado"""
    
    # Identificadores únicos
    event_id: str
    timestamp: datetime
    
    # Acción y nivel
    action: AuditAction
    level: AuditLevel
    
    # Contexto del usuario
    user_id: Optional[str] = None
    username: Optional[str] = None
    user_roles: Optional[list] = None
    
    # Contexto de la request
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Contexto FHIR
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_version: Optional[str] = None
    endpoint: Optional[str] = None
    http_method: Optional[str] = None
    
    # Detalles del evento
    message: str = ""
    description: Optional[str] = None
    status_code: Optional[int] = None
    
    # Metadatos adicionales
    metadata: Optional[Dict[str, Any]] = None
    
    # Información de rendimiento
    duration_ms: Optional[float] = None
    
    # Información de error
    error_code: Optional[str] = None
    error_details: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para logging"""
        data = asdict(self)
        # Convertir datetime a ISO string
        data["timestamp"] = self.timestamp.isoformat()
        # Filtrar valores None
        return {k: v for k, v in data.items() if v is not None}
    
    def to_json(self) -> str:
        """Convertir a JSON para almacenamiento"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=None)


class AuditLogger:
    """Logger de auditoría con almacenamiento en base de datos y archivos"""
    
    def __init__(self, name: str = "audit"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Configurar handlers si no existen
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Configurar handlers de logging"""
        # Handler para archivo de auditoría
        from logging.handlers import RotatingFileHandler
        import os
        
        # Crear directorio de logs si no existe
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Handler rotativo para auditoría
        audit_handler = RotatingFileHandler(
            filename=os.path.join(log_dir, "audit.log"),
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10,
            encoding="utf-8"
        )
        
        # Formatter personalizado para auditoría
        audit_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        audit_handler.setFormatter(audit_formatter)
        
        # Handler para consola en desarrollo
        if settings.debug:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(audit_formatter)
            self.logger.addHandler(console_handler)
        
        self.logger.addHandler(audit_handler)
    
    async def log_event(self, event: AuditEvent):
        """Registrar evento de auditoría"""
        try:
            # Log a archivo
            log_message = event.to_json()
            
            if event.level == AuditLevel.CRITICAL:
                self.logger.critical(log_message)
            elif event.level == AuditLevel.ERROR:
                self.logger.error(log_message)
            elif event.level == AuditLevel.WARNING:
                self.logger.warning(log_message)
            elif event.level == AuditLevel.SECURITY:
                self.logger.warning(f"SECURITY: {log_message}")
            else:
                self.logger.info(log_message)
            
            # Guardar en base de datos (async)
            await self._save_to_database(event)
            
        except Exception as e:
            # Nunca fallar por logging
            self.logger.error(f"Error logging audit event: {str(e)}")
    
    async def _save_to_database(self, event: AuditEvent):
        """Guardar evento en base de datos"""
        try:
            async with get_async_session() as session:
                # Importar modelo aquí para evitar circular imports
                from app.models.orm.audit import AuditLogORM
                
                audit_record = AuditLogORM(
                    event_id=event.event_id,
                    timestamp=event.timestamp,
                    action=event.action.value,
                    level=event.level.value,
                    user_id=event.user_id,
                    username=event.username,
                    user_roles=event.user_roles,
                    session_id=event.session_id,
                    request_id=event.request_id,
                    ip_address=event.ip_address,
                    user_agent=event.user_agent,
                    resource_type=event.resource_type,
                    resource_id=event.resource_id,
                    resource_version=event.resource_version,
                    endpoint=event.endpoint,
                    http_method=event.http_method,
                    message=event.message,
                    description=event.description,
                    status_code=event.status_code,
                    metadata=event.metadata,
                    duration_ms=event.duration_ms,
                    error_code=event.error_code,
                    error_details=event.error_details
                )
                
                session.add(audit_record)
                await session.commit()
                
        except Exception as e:
            # Log error pero no propagar
            self.logger.error(f"Failed to save audit event to database: {str(e)}")
    
    async def log_fhir_operation(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        request: Optional[Request] = None,
        response: Optional[Response] = None,
        duration_ms: Optional[float] = None,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log operación FHIR específica"""
        
        # Extraer información del request
        request_info = {}
        if request:
            request_info = {
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "endpoint": str(request.url.path),
                "http_method": request.method,
                "request_id": getattr(request.state, "request_id", None)
            }
        
        # Determinar nivel basado en acción
        level = AuditLevel.INFO
        if action in [AuditAction.DELETE, AuditAction.LOGIN_FAILED, AuditAction.ACCESS_DENIED]:
            level = AuditLevel.WARNING
        elif action == AuditAction.ERROR:
            level = AuditLevel.ERROR
        
        # Crear evento
        event = AuditEvent(
            event_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            action=action,
            level=level,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            message=message or f"{action.value} {resource_type}" + (f"/{resource_id}" if resource_id else ""),
            status_code=response.status_code if response else None,
            duration_ms=duration_ms,
            metadata=metadata,
            **request_info
        )
        
        await self.log_event(event)
    
    async def log_auth_event(
        self,
        action: AuditAction,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        request: Optional[Request] = None,
        success: bool = True,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log evento de autenticación"""
        
        request_info = {}
        if request:
            request_info = {
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "endpoint": str(request.url.path),
                "http_method": request.method,
                "session_id": getattr(request.state, "session_id", None)
            }
        
        level = AuditLevel.SECURITY if not success else AuditLevel.INFO
        
        event = AuditEvent(
            event_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            action=action,
            level=level,
            user_id=user_id,
            username=username,
            message=message or f"{action.value}" + (f" for {username}" if username else ""),
            metadata=metadata,
            **request_info
        )
        
        await self.log_event(event)
    
    async def log_system_event(
        self,
        action: AuditAction,
        level: AuditLevel,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        error_details: Optional[str] = None
    ):
        """Log evento del sistema"""
        
        event = AuditEvent(
            event_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            action=action,
            level=level,
            message=message,
            metadata=metadata,
            error_details=error_details
        )
        
        await self.log_event(event)


# Instancia global
audit_logger = AuditLogger()


# Funciones de conveniencia
async def audit_fhir_operation(
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    request: Optional[Request] = None,
    response: Optional[Response] = None,
    duration_ms: Optional[float] = None,
    message: str = "",
    metadata: Optional[Dict[str, Any]] = None
):
    """Función de conveniencia para operaciones FHIR"""
    await audit_logger.log_fhir_operation(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        username=username,
        request=request,
        response=response,
        duration_ms=duration_ms,
        message=message,
        metadata=metadata
    )


async def audit_auth_event(
    action: AuditAction,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    request: Optional[Request] = None,
    success: bool = True,
    message: str = "",
    metadata: Optional[Dict[str, Any]] = None
):
    """Función de conveniencia para eventos de autenticación"""
    await audit_logger.log_auth_event(
        action=action,
        user_id=user_id,
        username=username,
        request=request,
        success=success,
        message=message,
        metadata=metadata
    )


async def audit_system_event(
    action: AuditAction,
    level: AuditLevel,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
    error_details: Optional[str] = None
):
    """Función de conveniencia para eventos del sistema"""
    await audit_logger.log_system_event(
        action=action,
        level=level,
        message=message,
        metadata=metadata,
        error_details=error_details
    )


# Context manager para auditoría de operaciones
@asynccontextmanager
async def audit_operation(
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    request: Optional[Request] = None
):
    """Context manager para auditar operaciones con timing"""
    start_time = datetime.now()
    
    try:
        yield
        # Operación exitosa
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        await audit_fhir_operation(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            username=username,
            request=request,
            duration_ms=duration_ms,
            message=f"Successful {action.value}"
        )
        
    except Exception as e:
        # Operación fallida
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        await audit_fhir_operation(
            action=AuditAction.ERROR,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            username=username,
            request=request,
            duration_ms=duration_ms,
            message=f"Failed {action.value}: {str(e)}",
            metadata={"original_action": action.value, "error": str(e)}
        )
        raise