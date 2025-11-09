"""
Patient Model - FHIR R4
Modelo de Paciente basado en estándar FHIR R4
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union, Literal
from datetime import datetime, date

from .base import (
    DomainResourceBase, 
    HumanName, 
    Identifier, 
    ContactPoint, 
    Address,
    AdministrativeGender,
    CodeableConcept,
    Reference,
    Attachment,
    Period
)


class PatientContact(BaseModel):
    """Contacto del paciente (persona relacionada)"""
    relationship: Optional[List[CodeableConcept]] = Field(None, description="Relación con el paciente")
    name: Optional[HumanName] = Field(None, description="Nombre del contacto")
    telecom: Optional[List[ContactPoint]] = Field(None, description="Información de contacto")
    address: Optional[Address] = Field(None, description="Dirección del contacto")
    gender: Optional[AdministrativeGender] = Field(None, description="Género del contacto")
    organization: Optional[Reference] = Field(None, description="Organización del contacto")
    period: Optional[Period] = Field(None, description="Período de contacto")


class PatientCommunication(BaseModel):
    """Idiomas de comunicación del paciente"""
    language: CodeableConcept = Field(..., description="Idioma de comunicación")
    preferred: Optional[bool] = Field(None, description="Idioma preferido")


class PatientLink(BaseModel):
    """Enlaces a otros pacientes (fusión, etc.)"""
    other: Reference = Field(..., description="Referencia al otro paciente")
    type: str = Field(..., description="Tipo de enlace: replaced-by, replaces, refer, seealso")
    
    @validator('type')
    def valid_link_type(cls, v):
        valid_types = ['replaced-by', 'replaces', 'refer', 'seealso']
        if v not in valid_types:
            raise ValueError(f'Tipo de enlace debe ser uno de: {valid_types}')
        return v


class Patient(DomainResourceBase):
    """
    Modelo de Paciente FHIR R4
    
    Representa información sobre un individuo que recibe atención médica
    """
    resource_type: Literal["Patient"] = "Patient"
    
    # Identificadores
    identifier: Optional[List[Identifier]] = Field(
        None, 
        description="Identificadores del paciente (CC, pasaporte, historia clínica, etc.)"
    )
    
    # Estado activo
    active: Optional[bool] = Field(
        True, 
        description="Si el registro del paciente está activo"
    )
    
    # Nombres
    name: Optional[List[HumanName]] = Field(
        None, 
        description="Nombres del paciente"
    )
    
    # Contacto
    telecom: Optional[List[ContactPoint]] = Field(
        None, 
        description="Información de contacto del paciente"
    )
    
    # Género
    gender: Optional[AdministrativeGender] = Field(
        None, 
        description="Género administrativo"
    )
    
    # Fecha de nacimiento
    birth_date: Optional[date] = Field(
        None, 
        description="Fecha de nacimiento"
    )
    
    # Estado vital
    deceased_boolean: Optional[bool] = Field(
        None, 
        description="Indica si el paciente ha fallecido"
    )
    deceased_date_time: Optional[datetime] = Field(
        None, 
        description="Fecha y hora de fallecimiento"
    )
    
    # Direcciones
    address: Optional[List[Address]] = Field(
        None, 
        description="Direcciones del paciente"
    )
    
    # Estado marital
    marital_status: Optional[CodeableConcept] = Field(
        None, 
        description="Estado civil"
    )
    
    # Múltiples nacimientos
    multiple_birth_boolean: Optional[bool] = Field(
        None, 
        description="Indica si es parte de un nacimiento múltiple"
    )
    multiple_birth_integer: Optional[int] = Field(
        None, 
        ge=1,
        description="Orden en nacimiento múltiple"
    )
    
    # Foto
    photo: Optional[List[Attachment]] = Field(
        None, 
        description="Fotografías del paciente"
    )
    
    # Contactos
    contact: Optional[List[PatientContact]] = Field(
        None, 
        description="Contactos del paciente"
    )
    
    # Comunicación
    communication: Optional[List[PatientCommunication]] = Field(
        None, 
        description="Idiomas de comunicación"
    )
    
    # Médicos generales
    general_practitioner: Optional[List[Reference]] = Field(
        None, 
        description="Médicos de cabecera"
    )
    
    # Organización gestora
    managing_organization: Optional[Reference] = Field(
        None, 
        description="Organización que gestiona el registro"
    )
    
    # Enlaces
    link: Optional[List[PatientLink]] = Field(
        None, 
        description="Enlaces con otros registros de paciente"
    )
    
    # Validaciones
    @validator('birth_date')
    def birth_date_not_future(cls, v):
        if v and v > date.today():
            raise ValueError('La fecha de nacimiento no puede ser futura')
        return v
    
    @validator('deceased_date_time')
    def deceased_date_not_future(cls, v):
        if v and v > datetime.now():
            raise ValueError('La fecha de fallecimiento no puede ser futura')
        return v
    
    @validator('deceased_date_time')
    def deceased_consistent(cls, v, values):
        if v and values.get('deceased_boolean') is False:
            raise ValueError('No se puede especificar fecha de fallecimiento si deceased_boolean es False')
        return v
    
    @validator('multiple_birth_integer')
    def multiple_birth_consistent(cls, v, values):
        if v and values.get('multiple_birth_boolean') is False:
            raise ValueError('No se puede especificar orden de nacimiento si multiple_birth_boolean es False')
        return v


# Modelos de request/response

class PatientCreate(BaseModel):
    """Modelo para crear un paciente"""
    identifier: Optional[List[Identifier]] = None
    active: bool = True
    name: List[HumanName] = Field(..., min_items=1, description="Al menos un nombre es requerido")
    telecom: Optional[List[ContactPoint]] = None
    gender: Optional[AdministrativeGender] = None
    birth_date: Optional[date] = None
    address: Optional[List[Address]] = None
    marital_status: Optional[CodeableConcept] = None
    contact: Optional[List[PatientContact]] = None
    communication: Optional[List[PatientCommunication]] = None
    
    @validator('birth_date')
    def birth_date_not_future(cls, v):
        if v and v > date.today():
            raise ValueError('La fecha de nacimiento no puede ser futura')
        return v


class PatientUpdate(BaseModel):
    """Modelo para actualizar un paciente"""
    identifier: Optional[List[Identifier]] = None
    active: Optional[bool] = None
    name: Optional[List[HumanName]] = None
    telecom: Optional[List[ContactPoint]] = None
    gender: Optional[AdministrativeGender] = None
    birth_date: Optional[date] = None
    address: Optional[List[Address]] = None
    marital_status: Optional[CodeableConcept] = None
    contact: Optional[List[PatientContact]] = None
    communication: Optional[List[PatientCommunication]] = None
    
    @validator('birth_date')
    def birth_date_not_future(cls, v):
        if v and v > date.today():
            raise ValueError('La fecha de nacimiento no puede ser futura')
        return v


class PatientResponse(Patient):
    """Modelo de respuesta de paciente con metadatos adicionales"""
    created_at: Optional[datetime] = Field(None, description="Fecha de creación del registro")
    updated_at: Optional[datetime] = Field(None, description="Fecha de última actualización")


class PatientSummary(BaseModel):
    """Resumen de paciente para listados"""
    id: str = Field(..., description="ID del paciente")
    identifier: Optional[List[Identifier]] = None
    active: bool = Field(True, description="Estado activo")
    name: Optional[List[HumanName]] = None
    gender: Optional[AdministrativeGender] = None
    birth_date: Optional[date] = None
    deceased_boolean: Optional[bool] = None
    created_at: Optional[datetime] = None


# Modelos de búsqueda

class PatientSearchParams(BaseModel):
    """Parámetros de búsqueda de pacientes"""
    active: Optional[bool] = Field(None, description="Filtrar por estado activo")
    name: Optional[str] = Field(None, description="Buscar por nombre (texto libre)")
    family: Optional[str] = Field(None, description="Buscar por apellido")
    given: Optional[str] = Field(None, description="Buscar por nombre de pila")
    identifier: Optional[str] = Field(None, description="Buscar por identificador")
    gender: Optional[AdministrativeGender] = Field(None, description="Filtrar por género")
    birthdate: Optional[date] = Field(None, description="Filtrar por fecha de nacimiento")
    deceased: Optional[bool] = Field(None, description="Filtrar por estado de fallecimiento")
    
    # Parámetros de paginación
    page: int = Field(1, ge=1, description="Número de página")
    size: int = Field(20, ge=1, le=100, description="Tamaño de página")
    
    # Ordenamiento
    sort: Optional[str] = Field(None, description="Campo de ordenamiento")
    order: Optional[str] = Field("asc", description="Orden: asc o desc")
    
    @validator('order')
    def valid_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('El orden debe ser "asc" o "desc"')
        return v