"""
ORM Models Package - SQLAlchemy Models for FHIR Resources
Modelos ORM optimizados para base de datos distribuida Citus
"""

# Importar la base y configuraciones
from .base import (
    Base,
    BaseModel,
    DistributedModel,
    ReferenceModel,
    CitusTableConfig,
    UUIDMixin,
    UUIDFieldMixin,
    AuditMixin,
    SoftDeleteMixin,
    FHIRResourceMixin,
    get_table_comment,
    create_composite_primary_key,
    FHIRStatus,
    CommonIndexes
)

# Importar todos los modelos para SQLAlchemy
from .base import Base
from .patient import PatientORM
from .practitioner import PractitionerORM
from .observation import ObservationORM
from .condition import ConditionORM
from .medication_request import MedicationRequestORM
from .diagnostic_report import DiagnosticReportORM
from .admission import AdmissionORM
from .auth import (
    UserORM, RoleORM, PermissionORM,
    RefreshTokenORM, APIKeyORM
)
from .audit import (
    AuditLogORM, SystemMetricsORM, AlertORM
)

# Importar modelos pydantic para aliases
from app.models.patient import Patient
from app.models.practitioner import Practitioner
from app.models.observation import Observation
from app.models.condition import Condition
from app.models.medication_request import MedicationRequest
from app.models.diagnostic_report import DiagnosticReport

# Importar modelos de autenticación
from .auth import (
    UserORM,
    RoleORM, 
    PermissionORM,
    RefreshTokenORM,
    APIKeyORM,
    user_roles,
    role_permissions,
    create_default_roles,
    create_default_permissions
)

# Lista de todos los modelos ORM principales
ORM_MODELS = [
    PatientORM,
    PractitionerORM,
    ObservationORM,
    ConditionORM,
    MedicationRequestORM,
    DiagnosticReportORM,
    AdmissionORM
]

# Lista de modelos de autenticación
AUTH_MODELS = [
    UserORM,
    RoleORM,
    PermissionORM,
    RefreshTokenORM,
    APIKeyORM
]

# Lista de modelos de auditoría
AUDIT_MODELS = [
    AuditLogORM,
    SystemMetricsORM,
    AlertORM
]

# Lista de modelos distribuidos (por documento_id)
DISTRIBUTED_MODELS = [
    PatientORM,
    ObservationORM,
    ConditionORM,
    MedicationRequestORM,
    DiagnosticReportORM,
    AdmissionORM
]

# Lista de modelos de referencia (replicados)
REFERENCE_MODELS = [
    PractitionerORM
]

# Mapeo de nombres de tabla a modelos ORM
TABLE_MODEL_MAP = {
    "paciente": PatientORM,
    "profesional": PractitionerORM,
    "observacion": ObservationORM,
    "condicion": ConditionORM,
    "medicamento": MedicationRequestORM,
    "resultado_laboratorio": DiagnosticReportORM,
    "admision": AdmissionORM
}

# Mapeo de tipos de recursos FHIR a modelos ORM
FHIR_RESOURCE_MAP = {
    "Patient": PatientORM,
    "Practitioner": PractitionerORM,
    "Observation": ObservationORM,
    "Condition": ConditionORM,
    "MedicationRequest": MedicationRequestORM,
    "DiagnosticReport": DiagnosticReportORM
}

# Aliases para facilitar las importaciones
RESOURCE_ALIASES = {
    "Patient": Patient,
    "Practitioner": Practitioner,
    "Observation": Observation,
    "Condition": Condition,
    "MedicationRequest": MedicationRequest,
    "DiagnosticReport": DiagnosticReport
}


def get_orm_model_by_table(table_name: str):
    """
    Obtiene el modelo ORM por nombre de tabla
    
    Args:
        table_name: Nombre de la tabla en la base de datos
    
    Returns:
        Clase del modelo ORM o None si no se encuentra
    """
    return TABLE_MODEL_MAP.get(table_name)


def get_orm_model_by_fhir_type(fhir_type: str):
    """
    Obtiene el modelo ORM por tipo de recurso FHIR
    
    Args:
        fhir_type: Tipo de recurso FHIR (ej: "Patient", "Observation")
    
    Returns:
        Clase del modelo ORM o None si no se encuentra
    """
    return FHIR_RESOURCE_MAP.get(fhir_type)


def get_distributed_models():
    """
    Obtiene todos los modelos distribuidos por documento_id
    
    Returns:
        Lista de clases de modelos distribuidos
    """
    return DISTRIBUTED_MODELS.copy()


def get_reference_models():
    """
    Obtiene todos los modelos de referencia (replicados)
    
    Returns:
        Lista de clases de modelos de referencia
    """
    return REFERENCE_MODELS.copy()


def get_all_table_names():
    """
    Obtiene todos los nombres de tablas mapeados
    
    Returns:
        Lista de nombres de tablas
    """
    return list(TABLE_MODEL_MAP.keys())


def get_all_fhir_types():
    """
    Obtiene todos los tipos de recursos FHIR mapeados
    
    Returns:
        Lista de tipos de recursos FHIR
    """
    return list(FHIR_RESOURCE_MAP.keys())


def is_distributed_model(model_class):
    """
    Verifica si un modelo es distribuido
    
    Args:
        model_class: Clase del modelo a verificar
    
    Returns:
        True si el modelo es distribuido, False en caso contrario
    """
    return model_class in DISTRIBUTED_MODELS


def is_reference_model(model_class):
    """
    Verifica si un modelo es de referencia
    
    Args:
        model_class: Clase del modelo a verificar
    
    Returns:
        True si el modelo es de referencia, False en caso contrario
    """
    return model_class in REFERENCE_MODELS


class ORMUtils:
    """Utilidades para trabajar con los modelos ORM"""
    
    @staticmethod
    def create_all_tables(engine, checkfirst=True):
        """
        Crea todas las tablas definidas en los modelos
        
        Args:
            engine: SQLAlchemy engine
            checkfirst: Si verificar primero si las tablas existen
        """
        Base.metadata.create_all(bind=engine, checkfirst=checkfirst)
    
    @staticmethod
    def drop_all_tables(engine):
        """
        Elimina todas las tablas definidas en los modelos
        
        Args:
            engine: SQLAlchemy engine
        """
        Base.metadata.drop_all(bind=engine)
    
    @staticmethod
    def get_table_info():
        """
        Obtiene información de todas las tablas definidas
        
        Returns:
            Diccionario con información de tablas
        """
        table_info = {}
        
        for table_name, model_class in TABLE_MODEL_MAP.items():
            table_info[table_name] = {
                "model_class": model_class.__name__,
                "fhir_type": None,
                "is_distributed": is_distributed_model(model_class),
                "is_reference": is_reference_model(model_class),
                "primary_key": [col.name for col in model_class.__table__.primary_key.columns],
                "column_count": len(model_class.__table__.columns),
                "index_count": len(model_class.__table__.indexes)
            }
            
            # Buscar el tipo FHIR correspondiente
            for fhir_type, orm_model in FHIR_RESOURCE_MAP.items():
                if orm_model == model_class:
                    table_info[table_name]["fhir_type"] = fhir_type
                    break
        
        return table_info
    
    @staticmethod
    def validate_citus_configuration():
        """
        Valida que la configuración de Citus sea correcta
        
        Returns:
            Lista de advertencias/errores de configuración
        """
        issues = []
        
        # Verificar que los modelos distribuidos tengan documento_id
        for model in DISTRIBUTED_MODELS:
            if not hasattr(model, 'documento_id'):
                issues.append(f"Modelo distribuido {model.__name__} no tiene campo documento_id")
            
            # Verificar que documento_id esté en la primary key
            pk_columns = [col.name for col in model.__table__.primary_key.columns]
            if 'documento_id' not in pk_columns:
                issues.append(f"Modelo distribuido {model.__name__} no incluye documento_id en PK")
        
        # Verificar que los modelos de referencia no tengan documento_id
        for model in REFERENCE_MODELS:
            if hasattr(model, 'documento_id'):
                issues.append(f"Modelo de referencia {model.__name__} no debería tener documento_id")
        
        return issues


# Exportaciones del módulo
__all__ = [
    # Clases base
    "Base",
    "BaseModel",
    "DistributedModel",
    "ReferenceModel",
    "CitusTableConfig",
    "UUIDMixin",
    "AuditMixin",
    "SoftDeleteMixin",
    "FHIRResourceMixin",
    
    # Funciones utilitarias base
    "get_table_comment",
    "create_composite_primary_key",
    "FHIRStatus",
    "CommonIndexes",
    
    # Modelos ORM
    "PatientORM",
    "Patient",
    "PractitionerORM", 
    "Practitioner",
    "ObservationORM",
    "Observation",
    "ConditionORM",
    "Condition",
    "MedicationRequestORM",
    "MedicationRequest",
    "DiagnosticReportORM",
    "DiagnosticReport",
    "AdmissionORM",
    
    # Listas de modelos
    "ORM_MODELS",
    "DISTRIBUTED_MODELS",
    "REFERENCE_MODELS",
    
    # Mapeos
    "TABLE_MODEL_MAP",
    "FHIR_RESOURCE_MAP",
    "RESOURCE_ALIASES",
    
    # Funciones utilitarias
    "get_orm_model_by_table",
    "get_orm_model_by_fhir_type",
    "get_distributed_models",
    "get_reference_models",
    "get_all_table_names",
    "get_all_fhir_types",
    "is_distributed_model",
    "is_reference_model",
    
    # Clase de utilidades
    "ORMUtils"
]