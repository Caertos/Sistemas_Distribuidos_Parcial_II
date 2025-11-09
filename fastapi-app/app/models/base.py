"""
Base Models for FHIR R4
Modelos base y tipos comunes del estándar FHIR
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Union, Any, Dict
from datetime import datetime, date
from enum import Enum
import uuid


class AdministrativeGender(str, Enum):
    """Género administrativo según FHIR"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class ContactPointSystem(str, Enum):
    """Sistemas de contacto según FHIR"""
    PHONE = "phone"
    FAX = "fax"
    EMAIL = "email"
    PAGER = "pager"
    URL = "url"
    SMS = "sms"
    OTHER = "other"


class ContactPointUse(str, Enum):
    """Uso de punto de contacto según FHIR"""
    HOME = "home"
    WORK = "work"
    TEMP = "temp"
    OLD = "old"
    MOBILE = "mobile"


class AddressUse(str, Enum):
    """Uso de dirección según FHIR"""
    HOME = "home"
    WORK = "work"
    TEMP = "temp"
    OLD = "old"
    BILLING = "billing"


class AddressType(str, Enum):
    """Tipo de dirección según FHIR"""
    POSTAL = "postal"
    PHYSICAL = "physical"
    BOTH = "both"


class NameUse(str, Enum):
    """Uso de nombre según FHIR"""
    USUAL = "usual"
    OFFICIAL = "official"
    TEMP = "temp"
    NICKNAME = "nickname"
    ANONYMOUS = "anonymous"
    OLD = "old"
    MAIDEN = "maiden"


class IdentifierUse(str, Enum):
    """Uso de identificador según FHIR"""
    USUAL = "usual"
    OFFICIAL = "official"
    TEMP = "temp"
    SECONDARY = "secondary"
    OLD = "old"


class ObservationStatus(str, Enum):
    """Estado de observación según FHIR"""
    REGISTERED = "registered"
    PRELIMINARY = "preliminary"
    FINAL = "final"
    AMENDED = "amended"
    CORRECTED = "corrected"
    CANCELLED = "cancelled"
    ENTERED_IN_ERROR = "entered-in-error"
    UNKNOWN = "unknown"


class ConditionClinicalStatus(str, Enum):
    """Estado clínico de condición según FHIR"""
    ACTIVE = "active"
    RECURRENCE = "recurrence"
    RELAPSE = "relapse"
    INACTIVE = "inactive"
    REMISSION = "remission"
    RESOLVED = "resolved"


class ConditionVerificationStatus(str, Enum):
    """Estado de verificación de condición según FHIR"""
    UNCONFIRMED = "unconfirmed"
    PROVISIONAL = "provisional"
    DIFFERENTIAL = "differential"
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    ENTERED_IN_ERROR = "entered-in-error"


# Modelos base FHIR

class Period(BaseModel):
    """Período de tiempo con inicio y fin"""
    start: Optional[datetime] = Field(None, description="Fecha/hora de inicio")
    end: Optional[datetime] = Field(None, description="Fecha/hora de fin")
    
    @validator('end')
    def end_after_start(cls, v, values):
        if v and values.get('start') and v <= values['start']:
            raise ValueError('La fecha de fin debe ser posterior a la de inicio')
        return v


class Coding(BaseModel):
    """Código de un sistema de terminología"""
    system: Optional[str] = Field(None, description="Sistema de terminología")
    version: Optional[str] = Field(None, description="Versión del sistema")
    code: Optional[str] = Field(None, description="Código")
    display: Optional[str] = Field(None, description="Representación para mostrar")
    user_selected: Optional[bool] = Field(None, description="Seleccionado por el usuario")


class CodeableConcept(BaseModel):
    """Concepto codificable que puede tener múltiples códigos"""
    coding: Optional[List[Coding]] = Field(None, description="Códigos de diferentes sistemas")
    text: Optional[str] = Field(None, description="Representación en texto plano")


class Identifier(BaseModel):
    """Identificador para un recurso"""
    use: Optional[IdentifierUse] = Field(None, description="Uso del identificador")
    type: Optional[CodeableConcept] = Field(None, description="Tipo de identificador")
    system: Optional[str] = Field(None, description="Sistema del identificador")
    value: Optional[str] = Field(None, description="Valor único del identificador")
    period: Optional[Period] = Field(None, description="Período de validez")


class ContactPoint(BaseModel):
    """Información de contacto"""
    system: Optional[ContactPointSystem] = Field(None, description="Sistema de contacto")
    value: Optional[str] = Field(None, description="Valor del contacto")
    use: Optional[ContactPointUse] = Field(None, description="Uso del contacto")
    rank: Optional[int] = Field(None, ge=1, description="Preferencia de uso (1 = más alto)")
    period: Optional[Period] = Field(None, description="Período de uso")


class Address(BaseModel):
    """Dirección postal"""
    use: Optional[AddressUse] = Field(None, description="Uso de la dirección")
    type: Optional[AddressType] = Field(None, description="Tipo de dirección")
    text: Optional[str] = Field(None, description="Representación textual completa")
    line: Optional[List[str]] = Field(None, description="Líneas de dirección")
    city: Optional[str] = Field(None, description="Ciudad")
    district: Optional[str] = Field(None, description="Distrito/condado")
    state: Optional[str] = Field(None, description="Estado/provincia")
    postal_code: Optional[str] = Field(None, description="Código postal")
    country: Optional[str] = Field(None, description="País")
    period: Optional[Period] = Field(None, description="Período de uso")


class HumanName(BaseModel):
    """Nombre humano"""
    use: Optional[NameUse] = Field(None, description="Uso del nombre")
    text: Optional[str] = Field(None, description="Representación textual completa")
    family: Optional[str] = Field(None, description="Apellidos")
    given: Optional[List[str]] = Field(None, description="Nombres de pila")
    prefix: Optional[List[str]] = Field(None, description="Prefijos")
    suffix: Optional[List[str]] = Field(None, description="Sufijos")
    period: Optional[Period] = Field(None, description="Período de uso")


class Attachment(BaseModel):
    """Contenido adjunto"""
    content_type: Optional[str] = Field(None, description="Tipo MIME")
    language: Optional[str] = Field(None, description="Idioma del contenido")
    data: Optional[bytes] = Field(None, description="Datos codificados en base64")
    url: Optional[str] = Field(None, description="URL del contenido")
    size: Optional[int] = Field(None, ge=0, description="Número de bytes")
    hash: Optional[bytes] = Field(None, description="Hash SHA-1 del contenido")
    title: Optional[str] = Field(None, description="Etiqueta")
    creation: Optional[datetime] = Field(None, description="Fecha de creación")


class Quantity(BaseModel):
    """Cantidad medida o medible"""
    value: Optional[float] = Field(None, description="Valor numérico")
    comparator: Optional[str] = Field(None, description="Comparador (<, <=, >=, >)")
    unit: Optional[str] = Field(None, description="Unidad de medida")
    system: Optional[str] = Field(None, description="Sistema de unidades")
    code: Optional[str] = Field(None, description="Código de la unidad")
    
    @validator('comparator')
    def valid_comparator(cls, v):
        if v and v not in ['<', '<=', '>=', '>']:
            raise ValueError('Comparador debe ser <, <=, >=, o >')
        return v


class Range(BaseModel):
    """Rango de valores"""
    low: Optional[Quantity] = Field(None, description="Valor mínimo")
    high: Optional[Quantity] = Field(None, description="Valor máximo")


class Ratio(BaseModel):
    """Ratio entre dos cantidades"""
    numerator: Optional[Quantity] = Field(None, description="Numerador")
    denominator: Optional[Quantity] = Field(None, description="Denominador")


class Reference(BaseModel):
    """Referencia a otro recurso"""
    reference: Optional[str] = Field(None, description="Referencia literal")
    type: Optional[str] = Field(None, description="Tipo de recurso")
    identifier: Optional[Identifier] = Field(None, description="Identificador lógico")
    display: Optional[str] = Field(None, description="Texto alternativo")


class Meta(BaseModel):
    """Metadatos sobre el recurso"""
    version_id: Optional[str] = Field(None, description="ID de versión")
    last_updated: Optional[datetime] = Field(None, description="Última modificación")
    source: Optional[str] = Field(None, description="URI que identifica la fuente")
    profile: Optional[List[str]] = Field(None, description="Perfiles que declara conformidad")
    security: Optional[List[Coding]] = Field(None, description="Etiquetas de seguridad")
    tag: Optional[List[Coding]] = Field(None, description="Etiquetas")


class ResourceBase(BaseModel):
    """Clase base para todos los recursos FHIR"""
    id: Optional[str] = Field(None, description="ID lógico del recurso")
    meta: Optional[Meta] = Field(None, description="Metadatos del recurso")
    implicit_rules: Optional[str] = Field(None, description="Reglas bajo las que se construyó")
    language: Optional[str] = Field(None, description="Idioma del contenido")
    
    class Config:
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"


class DomainResourceBase(ResourceBase):
    """Clase base para recursos de dominio FHIR"""
    text: Optional[str] = Field(None, description="Narrativa generada por humanos")
    contained: Optional[List[Dict[str, Any]]] = Field(None, description="Recursos contenidos")
    extension: Optional[List[Dict[str, Any]]] = Field(None, description="Extensiones adicionales")
    modifier_extension: Optional[List[Dict[str, Any]]] = Field(None, description="Extensiones que no pueden ser ignoradas")


# Utilidades

def generate_fhir_id() -> str:
    """Generar ID compatible con FHIR"""
    return str(uuid.uuid4())


def validate_fhir_id(id_value: str) -> bool:
    """Validar formato de ID FHIR"""
    if not id_value:
        return False
    # IDs FHIR: 1-64 caracteres, [A-Za-z0-9\-\.]{1,64}
    import re
    pattern = r'^[A-Za-z0-9\-\.]{1,64}$'
    return bool(re.match(pattern, id_value))


# Modelos de respuesta comunes

class OperationOutcome(DomainResourceBase):
    """Resultado de una operación"""
    resource_type: str = Field("OperationOutcome", const=True)
    issue: List[Dict[str, Any]] = Field(..., description="Lista de problemas")


class Bundle(DomainResourceBase):
    """Colección de recursos"""
    resource_type: str = Field("Bundle", const=True)
    type: str = Field(..., description="Tipo de bundle")
    total: Optional[int] = Field(None, description="Total de recursos")
    link: Optional[List[Dict[str, Any]]] = Field(None, description="Enlaces de navegación")
    entry: Optional[List[Dict[str, Any]]] = Field(None, description="Entradas del bundle")


# Modelos de paginación

class PageInfo(BaseModel):
    """Información de paginación"""
    page: int = Field(1, ge=1, description="Página actual")
    size: int = Field(20, ge=1, le=100, description="Tamaño de página")
    total: Optional[int] = Field(None, description="Total de elementos")
    pages: Optional[int] = Field(None, description="Total de páginas")


class PaginatedResponse(BaseModel):
    """Respuesta paginada"""
    data: List[Any] = Field(..., description="Datos de la página")
    page_info: PageInfo = Field(..., description="Información de paginación")
    links: Optional[Dict[str, str]] = Field(None, description="Enlaces de navegación")