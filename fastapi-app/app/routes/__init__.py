"""
Routes Package - Endpoints API REST FHIR R4

Este paquete contiene todos los routers de FastAPI que implementan
endpoints REST compatibles con la especificación FHIR R4.

Arquitectura de Endpoints:
- Prefijos FHIR estándar: /fhir/R4/{ResourceType}
- Operaciones CRUD completas para todos los recursos
- Parámetros de búsqueda compatibles con FHIR R4
- Paginación y ordenamiento según especificación
- Manejo de errores HTTP estándar
- Metadatos y capacidades FHIR

Recursos Implementados:
- Patient: Gestión de pacientes (recurso distribuido)
- Practitioner: Gestión de profesionales (recurso de referencia)
- Observation: Gestión de observaciones clínicas (recurso distribuido)
- Condition: Gestión de condiciones médicas (recurso distribuido)
- MedicationRequest: Gestión de prescripciones (recurso distribuido)
- DiagnosticReport: Gestión de reportes diagnósticos (recurso distribuido)

Funcionalidades por Router:
- Operaciones CRUD: POST, GET, PUT/PATCH, DELETE
- Búsqueda avanzada: GET /?param=value con filtros FHIR
- Endpoints especializados: por paciente, categoría, estado, etc.
- Metadatos FHIR: GET /$metadata (CapabilityStatement)
- Validación: POST /$validate (sin persistir)

Usage:
    from app.routes import (
        patient_router,
        practitioner_router,
        observation_router,
        condition_router,
        medication_request_router,
        diagnostic_report_router
    )
    
    # Registrar en FastAPi app
    app.include_router(patient_router)
    app.include_router(practitioner_router)
    # etc.
"""

# Importar todos los routers
from .patient import router as patient_router
from .practitioner import router as practitioner_router
from .observation import router as observation_router
from .condition import router as condition_router
from .medication_request import router as medication_request_router
from .diagnostic_report import router as diagnostic_report_router

# Lista de todos los routers para registro fácil
ALL_ROUTERS = [
    patient_router,
    practitioner_router,
    observation_router,
    condition_router,
    medication_request_router,
    diagnostic_report_router
]

# Routers por tipo de recurso (distribuido vs referencia)
DISTRIBUTED_ROUTERS = [
    patient_router,
    observation_router,
    condition_router,
    medication_request_router,
    diagnostic_report_router
]

REFERENCE_ROUTERS = [
    practitioner_router
]

# Mapeo de tipos de recursos a sus routers
RESOURCE_ROUTERS = {
    "Patient": patient_router,
    "Practitioner": practitioner_router,
    "Observation": observation_router,
    "Condition": condition_router,
    "MedicationRequest": medication_request_router,
    "DiagnosticReport": diagnostic_report_router
}

def get_router_by_resource_type(resource_type: str):
    """
    Obtener router por tipo de recurso FHIR
    
    Args:
        resource_type: Tipo de recurso FHIR (Patient, Observation, etc.)
        
    Returns:
        Router de FastAPI correspondiente
        
    Raises:
        KeyError: Si el tipo de recurso no está soportado
    """
    if resource_type not in RESOURCE_ROUTERS:
        raise KeyError(f"Router not found for resource type: {resource_type}")
    return RESOURCE_ROUTERS[resource_type]

def register_all_routers(app):
    """
    Registrar todos los routers en una aplicación FastAPI
    
    Args:
        app: Instancia de FastAPI
    """
    for router in ALL_ROUTERS:
        app.include_router(router)

def get_supported_resource_types():
    """
    Obtener lista de tipos de recursos soportados
    
    Returns:
        Lista de tipos de recursos FHIR soportados
    """
    return list(RESOURCE_ROUTERS.keys())

def get_distributed_routers():
    """
    Obtener routers para recursos distribuidos
    
    Returns:
        Lista de routers de recursos distribuidos
    """
    return DISTRIBUTED_ROUTERS.copy()

def get_reference_routers():
    """
    Obtener routers para recursos de referencia
    
    Returns:
        Lista de routers de recursos de referencia
    """
    return REFERENCE_ROUTERS.copy()

# Información de endpoints por recurso
ENDPOINT_INFO = {
    "Patient": {
        "prefix": "/fhir/R4/Patient",
        "distributed": True,
        "operations": ["create", "read", "update", "delete", "search"],
        "search_params": ["name", "family", "given", "identifier", "birthdate", "gender", "phone", "email", "address"],
        "special_endpoints": ["/identifier/{value}", "/gender/{value}"]
    },
    "Practitioner": {
        "prefix": "/fhir/R4/Practitioner", 
        "distributed": False,
        "operations": ["create", "read", "update", "delete", "search"],
        "search_params": ["name", "family", "given", "identifier", "specialty"],
        "special_endpoints": ["/identifier/{value}", "/specialty/{value}", "/specialties/list"]
    },
    "Observation": {
        "prefix": "/fhir/R4/Observation",
        "distributed": True,
        "operations": ["create", "read", "update", "delete", "search"],
        "search_params": ["patient", "code", "category", "status", "date", "value-quantity", "value-string"],
        "special_endpoints": ["/patient/{id}", "/category/{value}", "/vital-signs/patient/{id}", "/laboratory/patient/{id}"]
    },
    "Condition": {
        "prefix": "/fhir/R4/Condition",
        "distributed": True,
        "operations": ["create", "read", "update", "delete", "search"],
        "search_params": ["patient", "code", "category", "clinical-status", "verification-status", "severity", "onset-date", "recorded-date"],
        "special_endpoints": ["/patient/{id}", "/patient/{id}/active", "/patient/{id}/chronic", "/category/{value}"]
    },
    "MedicationRequest": {
        "prefix": "/fhir/R4/MedicationRequest",
        "distributed": True,
        "operations": ["create", "read", "update", "delete", "search"],
        "search_params": ["patient", "medication", "status", "intent", "priority", "requester", "authored-on"],
        "special_endpoints": ["/patient/{id}", "/patient/{id}/active", "/practitioner/{id}", "/medication/{code}"]
    },
    "DiagnosticReport": {
        "prefix": "/fhir/R4/DiagnosticReport",
        "distributed": True,
        "operations": ["create", "read", "update", "delete", "search"],
        "search_params": ["patient", "code", "category", "status", "performer", "date", "issued"],
        "special_endpoints": ["/patient/{id}", "/patient/{id}/laboratory", "/patient/{id}/imaging", "/category/{value}", "/practitioner/{id}"]
    }
}

def get_endpoint_info(resource_type: str = None):
    """
    Obtener información de endpoints
    
    Args:
        resource_type: Tipo de recurso específico o None para todos
        
    Returns:
        Información de endpoints para el recurso o todos los recursos
    """
    if resource_type:
        return ENDPOINT_INFO.get(resource_type)
    return ENDPOINT_INFO.copy()

# Exportaciones principales del paquete
__all__ = [
    # Routers individuales
    "patient_router",
    "practitioner_router",
    "observation_router",
    "condition_router", 
    "medication_request_router",
    "diagnostic_report_router",
    
    # Colecciones de routers
    "ALL_ROUTERS",
    "DISTRIBUTED_ROUTERS",
    "REFERENCE_ROUTERS",
    "RESOURCE_ROUTERS",
    
    # Utilidades
    "get_router_by_resource_type",
    "register_all_routers",
    "get_supported_resource_types",
    "get_distributed_routers",
    "get_reference_routers",
    "get_endpoint_info",
    
    # Información de configuración
    "ENDPOINT_INFO"
]