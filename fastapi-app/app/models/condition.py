"""
Condition Model - FHIR R4
Modelo de Condición/Diagnóstico basado en estándar FHIR R4
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date

from .base import (
    DomainResourceBase,
    ConditionClinicalStatus,
    ConditionVerificationStatus,
    CodeableConcept,
    Reference,
    Identifier,
    Period,
    Quantity,
    Range
, Literal)


class ConditionStage(BaseModel):
    """Etapa clínica o grado de una condición"""
    summary: Optional[CodeableConcept] = Field(None, description="Resumen simple de la etapa")
    assessment: Optional[List[Reference]] = Field(None, description="Evaluación formal de la etapa")
    type: Optional[CodeableConcept] = Field(None, description="Tipo de estadificación")


class ConditionEvidence(BaseModel):
    """Evidencia de apoyo para la condición"""
    code: Optional[List[CodeableConcept]] = Field(None, description="Manifestación/síntoma")
    detail: Optional[List[Reference]] = Field(None, description="Evidencia de apoyo / manifestaciones")


class Condition(DomainResourceBase):
    """
    Modelo de Condición FHIR R4
    
    Representa un problema clínico, condición, diagnóstico, o preocupación clínica
    """
    resource_type: Literal["Condition"] = "Condition"
    
    # Identificadores
    identifier: Optional[List[Identifier]] = Field(
        None,
        description="Identificadores externos para esta condición"
    )
    
    # Estado clínico
    clinical_status: Optional[ConditionClinicalStatus] = Field(
        None,
        description="Estado clínico activo de la condición"
    )
    
    # Estado de verificación
    verification_status: Optional[ConditionVerificationStatus] = Field(
        None,
        description="Estado de verificación de la condición"
    )
    
    # Categorías
    category: Optional[List[CodeableConcept]] = Field(
        None,
        description="Categoría de la condición"
    )
    
    # Severidad
    severity: Optional[CodeableConcept] = Field(
        None,
        description="Gravedad subjetiva de la condición"
    )
    
    # Código de la condición
    code: Optional[CodeableConcept] = Field(
        None,
        description="Identificación de la condición, problema o diagnóstico"
    )
    
    # Partes del cuerpo
    body_site: Optional[List[CodeableConcept]] = Field(
        None,
        description="Ubicación anatómica, si es relevante"
    )
    
    # Sujeto
    subject: Reference = Field(
        ...,
        description="Quién tiene la condición"
    )
    
    # Contexto
    encounter: Optional[Reference] = Field(
        None,
        description="Encuentro durante el cual se creó la condición"
    )
    
    # Inicio
    onset_date_time: Optional[datetime] = Field(
        None,
        description="Fecha/hora estimada o real de inicio"
    )
    
    onset_age: Optional[Quantity] = Field(
        None,
        description="Edad estimada o real de inicio"
    )
    
    onset_period: Optional[Period] = Field(
        None,
        description="Período estimado o real de inicio"
    )
    
    onset_range: Optional[Range] = Field(
        None,
        description="Rango estimado o real de inicio"
    )
    
    onset_string: Optional[str] = Field(
        None,
        description="Descripción de texto del inicio"
    )
    
    # Resolución
    abatement_date_time: Optional[datetime] = Field(
        None,
        description="Fecha/hora estimada o real de resolución"
    )
    
    abatement_age: Optional[Quantity] = Field(
        None,
        description="Edad estimada o real de resolución"
    )
    
    abatement_period: Optional[Period] = Field(
        None,
        description="Período estimado o real de resolución"
    )
    
    abatement_range: Optional[Range] = Field(
        None,
        description="Rango estimado o real de resolución"
    )
    
    abatement_string: Optional[str] = Field(
        None,
        description="Descripción de texto de la resolución"
    )
    
    # Fechas de registro
    recorded_date: Optional[datetime] = Field(
        None,
        description="Fecha en que fue registrada por primera vez"
    )
    
    # Quién lo registró
    recorder: Optional[Reference] = Field(
        None,
        description="Quién registró la condición"
    )
    
    # Fuente de la información
    asserter: Optional[Reference] = Field(
        None,
        description="Persona que afirma esta condición"
    )
    
    # Etapa
    stage: Optional[List[ConditionStage]] = Field(
        None,
        description="Etapa/grado, generalmente evaluado formalmente"
    )
    
    # Evidencia
    evidence: Optional[List[ConditionEvidence]] = Field(
        None,
        description="Evidencia de apoyo / manifestaciones que llevaron al diagnóstico"
    )
    
    # Notas
    note: Optional[List[str]] = Field(
        None,
        description="Información adicional sobre la condición"
    )
    
    # Validaciones
    @field_validator('onset_date_time')
    def onset_not_future(cls, v):
        if v and v > datetime.now():
            raise ValueError('La fecha de inicio no puede ser futura')
        return v
    
    @field_validator('recorded_date')
    def recorded_not_future(cls, v):
        if v and v > datetime.now():
            raise ValueError('La fecha de registro no puede ser futura')
        return v
    
    @field_validator('abatement_date_time')
    def abatement_after_onset(cls, v, values):
        onset = values.get('onset_date_time')
        if v and onset and v <= onset:
            raise ValueError('La fecha de resolución debe ser posterior al inicio')
        return v


# Modelos de request/response

class ConditionCreate(BaseModel):
    """Modelo para crear una condición"""
    identifier: Optional[List[Identifier]] = None
    clinical_status: Optional[ConditionClinicalStatus] = Field(ConditionClinicalStatus.ACTIVE)
    verification_status: Optional[ConditionVerificationStatus] = Field(ConditionVerificationStatus.CONFIRMED)
    category: Optional[List[CodeableConcept]] = None
    severity: Optional[CodeableConcept] = None
    code: Optional[CodeableConcept] = None
    body_site: Optional[List[CodeableConcept]] = None
    subject: Reference = Field(..., description="Quién tiene la condición")
    encounter: Optional[Reference] = None
    onset_date_time: Optional[datetime] = None
    onset_string: Optional[str] = None
    recorder: Optional[Reference] = None
    asserter: Optional[Reference] = None
    stage: Optional[List[ConditionStage]] = None
    evidence: Optional[List[ConditionEvidence]] = None
    note: Optional[List[str]] = None


class ConditionUpdate(BaseModel):
    """Modelo para actualizar una condición"""
    clinical_status: Optional[ConditionClinicalStatus] = None
    verification_status: Optional[ConditionVerificationStatus] = None
    category: Optional[List[CodeableConcept]] = None
    severity: Optional[CodeableConcept] = None
    body_site: Optional[List[CodeableConcept]] = None
    abatement_date_time: Optional[datetime] = None
    abatement_string: Optional[str] = None
    stage: Optional[List[ConditionStage]] = None
    evidence: Optional[List[ConditionEvidence]] = None
    note: Optional[List[str]] = None


class ConditionResponse(Condition):
    """Modelo de respuesta de condición con metadatos adicionales"""
    created_at: Optional[datetime] = Field(None, description="Fecha de creación del registro")
    updated_at: Optional[datetime] = Field(None, description="Fecha de última actualización")


class ConditionSummary(BaseModel):
    """Resumen de condición para listados"""
    id: str = Field(..., description="ID de la condición")
    clinical_status: Optional[ConditionClinicalStatus] = None
    verification_status: Optional[ConditionVerificationStatus] = None
    category: Optional[List[CodeableConcept]] = None
    severity: Optional[CodeableConcept] = None
    code: Optional[CodeableConcept] = None
    subject: Reference
    onset_date_time: Optional[datetime] = None
    recorded_date: Optional[datetime] = None
    created_at: Optional[datetime] = None


# Modelos de búsqueda

class ConditionSearchParams(BaseModel):
    """Parámetros de búsqueda de condiciones"""
    clinical_status: Optional[ConditionClinicalStatus] = Field(None, description="Filtrar por estado clínico")
    verification_status: Optional[ConditionVerificationStatus] = Field(None, description="Filtrar por estado de verificación")
    category: Optional[str] = Field(None, description="Filtrar por categoría")
    severity: Optional[str] = Field(None, description="Filtrar por severidad")
    code: Optional[str] = Field(None, description="Buscar por código de condición")
    subject: Optional[str] = Field(None, description="Filtrar por sujeto (paciente)")
    encounter: Optional[str] = Field(None, description="Filtrar por encuentro")
    onset_date: Optional[datetime] = Field(None, description="Filtrar por fecha de inicio")
    recorded_date: Optional[datetime] = Field(None, description="Filtrar por fecha de registro")
    
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