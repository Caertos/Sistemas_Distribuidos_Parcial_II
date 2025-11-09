"""
MedicationRequest Model - FHIR R4
Modelo de Solicitud de Medicamento basado en estándar FHIR R4
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Union
from datetime import datetime, date
from enum import Enum

from .base import (
    DomainResourceBase,
    CodeableConcept,
    Reference,
    Identifier,
    Period,
    Quantity,
    Attachment
)


class MedicationRequestStatus(str, Enum):
    """Estado de la solicitud de medicamento"""
    ACTIVE = "active"
    ON_HOLD = "on-hold"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    ENTERED_IN_ERROR = "entered-in-error"
    STOPPED = "stopped"
    DRAFT = "draft"
    UNKNOWN = "unknown"


class MedicationRequestIntent(str, Enum):
    """Intención de la solicitud de medicamento"""
    PROPOSAL = "proposal"
    PLAN = "plan"
    ORDER = "order"
    ORIGINAL_ORDER = "original-order"
    REFLEX_ORDER = "reflex-order"
    FILLER_ORDER = "filler-order"
    INSTANCE_ORDER = "instance-order"
    OPTION = "option"


class MedicationRequestPriority(str, Enum):
    """Prioridad de la solicitud"""
    ROUTINE = "routine"
    URGENT = "urgent"
    ASAP = "asap"
    STAT = "stat"


class Dosage(BaseModel):
    """Instrucciones de dosificación"""
    sequence: Optional[int] = Field(None, description="Orden de las instrucciones de dosificación")
    text: Optional[str] = Field(None, description="Instrucciones de dosificación de texto libre")
    additional_instruction: Optional[List[CodeableConcept]] = Field(None, description="Instrucciones suplementarias")
    patient_instruction: Optional[str] = Field(None, description="Instrucciones del paciente")
    timing: Optional[dict] = Field(None, description="Cuándo debe administrarse el medicamento")
    as_needed_boolean: Optional[bool] = Field(None, description="Tomar 'según sea necesario'")
    as_needed_codeable_concept: Optional[CodeableConcept] = Field(None, description="Tomar 'según sea necesario' (razón)")
    site: Optional[CodeableConcept] = Field(None, description="Sitio del cuerpo para administrar")
    route: Optional[CodeableConcept] = Field(None, description="Cómo debe entrar el medicamento en el cuerpo")
    method: Optional[CodeableConcept] = Field(None, description="Técnica para administrar medicamento")
    dose_and_rate: Optional[List[dict]] = Field(None, description="Cantidad de medicamento por dosis")
    max_dose_per_period: Optional[Quantity] = Field(None, description="Límite superior de medicamento por unidad de tiempo")
    max_dose_per_administration: Optional[Quantity] = Field(None, description="Límite superior de medicamento por administración")
    max_dose_per_lifetime: Optional[Quantity] = Field(None, description="Límite superior de medicamento de por vida")


class MedicationRequestSubstitution(BaseModel):
    """Información de sustitución"""
    allowed_boolean: Optional[bool] = Field(None, description="Si está permitida la sustitución")
    allowed_codeable_concept: Optional[CodeableConcept] = Field(None, description="Si está permitida la sustitución")
    reason: Optional[CodeableConcept] = Field(None, description="Por qué debe o no debe hacerse la sustitución")


class MedicationRequestDispenseRequest(BaseModel):
    """Solicitud de dispensación específica"""
    initial_fill: Optional[dict] = Field(None, description="Primer llenado de detalles")
    dispense_interval: Optional[dict] = Field(None, description="Tiempo mínimo entre dispensaciones")
    validity_period: Optional[Period] = Field(None, description="Período de validez de tiempo")
    number_of_repeats_allowed: Optional[int] = Field(None, description="Número de recargas autorizadas")
    quantity: Optional[Quantity] = Field(None, description="Cantidad a dispensar")
    expected_supply_duration: Optional[dict] = Field(None, description="Número de días de suministro por dispensación")
    performer: Optional[Reference] = Field(None, description="Organización prevista que dispensará")


class MedicationRequest(DomainResourceBase):
    """
    Modelo de Solicitud de Medicamento FHIR R4
    
    Representa una orden o solicitud para el suministro y administración de un medicamento
    """
    resource_type: str = Field("MedicationRequest", const=True)
    
    # Identificadores
    identifier: Optional[List[Identifier]] = Field(
        None,
        description="Identificadores externos"
    )
    
    # Estado
    status: MedicationRequestStatus = Field(
        ...,
        description="Estado de la solicitud"
    )
    
    # Razón del estado
    status_reason: Optional[CodeableConcept] = Field(
        None,
        description="Razón para el estado actual"
    )
    
    # Intención
    intent: MedicationRequestIntent = Field(
        ...,
        description="Intención de la solicitud"
    )
    
    # Categoría
    category: Optional[List[CodeableConcept]] = Field(
        None,
        description="Tipo de solicitud de medicamento"
    )
    
    # Prioridad
    priority: Optional[MedicationRequestPriority] = Field(
        None,
        description="Prioridad de la solicitud"
    )
    
    # No realizar
    do_not_perform: Optional[bool] = Field(
        None,
        description="Verdadero si el medicamento no debe ser dado"
    )
    
    # Medicamento reportado
    reported_boolean: Optional[bool] = Field(
        None,
        description="Reportado en lugar de prescrito/dispensado"
    )
    
    reported_reference: Optional[Reference] = Field(
        None,
        description="Persona o organización que proporciona la información"
    )
    
    # Medicamento
    medication_codeable_concept: Optional[CodeableConcept] = Field(
        None,
        description="Medicamento a suministrar"
    )
    
    medication_reference: Optional[Reference] = Field(
        None,
        description="Medicamento a suministrar"
    )
    
    # Sujeto
    subject: Reference = Field(
        ...,
        description="Para quién es la solicitud de medicamento"
    )
    
    # Contexto
    encounter: Optional[Reference] = Field(
        None,
        description="Encuentro durante el cual se creó la solicitud"
    )
    
    # Información de apoyo
    supporting_information: Optional[List[Reference]] = Field(
        None,
        description="Información para apoyar la solicitud de medicamento"
    )
    
    # Fecha de autoría
    authored_on: Optional[datetime] = Field(
        None,
        description="Cuándo se escribió la solicitud"
    )
    
    # Solicitante
    requester: Optional[Reference] = Field(
        None,
        description="Quién/Qué solicitó el Medicamento"
    )
    
    # Ejecutor
    performer: Optional[Reference] = Field(
        None,
        description="Ejecutor previsto de la medicación"
    )
    
    # Tipo de ejecutor
    performer_type: Optional[CodeableConcept] = Field(
        None,
        description="Tipo de ejecutor de la medicación"
    )
    
    # Grabador
    recorder: Optional[Reference] = Field(
        None,
        description="Persona que ingresó la solicitud"
    )
    
    # Código de razón
    reason_code: Optional[List[CodeableConcept]] = Field(
        None,
        description="Razón o indicación para ordenar o no ordenar el medicamento"
    )
    
    # Referencia de razón
    reason_reference: Optional[List[Reference]] = Field(
        None,
        description="Condición o observación que soporta por qué se está pidiendo el medicamento"
    )
    
    # URL instantáneo
    instantiates_canonical: Optional[List[str]] = Field(
        None,
        description="URL instantáneo de FHIR definido protocolo, guía, orden establecida"
    )
    
    instantiates_uri: Optional[List[str]] = Field(
        None,
        description="URL instantáneo de protocolo, guía, orden establecida no definida por FHIR"
    )
    
    # Basado en
    based_on: Optional[List[Reference]] = Field(
        None,
        description="Lo que solicitud cumple"
    )
    
    # ID de grupo
    group_identifier: Optional[Identifier] = Field(
        None,
        description="Identificador compuesto de solicitud"
    )
    
    # Estado del curso de la terapia
    course_of_therapy_type: Optional[CodeableConcept] = Field(
        None,
        description="Descripción general del patrón de medicación"
    )
    
    # Seguro
    insurance: Optional[List[Reference]] = Field(
        None,
        description="Planes de seguro, programas de cobertura, sistemas de pago"
    )
    
    # Nota
    note: Optional[List[str]] = Field(
        None,
        description="Información sobre la solicitud de medicamento"
    )
    
    # Instrucciones de dosificación
    dosage_instruction: Optional[List[Dosage]] = Field(
        None,
        description="Cómo debe tomarse el medicamento"
    )
    
    # Solicitud de dispensación
    dispense_request: Optional[MedicationRequestDispenseRequest] = Field(
        None,
        description="Solicitud de dispensación de medicamento"
    )
    
    # Sustitución
    substitution: Optional[MedicationRequestSubstitution] = Field(
        None,
        description="Cualquier restricción sobre sustitución de medicamento"
    )
    
    # Prescripción anterior
    prior_prescription: Optional[Reference] = Field(
        None,
        description="Una orden/prescripción que está siendo reemplazada"
    )
    
    # Evento de detección
    detected_issue: Optional[List[Reference]] = Field(
        None,
        description="Problema clínico con acción"
    )
    
    # URL del evento
    event_history: Optional[List[Reference]] = Field(
        None,
        description="Una lista de eventos de interés en el ciclo de vida"
    )
    
    # Validaciones
    @validator('authored_on')
    def authored_not_future(cls, v):
        if v and v > datetime.now():
            raise ValueError('La fecha de autoría no puede ser futura')
        return v


# Modelos de request/response

class MedicationRequestCreate(BaseModel):
    """Modelo para crear una solicitud de medicamento"""
    identifier: Optional[List[Identifier]] = None
    status: MedicationRequestStatus = Field(..., description="Estado de la solicitud")
    intent: MedicationRequestIntent = Field(..., description="Intención de la solicitud")
    category: Optional[List[CodeableConcept]] = None
    priority: Optional[MedicationRequestPriority] = None
    medication_codeable_concept: Optional[CodeableConcept] = None
    medication_reference: Optional[Reference] = None
    subject: Reference = Field(..., description="Para quién es la solicitud")
    encounter: Optional[Reference] = None
    authored_on: Optional[datetime] = None
    requester: Optional[Reference] = None
    reason_code: Optional[List[CodeableConcept]] = None
    reason_reference: Optional[List[Reference]] = None
    note: Optional[List[str]] = None
    dosage_instruction: Optional[List[Dosage]] = None
    dispense_request: Optional[MedicationRequestDispenseRequest] = None


class MedicationRequestUpdate(BaseModel):
    """Modelo para actualizar una solicitud de medicamento"""
    status: Optional[MedicationRequestStatus] = None
    status_reason: Optional[CodeableConcept] = None
    priority: Optional[MedicationRequestPriority] = None
    note: Optional[List[str]] = None
    dosage_instruction: Optional[List[Dosage]] = None


class MedicationRequestResponse(MedicationRequest):
    """Modelo de respuesta de solicitud de medicamento con metadatos adicionales"""
    created_at: Optional[datetime] = Field(None, description="Fecha de creación del registro")
    updated_at: Optional[datetime] = Field(None, description="Fecha de última actualización")


class MedicationRequestSummary(BaseModel):
    """Resumen de solicitud de medicamento para listados"""
    id: str = Field(..., description="ID de la solicitud")
    status: MedicationRequestStatus
    intent: MedicationRequestIntent
    medication_codeable_concept: Optional[CodeableConcept] = None
    subject: Reference
    authored_on: Optional[datetime] = None
    requester: Optional[Reference] = None
    created_at: Optional[datetime] = None


# Modelos de búsqueda

class MedicationRequestSearchParams(BaseModel):
    """Parámetros de búsqueda de solicitudes de medicamento"""
    status: Optional[MedicationRequestStatus] = Field(None, description="Filtrar por estado")
    intent: Optional[MedicationRequestIntent] = Field(None, description="Filtrar por intención")
    priority: Optional[MedicationRequestPriority] = Field(None, description="Filtrar por prioridad")
    medication: Optional[str] = Field(None, description="Buscar por medicamento")
    subject: Optional[str] = Field(None, description="Filtrar por sujeto (paciente)")
    encounter: Optional[str] = Field(None, description="Filtrar por encuentro")
    requester: Optional[str] = Field(None, description="Filtrar por solicitante")
    authored_date: Optional[datetime] = Field(None, description="Filtrar por fecha de autoría")
    
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