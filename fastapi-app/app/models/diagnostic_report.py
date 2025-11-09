"""
DiagnosticReport Model - FHIR R4
Modelo de Reporte Diagnóstico basado en estándar FHIR R4
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union
from datetime import datetime, date
from enum import Enum

from .base import (
    DomainResourceBase,
    CodeableConcept,
    Reference,
    Identifier,
    Period,
    Attachment
, Literal)


class DiagnosticReportStatus(str, Enum):
    """Estado del reporte diagnóstico"""
    REGISTERED = "registered"
    PARTIAL = "partial"
    PRELIMINARY = "preliminary"
    FINAL = "final"
    AMENDED = "amended"
    CORRECTED = "corrected"
    APPENDED = "appended"
    CANCELLED = "cancelled"
    ENTERED_IN_ERROR = "entered-in-error"
    UNKNOWN = "unknown"


class DiagnosticReportMedia(BaseModel):
    """Medios clave asociados con este reporte"""
    comment: Optional[str] = Field(None, description="Comentario sobre el medio")
    link: Reference = Field(..., description="Referencia al medio")


class DiagnosticReport(DomainResourceBase):
    """
    Modelo de Reporte Diagnóstico FHIR R4
    
    Representa los hallazgos y interpretación de pruebas diagnósticas realizadas en pacientes, 
    grupos de pacientes, dispositivos y ubicaciones
    """
    resource_type: Literal["DiagnosticReport"] = "DiagnosticReport"
    
    # Identificadores
    identifier: Optional[List[Identifier]] = Field(
        None,
        description="Identificadores de negocio para el reporte"
    )
    
    # Solicitudes basadas en
    based_on: Optional[List[Reference]] = Field(
        None,
        description="Qué solicitud de servicio diagnóstico cumple este reporte"
    )
    
    # Estado
    status: DiagnosticReportStatus = Field(
        ...,
        description="Estado del reporte diagnóstico"
    )
    
    # Categoría
    category: Optional[List[CodeableConcept]] = Field(
        None,
        description="Clasificación de servicio (por ejemplo, Cardiología)"
    )
    
    # Código
    code: CodeableConcept = Field(
        ...,
        description="Nombre/Código para este reporte diagnóstico"
    )
    
    # Sujeto
    subject: Optional[Reference] = Field(
        None,
        description="El sujeto del reporte - generalmente, pero no siempre, el paciente"
    )
    
    # Encuentro
    encounter: Optional[Reference] = Field(
        None,
        description="Contexto de atención médica para el reporte"
    )
    
    # Tiempo efectivo
    effective_date_time: Optional[datetime] = Field(
        None,
        description="Tiempo clínicamente relevante/efectivo del reporte"
    )
    
    effective_period: Optional[Period] = Field(
        None,
        description="Período clínicamente relevante/efectivo del reporte"
    )
    
    # Emitido
    issued: Optional[datetime] = Field(
        None,
        description="Fecha y hora en que se puso a disposición este reporte"
    )
    
    # Ejecutor
    performer: Optional[List[Reference]] = Field(
        None,
        description="Organización/Profesional responsable del reporte"
    )
    
    # Intérprete de resultados
    results_interpreter: Optional[List[Reference]] = Field(
        None,
        description="Interpretación primaria de los resultados"
    )
    
    # Especimen
    specimen: Optional[List[Reference]] = Field(
        None,
        description="Especímenes en los que se basa este reporte"
    )
    
    # Resultado
    result: Optional[List[Reference]] = Field(
        None,
        description="Observaciones"
    )
    
    # Estudios de imagen
    imaging_study: Optional[List[Reference]] = Field(
        None,
        description="Referencia a estudios de imagen completos"
    )
    
    # Medios
    media: Optional[List[DiagnosticReportMedia]] = Field(
        None,
        description="Medios clave asociados con este reporte"
    )
    
    # Conclusión
    conclusion: Optional[str] = Field(
        None,
        description="Resumen clínico (interpretación) de los hallazgos"
    )
    
    # Código de conclusión
    conclusion_code: Optional[List[CodeableConcept]] = Field(
        None,
        description="Códigos para la conclusión textual"
    )
    
    # Presentación adjunta
    presented_form: Optional[List[Attachment]] = Field(
        None,
        description="Representación completa del reporte como emitido"
    )
    
    # Validaciones
    @field_validator('effective_date_time', 'issued')
    def date_not_future(cls, v):
        if v and v > datetime.now():
            raise ValueError('La fecha no puede ser futura')
        return v
    
    @field_validator('issued')
    def issued_after_effective(cls, v, values):
        effective_dt = values.get('effective_date_time')
        if v and effective_dt and v < effective_dt:
            raise ValueError('La fecha de emisión no puede ser anterior a la fecha efectiva')
        return v
    
    @field_validator('media')
    def media_has_link(cls, v):
        if v:
            for medium in v:
                if not medium.link:
                    raise ValueError('Cada medio debe tener un enlace')
        return v


# Modelos de request/response

class DiagnosticReportCreate(BaseModel):
    """Modelo para crear un reporte diagnóstico"""
    identifier: Optional[List[Identifier]] = None
    based_on: Optional[List[Reference]] = None
    status: DiagnosticReportStatus = Field(..., description="Estado del reporte")
    category: Optional[List[CodeableConcept]] = None
    code: CodeableConcept = Field(..., description="Nombre/Código para este reporte")
    subject: Optional[Reference] = None
    encounter: Optional[Reference] = None
    effective_date_time: Optional[datetime] = None
    effective_period: Optional[Period] = None
    performer: Optional[List[Reference]] = None
    results_interpreter: Optional[List[Reference]] = None
    specimen: Optional[List[Reference]] = None
    result: Optional[List[Reference]] = None
    imaging_study: Optional[List[Reference]] = None
    media: Optional[List[DiagnosticReportMedia]] = None
    conclusion: Optional[str] = None
    conclusion_code: Optional[List[CodeableConcept]] = None
    presented_form: Optional[List[Attachment]] = None


class DiagnosticReportUpdate(BaseModel):
    """Modelo para actualizar un reporte diagnóstico"""
    status: Optional[DiagnosticReportStatus] = None
    category: Optional[List[CodeableConcept]] = None
    effective_date_time: Optional[datetime] = None
    effective_period: Optional[Period] = None
    performer: Optional[List[Reference]] = None
    results_interpreter: Optional[List[Reference]] = None
    result: Optional[List[Reference]] = None
    conclusion: Optional[str] = None
    conclusion_code: Optional[List[CodeableConcept]] = None
    presented_form: Optional[List[Attachment]] = None


class DiagnosticReportResponse(DiagnosticReport):
    """Modelo de respuesta de reporte diagnóstico con metadatos adicionales"""
    created_at: Optional[datetime] = Field(None, description="Fecha de creación del registro")
    updated_at: Optional[datetime] = Field(None, description="Fecha de última actualización")


class DiagnosticReportSummary(BaseModel):
    """Resumen de reporte diagnóstico para listados"""
    id: str = Field(..., description="ID del reporte")
    status: DiagnosticReportStatus
    code: CodeableConcept
    subject: Optional[Reference] = None
    effective_date_time: Optional[datetime] = None
    issued: Optional[datetime] = None
    performer: Optional[List[Reference]] = None
    conclusion: Optional[str] = None
    created_at: Optional[datetime] = None


# Modelos de búsqueda

class DiagnosticReportSearchParams(BaseModel):
    """Parámetros de búsqueda de reportes diagnósticos"""
    status: Optional[DiagnosticReportStatus] = Field(None, description="Filtrar por estado")
    category: Optional[str] = Field(None, description="Filtrar por categoría")
    code: Optional[str] = Field(None, description="Buscar por código del reporte")
    subject: Optional[str] = Field(None, description="Filtrar por sujeto (paciente)")
    encounter: Optional[str] = Field(None, description="Filtrar por encuentro")
    performer: Optional[str] = Field(None, description="Filtrar por ejecutor")
    results_interpreter: Optional[str] = Field(None, description="Filtrar por intérprete")
    effective_date: Optional[datetime] = Field(None, description="Filtrar por fecha efectiva")
    issued_date: Optional[datetime] = Field(None, description="Filtrar por fecha de emisión")
    specimen: Optional[str] = Field(None, description="Filtrar por especimen")
    
    # Parámetros de paginación
    page: int = Field(1, ge=1, description="Número de página")
    size: int = Field(20, ge=1, le=100, description="Tamaño de página")
    
    # Ordenamiento
    sort: Optional[str] = Field(None, description="Campo de ordenamiento")
    order: Optional[str] = Field("desc", description="Orden: asc o desc")
    
    @field_validator('order')
    def valid_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('El orden debe ser "asc" o "desc"')
        return v


# Clases de utilidad para manejo de reportes

class DiagnosticReportUtility:
    """Utilidades para manejo de reportes diagnósticos"""
    
    @staticmethod
    def is_final_status(status: DiagnosticReportStatus) -> bool:
        """Verifica si el estado es final"""
        return status in [
            DiagnosticReportStatus.FINAL,
            DiagnosticReportStatus.AMENDED,
            DiagnosticReportStatus.CORRECTED,
            DiagnosticReportStatus.APPENDED
        ]
    
    @staticmethod
    def can_be_modified(status: DiagnosticReportStatus) -> bool:
        """Verifica si el reporte puede ser modificado"""
        return status not in [
            DiagnosticReportStatus.CANCELLED,
            DiagnosticReportStatus.ENTERED_IN_ERROR
        ]
    
    @staticmethod
    def get_status_priority(status: DiagnosticReportStatus) -> int:
        """Obtiene prioridad numérica del estado para ordenamiento"""
        priority_map = {
            DiagnosticReportStatus.REGISTERED: 1,
            DiagnosticReportStatus.PARTIAL: 2,
            DiagnosticReportStatus.PRELIMINARY: 3,
            DiagnosticReportStatus.FINAL: 4,
            DiagnosticReportStatus.AMENDED: 5,
            DiagnosticReportStatus.CORRECTED: 6,
            DiagnosticReportStatus.APPENDED: 7,
            DiagnosticReportStatus.CANCELLED: 8,
            DiagnosticReportStatus.ENTERED_IN_ERROR: 9,
            DiagnosticReportStatus.UNKNOWN: 10
        }
        return priority_map.get(status, 99)


# Constantes para categorías comunes de reportes diagnósticos

class DiagnosticReportCategories:
    """Categorías comunes de reportes diagnósticos"""
    
    CARDIOLOGY = CodeableConcept(
        coding=[{
            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
            "code": "CT",
            "display": "Cardiology"
        }]
    )
    
    RADIOLOGY = CodeableConcept(
        coding=[{
            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
            "code": "RAD",
            "display": "Radiology"
        }]
    )
    
    LABORATORY = CodeableConcept(
        coding=[{
            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
            "code": "LAB",
            "display": "Laboratory"
        }]
    )
    
    PATHOLOGY = CodeableConcept(
        coding=[{
            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
            "code": "PAT",
            "display": "Pathology"
        }]
    )
    
    MICROBIOLOGY = CodeableConcept(
        coding=[{
            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
            "code": "MB",
            "display": "Microbiology"
        }]
    )