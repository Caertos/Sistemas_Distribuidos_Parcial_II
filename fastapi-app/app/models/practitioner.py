"""
Practitioner Model - FHIR R4
Modelo de Profesional de la Salud basado en estándar FHIR R4
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date

from .base import (
    DomainResourceBase,
    HumanName,
    Identifier,
    ContactPoint,
    Address,
    AdministrativeGender,
    CodeableConcept,
    Period,
    Attachment
)


class PractitionerQualification(BaseModel):
    """Calificación profesional"""
    identifier: Optional[List[Identifier]] = Field(None, description="Identificadores de la calificación")
    code: CodeableConcept = Field(..., description="Código de la calificación")
    period: Optional[Period] = Field(None, description="Período de validez")
    issuer: Optional[str] = Field(None, description="Organización que emitió la calificación")


class Practitioner(DomainResourceBase):
    """
    Modelo de Profesional de la Salud FHIR R4
    
    Representa una persona involucrada formalmente en la provisión de atención médica
    """
    resource_type: str = Field("Practitioner", const=True)
    
    # Identificadores
    identifier: Optional[List[Identifier]] = Field(
        None,
        description="Identificadores del profesional (registro médico, cédula, etc.)"
    )
    
    # Estado activo
    active: Optional[bool] = Field(
        True,
        description="Si el registro del profesional está activo"
    )
    
    # Nombres
    name: Optional[List[HumanName]] = Field(
        None,
        description="Nombres del profesional"
    )
    
    # Contacto
    telecom: Optional[List[ContactPoint]] = Field(
        None,
        description="Información de contacto del profesional"
    )
    
    # Direcciones
    address: Optional[List[Address]] = Field(
        None,
        description="Direcciones del profesional"
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
    
    # Foto
    photo: Optional[List[Attachment]] = Field(
        None,
        description="Fotografías del profesional"
    )
    
    # Calificaciones
    qualification: Optional[List[PractitionerQualification]] = Field(
        None,
        description="Certificaciones, licencias y educación"
    )
    
    # Idiomas de comunicación
    communication: Optional[List[CodeableConcept]] = Field(
        None,
        description="Idiomas que puede usar para comunicarse"
    )
    
    # Validaciones
    @validator('birth_date')
    def birth_date_not_future(cls, v):
        if v and v > date.today():
            raise ValueError('La fecha de nacimiento no puede ser futura')
        return v


# Modelos de request/response

class PractitionerCreate(BaseModel):
    """Modelo para crear un profesional"""
    identifier: Optional[List[Identifier]] = None
    active: bool = True
    name: List[HumanName] = Field(..., min_items=1, description="Al menos un nombre es requerido")
    telecom: Optional[List[ContactPoint]] = None
    address: Optional[List[Address]] = None
    gender: Optional[AdministrativeGender] = None
    birth_date: Optional[date] = None
    qualification: Optional[List[PractitionerQualification]] = None
    communication: Optional[List[CodeableConcept]] = None
    
    @validator('birth_date')
    def birth_date_not_future(cls, v):
        if v and v > date.today():
            raise ValueError('La fecha de nacimiento no puede ser futura')
        return v


class PractitionerUpdate(BaseModel):
    """Modelo para actualizar un profesional"""
    identifier: Optional[List[Identifier]] = None
    active: Optional[bool] = None
    name: Optional[List[HumanName]] = None
    telecom: Optional[List[ContactPoint]] = None
    address: Optional[List[Address]] = None
    gender: Optional[AdministrativeGender] = None
    birth_date: Optional[date] = None
    qualification: Optional[List[PractitionerQualification]] = None
    communication: Optional[List[CodeableConcept]] = None


class PractitionerResponse(Practitioner):
    """Modelo de respuesta de profesional con metadatos adicionales"""
    created_at: Optional[datetime] = Field(None, description="Fecha de creación del registro")
    updated_at: Optional[datetime] = Field(None, description="Fecha de última actualización")


class PractitionerSummary(BaseModel):
    """Resumen de profesional para listados"""
    id: str = Field(..., description="ID del profesional")
    identifier: Optional[List[Identifier]] = None
    active: bool = Field(True, description="Estado activo")
    name: Optional[List[HumanName]] = None
    gender: Optional[AdministrativeGender] = None
    qualification: Optional[List[PractitionerQualification]] = None
    created_at: Optional[datetime] = None


# Modelos de búsqueda

class PractitionerSearchParams(BaseModel):
    """Parámetros de búsqueda de profesionales"""
    active: Optional[bool] = Field(None, description="Filtrar por estado activo")
    name: Optional[str] = Field(None, description="Buscar por nombre (texto libre)")
    family: Optional[str] = Field(None, description="Buscar por apellido")
    given: Optional[str] = Field(None, description="Buscar por nombre de pila")
    identifier: Optional[str] = Field(None, description="Buscar por identificador")
    gender: Optional[AdministrativeGender] = Field(None, description="Filtrar por género")
    specialty: Optional[str] = Field(None, description="Buscar por especialidad")
    
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