"""
Modelos FHIR R4 para la aplicación FastAPI
Incluye todos los recursos FHIR implementados
"""

# Modelos base
from .base import (
    # Enums base
    AdministrativeGender,
    NameUse,
    AddressUse,
    AddressType,
    ContactPointSystem,
    ContactPointUse,
    IdentifierUse,
    ObservationStatus,
    ConditionClinicalStatus,
    ConditionVerificationStatus,
    
    # Clases base
    ResourceBase,
    DomainResourceBase,
    Meta,
    
    # Tipos complejos
    HumanName,
    Address,
    ContactPoint,
    Identifier,
    CodeableConcept,
    Coding,
    Reference,
    Period,
    Quantity,
    Range,
    Ratio,
    Attachment,
    
    # Utilidades
    generate_fhir_id,
    validate_fhir_id,
    
    # Modelos de respuesta
    OperationOutcome,
    Bundle,
    PageInfo,
    PaginatedResponse
)

# Modelo Patient
from .patient import (
    # Clases específicas
    PatientContact,
    PatientCommunication,
    PatientLink,
    
    # Modelo principal
    Patient,
    
    # Modelos de request/response
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientSummary,
    PatientSearchParams
)

# Modelo Practitioner
from .practitioner import (
    # Clases específicas
    PractitionerQualification,
    
    # Modelo principal
    Practitioner,
    
    # Modelos de request/response
    PractitionerCreate,
    PractitionerUpdate,
    PractitionerResponse,
    PractitionerSummary,
    PractitionerSearchParams
)

# Modelo Observation
from .observation import (
    # Clases específicas
    ObservationReferenceRange,
    ObservationComponent,
    
    # Modelo principal
    Observation,
    
    # Modelos de request/response
    ObservationCreate,
    ObservationUpdate,
    ObservationResponse,
    ObservationSummary,
    ObservationSearchParams
)

# Modelo Condition
from .condition import (
    # Clases específicas
    ConditionStage,
    ConditionEvidence,
    
    # Modelo principal
    Condition,
    
    # Modelos de request/response
    ConditionCreate,
    ConditionUpdate,
    ConditionResponse,
    ConditionSummary,
    ConditionSearchParams
)

# Modelo MedicationRequest
from .medication_request import (
    # Enums específicos
    MedicationRequestStatus,
    MedicationRequestIntent,
    MedicationRequestPriority,
    
    # Clases específicas
    Dosage,
    MedicationRequestSubstitution,
    MedicationRequestDispenseRequest,
    
    # Modelo principal
    MedicationRequest,
    
    # Modelos de request/response
    MedicationRequestCreate,
    MedicationRequestUpdate,
    MedicationRequestResponse,
    MedicationRequestSummary,
    MedicationRequestSearchParams
)

# Modelo DiagnosticReport
from .diagnostic_report import (
    # Enums específicos
    DiagnosticReportStatus,
    
    # Clases específicas
    DiagnosticReportMedia,
    
    # Modelo principal
    DiagnosticReport,
    
    # Modelos de request/response
    DiagnosticReportCreate,
    DiagnosticReportUpdate,
    DiagnosticReportResponse,
    DiagnosticReportSummary,
    DiagnosticReportSearchParams,
    
    # Utilidades
    DiagnosticReportUtility,
    DiagnosticReportCategories
)

# Lista de todos los modelos FHIR principales
FHIR_MODELS = [
    Patient,
    Practitioner,
    Observation,
    Condition,
    MedicationRequest,
    DiagnosticReport
]

# Lista de todos los modelos de creación
CREATE_MODELS = [
    PatientCreate,
    PractitionerCreate,
    ObservationCreate,
    ConditionCreate,
    MedicationRequestCreate,
    DiagnosticReportCreate
]

# Lista de todos los modelos de actualización
UPDATE_MODELS = [
    PatientUpdate,
    PractitionerUpdate,
    ObservationUpdate,
    ConditionUpdate,
    MedicationRequestUpdate,
    DiagnosticReportUpdate
]

# Lista de todos los modelos de respuesta
RESPONSE_MODELS = [
    PatientResponse,
    PractitionerResponse,
    ObservationResponse,
    ConditionResponse,
    MedicationRequestResponse,
    DiagnosticReportResponse
]

# Lista de todos los modelos de resumen
SUMMARY_MODELS = [
    PatientSummary,
    PractitionerSummary,
    ObservationSummary,
    ConditionSummary,
    MedicationRequestSummary,
    DiagnosticReportSummary
]

# Lista de todos los modelos de búsqueda
SEARCH_MODELS = [
    PatientSearchParams,
    PractitionerSearchParams,
    ObservationSearchParams,
    ConditionSearchParams,
    MedicationRequestSearchParams,
    DiagnosticReportSearchParams
]

# Mapeo de tipos de recursos a modelos
RESOURCE_TYPE_MAP = {
    "Patient": Patient,
    "Practitioner": Practitioner,
    "Observation": Observation,
    "Condition": Condition,
    "MedicationRequest": MedicationRequest,
    "DiagnosticReport": DiagnosticReport
}

# Mapeo de tipos de recursos a modelos de creación
CREATE_MODEL_MAP = {
    "Patient": PatientCreate,
    "Practitioner": PractitionerCreate,
    "Observation": ObservationCreate,
    "Condition": ConditionCreate,
    "MedicationRequest": MedicationRequestCreate,
    "DiagnosticReport": DiagnosticReportCreate
}

# Mapeo de tipos de recursos a modelos de actualización
UPDATE_MODEL_MAP = {
    "Patient": PatientUpdate,
    "Practitioner": PractitionerUpdate,
    "Observation": ObservationUpdate,
    "Condition": ConditionUpdate,
    "MedicationRequest": MedicationRequestUpdate,
    "DiagnosticReport": DiagnosticReportUpdate
}

# Mapeo de tipos de recursos a modelos de respuesta
RESPONSE_MODEL_MAP = {
    "Patient": PatientResponse,
    "Practitioner": PractitionerResponse,
    "Observation": ObservationResponse,
    "Condition": ConditionResponse,
    "MedicationRequest": MedicationRequestResponse,
    "DiagnosticReport": DiagnosticReportResponse
}

# Mapeo de tipos de recursos a modelos de búsqueda
SEARCH_MODEL_MAP = {
    "Patient": PatientSearchParams,
    "Practitioner": PractitionerSearchParams,
    "Observation": ObservationSearchParams,
    "Condition": ConditionSearchParams,
    "MedicationRequest": MedicationRequestSearchParams,
    "DiagnosticReport": DiagnosticReportSearchParams
}

# Función auxiliar para obtener modelo por tipo de recurso
def get_model_by_resource_type(resource_type: str, model_type: str = "main"):
    """
    Obtiene un modelo basado en el tipo de recurso y tipo de modelo
    
    Args:
        resource_type: Tipo de recurso FHIR (ej: "Patient", "Observation")
        model_type: Tipo de modelo ("main", "create", "update", "response", "search")
    
    Returns:
        Clase del modelo correspondiente o None si no se encuentra
    """
    mapping = {
        "main": RESOURCE_TYPE_MAP,
        "create": CREATE_MODEL_MAP,
        "update": UPDATE_MODEL_MAP,
        "response": RESPONSE_MODEL_MAP,
        "search": SEARCH_MODEL_MAP
    }
    
    return mapping.get(model_type, {}).get(resource_type)


# Función auxiliar para validar tipo de recurso
def is_valid_resource_type(resource_type: str) -> bool:
    """
    Verifica si un tipo de recurso es válido
    
    Args:
        resource_type: Tipo de recurso a validar
    
    Returns:
        True si es válido, False en caso contrario
    """
    return resource_type in RESOURCE_TYPE_MAP


# Función auxiliar para obtener todos los tipos de recursos disponibles
def get_available_resource_types() -> list:
    """
    Obtiene lista de todos los tipos de recursos disponibles
    
    Returns:
        Lista de strings con los tipos de recursos
    """
    return list(RESOURCE_TYPE_MAP.keys())


__all__ = [
    # Modelos base
    "AdministrativeGender",
    "NameUse",
    "AddressUse", 
    "AddressType",
    "ContactPointSystem",
    "ContactPointUse",
    "IdentifierUse",
    "ObservationStatus",
    "ConditionClinicalStatus",
    "ConditionVerificationStatus",
    "ResourceBase",
    "DomainResourceBase",
    "Meta",
    "HumanName",
    "Address",
    "ContactPoint",
    "Identifier",
    "CodeableConcept",
    "Coding",
    "Reference",
    "Period",
    "Quantity",
    "Range",
    "Ratio",
    "Attachment",
    "generate_fhir_id",
    "validate_fhir_id",
    "OperationOutcome",
    "Bundle",
    "PageInfo",
    "PaginatedResponse",
    
    # Modelos Patient
    "PatientContact",
    "PatientCommunication",
    "PatientLink",
    "Patient",
    "PatientCreate",
    "PatientUpdate",
    "PatientResponse",
    "PatientSummary",
    "PatientSearchParams",
    
    # Modelos Practitioner
    "PractitionerQualification",
    "Practitioner",
    "PractitionerCreate",
    "PractitionerUpdate",
    "PractitionerResponse",
    "PractitionerSummary",
    "PractitionerSearchParams",
    
    # Modelos Observation
    "ObservationReferenceRange",
    "ObservationComponent",
    "Observation",
    "ObservationCreate",
    "ObservationUpdate",
    "ObservationResponse",
    "ObservationSummary",
    "ObservationSearchParams",
    
    # Modelos Condition
    "ConditionStage",
    "ConditionEvidence",
    "Condition",
    "ConditionCreate",
    "ConditionUpdate",
    "ConditionResponse",
    "ConditionSummary",
    "ConditionSearchParams",
    
    # Modelos MedicationRequest
    "MedicationRequestStatus",
    "MedicationRequestIntent",
    "MedicationRequestPriority",
    "Dosage",
    "MedicationRequestSubstitution",
    "MedicationRequestDispenseRequest",
    "MedicationRequest",
    "MedicationRequestCreate",
    "MedicationRequestUpdate",
    "MedicationRequestResponse",
    "MedicationRequestSummary",
    "MedicationRequestSearchParams",
    
    # Modelos DiagnosticReport
    "DiagnosticReportStatus",
    "DiagnosticReportMedia",
    "DiagnosticReport",
    "DiagnosticReportCreate",
    "DiagnosticReportUpdate",
    "DiagnosticReportResponse",
    "DiagnosticReportSummary",
    "DiagnosticReportSearchParams",
    "DiagnosticReportUtility",
    "DiagnosticReportCategories",
    
    # Listas y mapeos
    "FHIR_MODELS",
    "CREATE_MODELS",
    "UPDATE_MODELS",
    "RESPONSE_MODELS",
    "SUMMARY_MODELS",
    "SEARCH_MODELS",
    "RESOURCE_TYPE_MAP",
    "CREATE_MODEL_MAP",
    "UPDATE_MODEL_MAP",
    "RESPONSE_MODEL_MAP",
    "SEARCH_MODEL_MAP",
    
    # Funciones auxiliares
    "get_model_by_resource_type",
    "is_valid_resource_type",
    "get_available_resource_types"
]