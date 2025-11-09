"""
Audit ORM Models
Modelos de base de datos para sistema de auditoría
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import uuid4
from sqlalchemy import (
    Column, String, DateTime, Integer, Text, 
    JSON, Float, ARRAY, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models.orm.base import Base


class AuditLogORM(Base):
    """
    Modelo ORM para logs de auditoría
    
    Registra todas las operaciones importantes del sistema incluyendo:
    - Operaciones FHIR (CRUD)
    - Eventos de autenticación
    - Cambios de configuración
    - Errores del sistema
    """
    
    __tablename__ = "audit_logs"
    
    # Identificadores únicos
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Timestamp con timezone
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    
    # Tipo de acción y nivel
    action = Column(String(50), nullable=False, index=True)
    level = Column(String(20), nullable=False, index=True)
    
    # Contexto del usuario
    user_id = Column(String(255), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)
    user_roles = Column(ARRAY(String), nullable=True)
    
    # Contexto de sesión y request
    session_id = Column(String(255), nullable=True, index=True)
    request_id = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True, index=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # Contexto FHIR
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    resource_version = Column(String(50), nullable=True)
    endpoint = Column(String(500), nullable=True, index=True)
    http_method = Column(String(10), nullable=True, index=True)
    
    # Detalles del evento
    message = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    status_code = Column(Integer, nullable=True, index=True)
    
    # Metadatos adicionales (JSON)
    audit_metadata = Column(JSON, nullable=True)
    
    # Información de rendimiento
    duration_ms = Column(Float, nullable=True, index=True)
    
    # Información de error
    error_code = Column(String(50), nullable=True, index=True)
    error_details = Column(Text, nullable=True)
    
    # Índices compuestos para consultas comunes
    __table_args__ = (
        # Índice para consultas por usuario y fecha
        Index('idx_audit_user_timestamp', 'user_id', 'timestamp'),
        
        # Índice para consultas por recurso FHIR
        Index('idx_audit_resource', 'resource_type', 'resource_id', 'action'),
        
        # Índice para consultas de seguridad
        Index('idx_audit_security', 'level', 'action', 'timestamp'),
        
        # Índice para consultas por IP (seguridad)
        Index('idx_audit_ip_timestamp', 'ip_address', 'timestamp'),
        
        # Índice para análisis de rendimiento
        Index('idx_audit_performance', 'endpoint', 'duration_ms', 'timestamp'),
        
        # Índice para búsqueda por mensaje (útil para debugging)
        # PostgreSQL soporta índices GIN para texto
        Index('idx_audit_message_gin', 'message', postgresql_using='gin', 
              postgresql_ops={'message': 'gin_trgm_ops'})
    )
    
    def __repr__(self):
        return (
            f"<AuditLogORM("
            f"event_id='{self.event_id}', "
            f"action='{self.action}', "
            f"user='{self.username}', "
            f"resource='{self.resource_type}'"
            f")>"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para serialización"""
        return {
            "id": str(self.id),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "level": self.level,
            "user_id": self.user_id,
            "username": self.username,
            "user_roles": self.user_roles,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_version": self.resource_version,
            "endpoint": self.endpoint,
            "http_method": self.http_method,
            "message": self.message,
            "description": self.description,
            "status_code": self.status_code,
            "audit_metadata": self.audit_metadata,
            "duration_ms": self.duration_ms,
            "error_code": self.error_code,
            "error_details": self.error_details
        }


class SystemMetricsORM(Base):
    """
    Modelo ORM para métricas del sistema
    
    Registra métricas agregadas para monitoreo y alertas:
    - Contadores de operaciones por minuto/hora
    - Métricas de rendimiento
    - Estado de salud del sistema
    """
    
    __tablename__ = "system_metrics"
    
    # ID y timestamp
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    
    # Tipo de métrica
    metric_type = Column(String(50), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    
    # Valores de la métrica
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)
    
    # Etiquetas/dimensiones
    labels = Column(JSON, nullable=True)
    
    # Contexto opcional
    resource_type = Column(String(100), nullable=True, index=True)
    endpoint = Column(String(500), nullable=True)
    
    # Índices para consultas de métricas
    __table_args__ = (
        # Índice para consultas por tipo y tiempo
        Index('idx_metrics_type_timestamp', 'metric_type', 'metric_name', 'timestamp'),
        
        # Índice para consultas por recurso
        Index('idx_metrics_resource', 'resource_type', 'timestamp'),
        
        # Índice único para evitar duplicados en ventanas de tiempo
        Index('idx_metrics_unique', 'metric_type', 'metric_name', 'timestamp', unique=True)
    )
    
    def __repr__(self):
        return (
            f"<SystemMetricsORM("
            f"metric='{self.metric_type}.{self.metric_name}', "
            f"value={self.value}, "
            f"timestamp={self.timestamp}"
            f")>"
        )


class AlertORM(Base):
    """
    Modelo ORM para alertas del sistema
    
    Registra alertas generadas por el sistema de monitoreo:
    - Alertas de seguridad
    - Alertas de rendimiento
    - Alertas de errores críticos
    """
    
    __tablename__ = "alerts"
    
    # ID y timestamps
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Información de la alerta
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Estado de la alerta
    status = Column(String(20), nullable=False, default="active", index=True)  # active, acknowledged, resolved
    acknowledged_by = Column(String(255), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Contexto
    source = Column(String(100), nullable=True)  # audit_log, metrics, etc.
    source_event_id = Column(String(255), nullable=True, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(255), nullable=True)
    
    # Metadatos adicionales
    alert_metadata = Column(JSON, nullable=True)
    
    # Contadores
    occurrence_count = Column(Integer, nullable=False, default=1)
    last_occurrence = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Índices para alertas
    __table_args__ = (
        # Índice para consultas por estado y severidad
        Index('idx_alerts_status_severity', 'status', 'severity', 'created_at'),
        
        # Índice para consultas por tipo
        Index('idx_alerts_type_timestamp', 'alert_type', 'created_at'),
        
        # Índice para deduplicación
        Index('idx_alerts_dedup', 'alert_type', 'title', 'status')
    )
    
    def __repr__(self):
        return (
            f"<AlertORM("
            f"type='{self.alert_type}', "
            f"severity='{self.severity}', "
            f"status='{self.status}', "
            f"title='{self.title[:50]}...'"
            f")>"
        )