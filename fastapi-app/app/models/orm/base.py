"""
Base ORM Configuration for SQLAlchemy
Configuración base para los modelos ORM con optimizaciones para Citus
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, BigInteger, Text, DateTime, Boolean, text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from typing import Optional


# Base class para todos los modelos ORM
Base = declarative_base()


class BaseModel(Base):
    """
    Clase base abstracta para todos los modelos ORM
    Incluye campos comunes y metadatos
    """
    __abstract__ = True
    
    # Timestamp de creación (común a todas las tablas)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Fecha y hora de creación del registro"
    )


class DistributedModel(BaseModel):
    """
    Clase base para modelos distribuidos por documento_id en Citus
    Incluye la columna de distribución requerida
    """
    __abstract__ = True
    
    # Columna de distribución de Citus (requerida en PK)
    documento_id = Column(
        BigInteger,
        nullable=False,
        comment="ID del documento del paciente (columna de distribución Citus)"
    )


class ReferenceModel(BaseModel):
    """
    Clase base para modelos de referencia (replicados en Citus)
    Tablas que no requieren distribución
    """
    __abstract__ = True
    pass


# Configuraciones específicas para Citus

class CitusTableConfig:
    """
    Configuraciones y optimizaciones específicas para Citus
    """
    
    # Configuración para tablas distribuidas
    DISTRIBUTED_TABLE_CONFIG = {
        # Las configuraciones específicas de Citus se aplicarán 
        # después de la creación de tablas usando SQL directo
    }
    
    # Configuración para tablas de referencia
    REFERENCE_TABLE_CONFIG = {
        # Las configuraciones específicas de Citus se aplicarán 
        # después de la creación de tablas usando SQL directo
    }
    
    @staticmethod
    def get_distributed_table_args():
        """Retorna argumentos de tabla para tablas distribuidas"""
        return CitusTableConfig.DISTRIBUTED_TABLE_CONFIG
    
    @staticmethod
    def get_reference_table_args():
        """Retorna argumentos de tabla para tablas de referencia"""
        return CitusTableConfig.REFERENCE_TABLE_CONFIG


# Mixins para funcionalidades comunes

class UUIDMixin:
    """Mixin para tablas que requieren UUID como clave primaria"""
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        nullable=False,
        comment="UUID único del recurso (clave primaria)"
    )


class UUIDFieldMixin:
    """Mixin para tablas que requieren UUID pero no como clave primaria"""
    uuid = Column(
        UUID(as_uuid=True),
        server_default=text("gen_random_uuid()"),
        nullable=False,
        unique=True,
        comment="UUID único del recurso"
    )


class AuditMixin:
    """Mixin para auditoría extendida"""
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
        comment="Fecha y hora de última actualización"
    )
    
    version = Column(
        BigInteger,
        default=1,
        nullable=False,
        comment="Versión del registro para control de concurrencia"
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha y hora de eliminación lógica"
    )
    
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica si el registro está eliminado lógicamente"
    )


class FHIRResourceMixin:
    """Mixin para recursos FHIR"""
    fhir_id = Column(
        Text,
        nullable=True,
        comment="ID del recurso FHIR"
    )
    
    fhir_version = Column(
        Text,
        default="4.0.1",
        nullable=False,
        comment="Versión FHIR del recurso"
    )
    
    fhir_last_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Última actualización FHIR"
    )


# Utility functions para el ORM

def get_table_comment(resource_name: str, is_distributed: bool = True) -> str:
    """
    Genera comentario estándar para tablas
    
    Args:
        resource_name: Nombre del recurso FHIR
        is_distributed: Si la tabla está distribuida en Citus
    
    Returns:
        Comentario descriptivo para la tabla
    """
    distribution_type = "distribuida" if is_distributed else "referencia"
    return f"Tabla {distribution_type} para recurso FHIR {resource_name}"


def create_composite_primary_key(table_args: dict, pk_columns: list) -> dict:
    """
    Crea configuración de primary key compuesta para Citus
    
    Args:
        table_args: Argumentos de tabla existentes
        pk_columns: Lista de columnas que forman la PK
    
    Returns:
        Argumentos de tabla actualizados
    """
    table_args.update({
        "postgresql_pk_constraint": True,
        "postgresql_pk_columns": pk_columns
    })
    return table_args


# Constantes para mapeo de estados FHIR a base de datos

class FHIRStatus:
    """Constantes para estados FHIR comunes"""
    
    # Estados de Patient
    PATIENT_ACTIVE = "active"
    PATIENT_INACTIVE = "inactive"
    
    # Estados de Observation
    OBSERVATION_REGISTERED = "registered"
    OBSERVATION_PRELIMINARY = "preliminary"
    OBSERVATION_FINAL = "final"
    OBSERVATION_AMENDED = "amended"
    OBSERVATION_CANCELLED = "cancelled"
    OBSERVATION_ENTERED_IN_ERROR = "entered-in-error"
    OBSERVATION_UNKNOWN = "unknown"
    
    # Estados de Condition
    CONDITION_ACTIVE = "active"
    CONDITION_RECURRENCE = "recurrence"
    CONDITION_RELAPSE = "relapse"
    CONDITION_INACTIVE = "inactive"
    CONDITION_REMISSION = "remission"
    CONDITION_RESOLVED = "resolved"
    
    # Estados de MedicationRequest
    MEDICATION_REQUEST_ACTIVE = "active"
    MEDICATION_REQUEST_ON_HOLD = "on-hold"
    MEDICATION_REQUEST_CANCELLED = "cancelled"
    MEDICATION_REQUEST_COMPLETED = "completed"
    MEDICATION_REQUEST_ENTERED_IN_ERROR = "entered-in-error"
    MEDICATION_REQUEST_STOPPED = "stopped"
    MEDICATION_REQUEST_DRAFT = "draft"
    MEDICATION_REQUEST_UNKNOWN = "unknown"
    
    # Estados de DiagnosticReport
    DIAGNOSTIC_REPORT_REGISTERED = "registered"
    DIAGNOSTIC_REPORT_PARTIAL = "partial"
    DIAGNOSTIC_REPORT_PRELIMINARY = "preliminary"
    DIAGNOSTIC_REPORT_FINAL = "final"
    DIAGNOSTIC_REPORT_AMENDED = "amended"
    DIAGNOSTIC_REPORT_CORRECTED = "corrected"
    DIAGNOSTIC_REPORT_APPENDED = "appended"
    DIAGNOSTIC_REPORT_CANCELLED = "cancelled"
    DIAGNOSTIC_REPORT_ENTERED_IN_ERROR = "entered-in-error"
    DIAGNOSTIC_REPORT_UNKNOWN = "unknown"


# Configuraciones de índices comunes

class CommonIndexes:
    """Configuraciones de índices comunes para optimización"""
    
    @staticmethod
    def get_patient_indexes():
        """Índices comunes para tablas relacionadas con pacientes"""
        return [
            {"columns": ["documento_id"], "name": "idx_{table}_documento_id"},
            {"columns": ["paciente_id"], "name": "idx_{table}_paciente_id"},
            {"columns": ["created_at"], "name": "idx_{table}_created_at"},
            {"columns": ["documento_id", "created_at"], "name": "idx_{table}_doc_created"}
        ]
    
    @staticmethod
    def get_temporal_indexes():
        """Índices para consultas temporales"""
        return [
            {"columns": ["fecha"], "name": "idx_{table}_fecha"},
            {"columns": ["fecha_inicio"], "name": "idx_{table}_fecha_inicio"},
            {"columns": ["fecha_fin"], "name": "idx_{table}_fecha_fin"}
        ]
    
    @staticmethod
    def get_status_indexes():
        """Índices para estados y tipos"""
        return [
            {"columns": ["estado"], "name": "idx_{table}_estado"},
            {"columns": ["tipo"], "name": "idx_{table}_tipo"},
            {"columns": ["categoria"], "name": "idx_{table}_categoria"}
        ]


# Import necesarios que faltaron
from sqlalchemy import text

# Exportaciones del módulo
__all__ = [
    "Base",
    "BaseModel", 
    "DistributedModel",
    "ReferenceModel",
    "CitusTableConfig",
    "UUIDMixin",
    "AuditMixin", 
    "SoftDeleteMixin",
    "FHIRResourceMixin",
    "get_table_comment",
    "create_composite_primary_key",
    "FHIRStatus",
    "CommonIndexes"
]