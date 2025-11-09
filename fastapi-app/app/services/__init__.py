"""
Services Package - Capa de servicios de negocio para FHIR R4

Este paquete contiene todos los servicios de negocio que implementan
la lógica de operaciones CRUD y reglas de negocio específicas para
cada tipo de recurso FHIR R4.

Arquitectura de Servicios:
- BaseService: Clase base abstracta con operaciones CRUD genéricas
- DistributedService: Para recursos distribuidos co-localizados por documento_id  
- ReferenceService: Para recursos de referencia en tablas globales
- Servicios específicos: Implementaciones concretas para cada recurso FHIR

Cada servicio incluye:
- Operaciones CRUD estándar (create, read, update, delete)
- Búsqueda avanzada con filtros y paginación
- Validaciones de negocio específicas del dominio
- Transformaciones entre modelos Pydantic y ORM
- Manejo de errores con logging detallado
- Métodos especializados por tipo de recurso

Usage:
    from app.services import (
        patient_service,
        practitioner_service,
        observation_service,
        condition_service,
        medication_request_service,
        diagnostic_report_service
    )
    
    # Usar servicios en endpoints o lógica de negocio
    patient = await patient_service.get_by_id(session, patient_id)
"""

# Importar clases base
from .base import (
    BaseService,
    DistributedService, 
    ReferenceService,
    ServiceException,
    ResourceNotFoundException,
    ValidationException
)

# Importar servicios específicos y sus instancias globales
from .patient_service import PatientService, patient_service
from .practitioner_service import PractitionerService, practitioner_service
from .observation_service import ObservationService, observation_service
from .condition_service import ConditionService, condition_service
from .medication_request_service import MedicationRequestService, medication_request_service
from .diagnostic_report_service import DiagnosticReportService, diagnostic_report_service

# Servicios registrados automáticamente via SERVICES dict

# Diccionario de servicios para acceso dinámico
SERVICES = {
    "Patient": patient_service,
    "Practitioner": practitioner_service,
    "Observation": observation_service,
    "Condition": condition_service,
    "MedicationRequest": medication_request_service,
    "DiagnosticReport": diagnostic_report_service
}

# Lista de recursos distribuidos (co-localizados por documento_id)
DISTRIBUTED_RESOURCES = [
    "Patient",
    "Observation", 
    "Condition",
    "MedicationRequest",
    "DiagnosticReport"
]

# Lista de recursos de referencia (tablas globales)
REFERENCE_RESOURCES = [
    "Practitioner"
]

def get_service(resource_type: str):
    """
    Obtener servicio por tipo de recurso FHIR
    
    Args:
        resource_type: Tipo de recurso FHIR (Patient, Observation, etc.)
        
    Returns:
        Instancia del servicio correspondiente
        
    Raises:
        KeyError: Si el tipo de recurso no está soportado
    """
    if resource_type not in SERVICES:
        raise KeyError(f"Service not found for resource type: {resource_type}")
    return SERVICES[resource_type]

def is_distributed_resource(resource_type: str) -> bool:
    """
    Verificar si un recurso es distribuido (requiere documento_id)
    
    Args:
        resource_type: Tipo de recurso FHIR
        
    Returns:
        True si es distribuido, False si es de referencia
    """
    return resource_type in DISTRIBUTED_RESOURCES

def is_reference_resource(resource_type: str) -> bool:
    """
    Verificar si un recurso es de referencia (tabla global)
    
    Args:
        resource_type: Tipo de recurso FHIR
        
    Returns:
        True si es de referencia, False si es distribuido
    """
    return resource_type in REFERENCE_RESOURCES

def get_all_services():
    """
    Obtener todas las instancias de servicios
    
    Returns:
        Diccionario con todos los servicios disponibles
    """
    return SERVICES.copy()

def get_distributed_services():
    """
    Obtener servicios para recursos distribuidos
    
    Returns:
        Diccionario con servicios de recursos distribuidos
    """
    return {
        resource_type: service 
        for resource_type, service in SERVICES.items()
        if resource_type in DISTRIBUTED_RESOURCES
    }

def get_reference_services():
    """
    Obtener servicios para recursos de referencia
    
    Returns:
        Diccionario con servicios de recursos de referencia
    """
    return {
        resource_type: service 
        for resource_type, service in SERVICES.items()
        if resource_type in REFERENCE_RESOURCES
    }

# Exportaciones principales del paquete
__all__ = [
    # Clases base
    "BaseService",
    "DistributedService", 
    "ReferenceService",
    "ServiceException",
    "ResourceNotFoundException",
    "ValidationException",
    "service_registry",
    
    # Clases de servicios específicos
    "PatientService",
    "PractitionerService", 
    "ObservationService",
    "ConditionService",
    "MedicationRequestService",
    "DiagnosticReportService",
    
    # Instancias globales de servicios (recomendado para uso)
    "patient_service",
    "practitioner_service",
    "observation_service", 
    "condition_service",
    "medication_request_service",
    "diagnostic_report_service",
    
    # Utilidades y configuración
    "SERVICES",
    "DISTRIBUTED_RESOURCES",
    "REFERENCE_RESOURCES",
    "get_service",
    "is_distributed_resource",
    "is_reference_resource", 
    "get_all_services",
    "get_distributed_services",
    "get_reference_services"
]