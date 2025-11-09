"""
Observation Model - FHIR R4
Modelo de Observación Médica basado en estándar FHIR R4
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Union
from datetime import datetime

from .base import (
    DomainResourceBase,
    ObservationStatus,
    CodeableConcept,
    Reference,
    Identifier,
    Period,
    Quantity,
    Range,
    Ratio,
    Attachment
)


class ObservationReferenceRange(BaseModel):
    """Rango de referencia para una observación"""
    low: Optional[Quantity] = Field(None, description="Valor mínimo del rango")
    high: Optional[Quantity] = Field(None, description="Valor máximo del rango")
    type: Optional[CodeableConcept] = Field(None, description="Tipo de rango de referencia")
    applies_to: Optional[List[CodeableConcept]] = Field(None, description="Población aplicable")
    age: Optional[Range] = Field(None, description="Rango de edad aplicable")
    text: Optional[str] = Field(None, description="Descripción textual")


class ObservationComponent(BaseModel):
    """Componente de una observación (para observaciones multi-componente)"""
    code: CodeableConcept = Field(..., description="Tipo de componente")
    value_quantity: Optional[Quantity] = Field(None, description="Valor como cantidad")
    value_codeable_concept: Optional[CodeableConcept] = Field(None, description="Valor como concepto codificado")
    value_string: Optional[str] = Field(None, description="Valor como texto")
    value_boolean: Optional[bool] = Field(None, description="Valor como booleano")
    value_integer: Optional[int] = Field(None, description="Valor como entero")
    value_range: Optional[Range] = Field(None, description="Valor como rango")
    value_ratio: Optional[Ratio] = Field(None, description="Valor como ratio")
    value_time: Optional[str] = Field(None, description="Valor como tiempo")
    value_date_time: Optional[datetime] = Field(None, description="Valor como fecha/hora")
    value_period: Optional[Period] = Field(None, description="Valor como período")
    data_absent_reason: Optional[CodeableConcept] = Field(None, description="Razón por la cual no hay datos")
    interpretation: Optional[List[CodeableConcept]] = Field(None, description="Interpretación del resultado")
    reference_range: Optional[List[ObservationReferenceRange]] = Field(None, description="Rangos de referencia")


class Observation(DomainResourceBase):
    """
    Modelo de Observación FHIR R4
    
    Representa mediciones y afirmaciones simples sobre un paciente, dispositivo u otro sujeto
    """
    resource_type: str = Field("Observation", const=True)
    
    # Identificadores
    identifier: Optional[List[Identifier]] = Field(
        None,
        description="Identificadores únicos de la observación"
    )
    
    # Referencias a otros recursos
    based_on: Optional[List[Reference]] = Field(
        None,
        description="Solicitudes que cumplen esta observación"
    )
    
    part_of: Optional[List[Reference]] = Field(
        None,
        description="Procedimientos más grandes de los que forma parte"
    )
    
    # Estado
    status: ObservationStatus = Field(
        ...,
        description="Estado de la observación"
    )
    
    # Categorías
    category: Optional[List[CodeableConcept]] = Field(
        None,
        description="Clasificación de tipo de observación"
    )
    
    # Código de la observación
    code: CodeableConcept = Field(
        ...,
        description="Tipo de observación (código/nombre)"
    )
    
    # Sujeto
    subject: Optional[Reference] = Field(
        None,
        description="Sobre quién o qué es la observación"
    )
    
    # Contexto
    focus: Optional[List[Reference]] = Field(
        None,
        description="Qué observación aborda cuando el sujeto no es el paciente"
    )
    
    encounter: Optional[Reference] = Field(
        None,
        description="Encuentro de atención médica durante el cual se hizo la observación"
    )
    
    # Tiempo
    effective_date_time: Optional[datetime] = Field(
        None,
        description="Momento clínicamente relevante de la observación"
    )
    
    effective_period: Optional[Period] = Field(
        None,
        description="Período clínicamente relevante de la observación"
    )
    
    effective_instant: Optional[datetime] = Field(
        None,
        description="Instante clínicamente relevante de la observación"
    )
    
    # Momento de la observación
    issued: Optional[datetime] = Field(
        None,
        description="Fecha/hora en que este resultado fue puesto a disposición"
    )
    
    # Quién realizó la observación
    performer: Optional[List[Reference]] = Field(
        None,
        description="Quién es responsable de la observación"
    )
    
    # Valores
    value_quantity: Optional[Quantity] = Field(None, description="Resultado como cantidad")
    value_codeable_concept: Optional[CodeableConcept] = Field(None, description="Resultado como concepto codificado")
    value_string: Optional[str] = Field(None, description="Resultado como texto")
    value_boolean: Optional[bool] = Field(None, description="Resultado como booleano")
    value_integer: Optional[int] = Field(None, description="Resultado como entero")
    value_range: Optional[Range] = Field(None, description="Resultado como rango")
    value_ratio: Optional[Ratio] = Field(None, description="Resultado como ratio")
    value_time: Optional[str] = Field(None, description="Resultado como tiempo")
    value_date_time: Optional[datetime] = Field(None, description="Resultado como fecha/hora")
    value_period: Optional[Period] = Field(None, description="Resultado como período")
    
    # Razón por ausencia de datos
    data_absent_reason: Optional[CodeableConcept] = Field(
        None,
        description="Por qué no está disponible el resultado"
    )
    
    # Interpretación
    interpretation: Optional[List[CodeableConcept]] = Field(
        None,
        description="Alta, baja, normal, etc."
    )
    
    # Notas
    note: Optional[List[str]] = Field(
        None,
        description="Comentarios sobre la observación"
    )
    
    # Parte del cuerpo
    body_site: Optional[CodeableConcept] = Field(
        None,
        description="Sitio corporal observado"
    )
    
    # Método
    method: Optional[CodeableConcept] = Field(
        None,
        description="Cómo se realizó la observación"
    )
    
    # Especimen
    specimen: Optional[Reference] = Field(
        None,
        description="Especimen utilizado para esta observación"
    )
    
    # Dispositivo
    device: Optional[Reference] = Field(
        None,
        description="Dispositivo utilizado para la observación"
    )
    
    # Rangos de referencia
    reference_range: Optional[List[ObservationReferenceRange]] = Field(
        None,
        description="Proporciona orientación sobre interpretación"
    )
    
    # Observaciones relacionadas
    has_member: Optional[List[Reference]] = Field(
        None,
        description="Observaciones relacionadas incluidas en esta observación"
    )
    
    derived_from: Optional[List[Reference]] = Field(
        None,
        description="Observaciones relacionadas de las que se deriva esta observación"
    )
    
    # Componentes
    component: Optional[List[ObservationComponent]] = Field(
        None,
        description="Componente resultados"
    )
    
    # Validaciones
    @validator('effective_date_time')
    def effective_date_not_future(cls, v):
        if v and v > datetime.now():
            raise ValueError('La fecha efectiva no puede ser futura')
        return v
    
    @validator('issued')
    def issued_not_future(cls, v):
        if v and v > datetime.now():
            raise ValueError('La fecha de emisión no puede ser futura')
        return v


# Modelos de request/response

class ObservationCreate(BaseModel):
    """Modelo para crear una observación"""
    identifier: Optional[List[Identifier]] = None
    status: ObservationStatus = Field(..., description="Estado de la observación")
    category: Optional[List[CodeableConcept]] = None
    code: CodeableConcept = Field(..., description="Tipo de observación")
    subject: Optional[Reference] = None
    encounter: Optional[Reference] = None
    effective_date_time: Optional[datetime] = None
    effective_period: Optional[Period] = None
    performer: Optional[List[Reference]] = None
    value_quantity: Optional[Quantity] = None
    value_codeable_concept: Optional[CodeableConcept] = None
    value_string: Optional[str] = None
    value_boolean: Optional[bool] = None
    value_integer: Optional[int] = None
    data_absent_reason: Optional[CodeableConcept] = None
    interpretation: Optional[List[CodeableConcept]] = None
    note: Optional[List[str]] = None
    body_site: Optional[CodeableConcept] = None
    method: Optional[CodeableConcept] = None
    reference_range: Optional[List[ObservationReferenceRange]] = None
    component: Optional[List[ObservationComponent]] = None


class ObservationUpdate(BaseModel):
    """Modelo para actualizar una observación"""
    status: Optional[ObservationStatus] = None
    category: Optional[List[CodeableConcept]] = None
    effective_date_time: Optional[datetime] = None
    effective_period: Optional[Period] = None
    performer: Optional[List[Reference]] = None
    value_quantity: Optional[Quantity] = None
    value_codeable_concept: Optional[CodeableConcept] = None
    value_string: Optional[str] = None
    value_boolean: Optional[bool] = None
    value_integer: Optional[int] = None
    interpretation: Optional[List[CodeableConcept]] = None
    note: Optional[List[str]] = None
    reference_range: Optional[List[ObservationReferenceRange]] = None


class ObservationResponse(Observation):
    """Modelo de respuesta de observación con metadatos adicionales"""
    created_at: Optional[datetime] = Field(None, description="Fecha de creación del registro")
    updated_at: Optional[datetime] = Field(None, description="Fecha de última actualización")


class ObservationSummary(BaseModel):
    """Resumen de observación para listados"""
    id: str = Field(..., description="ID de la observación")
    status: ObservationStatus
    category: Optional[List[CodeableConcept]] = None
    code: CodeableConcept
    subject: Optional[Reference] = None
    effective_date_time: Optional[datetime] = None
    performer: Optional[List[Reference]] = None
    value_quantity: Optional[Quantity] = None
    value_string: Optional[str] = None
    created_at: Optional[datetime] = None


# Modelos de búsqueda

class ObservationSearchParams(BaseModel):
    """Parámetros de búsqueda de observaciones"""
    status: Optional[ObservationStatus] = Field(None, description="Filtrar por estado")
    category: Optional[str] = Field(None, description="Filtrar por categoría")
    code: Optional[str] = Field(None, description="Buscar por código de observación")
    subject: Optional[str] = Field(None, description="Filtrar por sujeto (paciente)")
    encounter: Optional[str] = Field(None, description="Filtrar por encuentro")
    performer: Optional[str] = Field(None, description="Filtrar por ejecutor")
    date: Optional[datetime] = Field(None, description="Filtrar por fecha")
    value_quantity: Optional[float] = Field(None, description="Filtrar por valor numérico")
    
    # Parámetros de paginación
    page: int = Field(1, ge=1, description="Número de página")
    size: int = Field(20, ge=1, le=100, description="Tamaño de página")
    
    # Ordenamiento
    sort: Optional[str] = Field(None, description="Campo de ordenamiento")
    order: Optional[str] = Field("desc", description="Orden: asc o desc")
    
    @validator('order')
    def valid_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('El orden debe ser "asc" o "desc"')
        return v