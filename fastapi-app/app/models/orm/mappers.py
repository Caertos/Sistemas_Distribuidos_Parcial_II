"""
Model Mappers - Utilidades para convertir entre modelos Pydantic y ORM
Transformaciones bidireccionales optimizadas para recursos FHIR
"""

from typing import Dict, Any, Optional, List, Type, Union
from datetime import datetime, date
import uuid

# Importar modelos Pydantic
from app.models import (
    Patient as PydanticPatient,
    Practitioner as PydanticPractitioner,
    Observation as PydanticObservation,
    Condition as PydanticCondition,
    MedicationRequest as PydanticMedicationRequest,
    DiagnosticReport as PydanticDiagnosticReport,
    PatientCreate,
    PractitionerCreate,
    ObservationCreate,
    ConditionCreate,
    MedicationRequestCreate,
    DiagnosticReportCreate
)

# Importar modelos ORM
from . import (
    PatientORM,
    PractitionerORM,
    ObservationORM,
    ConditionORM,
    MedicationRequestORM,
    DiagnosticReportORM
)


class ModelMapper:
    """Clase base para mappers bidireccionales entre Pydantic y ORM"""
    
    @staticmethod
    def safe_datetime_conversion(value: Any) -> Optional[datetime]:
        """
        Convierte de forma segura un valor a datetime
        
        Args:
            value: Valor a convertir (str, datetime, etc.)
        
        Returns:
            datetime object o None si no se puede convertir
        """
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            try:
                # Intentar diferentes formatos
                for fmt in [
                    '%Y-%m-%dT%H:%M:%S.%fZ',  # ISO con microsegundos
                    '%Y-%m-%dT%H:%M:%SZ',     # ISO sin microsegundos
                    '%Y-%m-%dT%H:%M:%S',      # ISO sin timezone
                    '%Y-%m-%d %H:%M:%S',      # Formato SQL
                ]:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
                
                # Si ningún formato funciona, usar dateutil como fallback
                from dateutil.parser import parse
                return parse(value)
            except:
                return None
        
        return None
    
    @staticmethod
    def safe_date_conversion(value: Any) -> Optional[date]:
        """
        Convierte de forma segura un valor a date
        
        Args:
            value: Valor a convertir (str, date, datetime, etc.)
        
        Returns:
            date object o None si no se puede convertir
        """
        if value is None:
            return None
        
        if isinstance(value, date):
            return value
        
        if isinstance(value, datetime):
            return value.date()
        
        if isinstance(value, str):
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                try:
                    # Intentar con datetime y extraer fecha
                    dt = ModelMapper.safe_datetime_conversion(value)
                    return dt.date() if dt else None
                except:
                    return None
        
        return None


class PatientMapper(ModelMapper):
    """Mapper para Patient/PatientORM"""
    
    @staticmethod
    def pydantic_to_orm(pydantic_model: Union[PydanticPatient, PatientCreate], 
                       documento_id: int, paciente_id: int = None) -> PatientORM:
        """
        Convierte modelo Pydantic Patient a ORM
        
        Args:
            pydantic_model: Modelo Pydantic Patient o PatientCreate
            documento_id: ID del documento (requerido para Citus)
            paciente_id: ID del paciente (opcional, se genera si no se proporciona)
        
        Returns:
            PatientORM instance
        """
        orm_data = {
            "documento_id": documento_id,
            "paciente_id": paciente_id or 1,  # Default, debería generarse en DB
        }
        
        # Mapear campos básicos
        if hasattr(pydantic_model, 'name') and pydantic_model.name:
            names = pydantic_model.name
            if names:
                # Tomar el primer nombre
                first_name = names[0]
                if first_name.given:
                    orm_data["nombre"] = " ".join(first_name.given)
                if first_name.family:
                    orm_data["apellido"] = first_name.family
        
        # Mapear género
        if hasattr(pydantic_model, 'gender') and pydantic_model.gender:
            gender_map = {
                "male": "masculino",
                "female": "femenino",
                "other": "otro",
                "unknown": "desconocido"
            }
            orm_data["sexo"] = gender_map.get(pydantic_model.gender.value, "desconocido")
        
        # Mapear fecha de nacimiento
        if hasattr(pydantic_model, 'birth_date') and pydantic_model.birth_date:
            orm_data["fecha_nacimiento"] = ModelMapper.safe_date_conversion(pydantic_model.birth_date)
        
        # Mapear información de contacto (simplificado como JSON string)
        if hasattr(pydantic_model, 'telecom') and pydantic_model.telecom:
            import json
            telecom_data = [tel.dict() for tel in pydantic_model.telecom]
            orm_data["contacto"] = json.dumps(telecom_data)
        
        # Mapear dirección/ciudad
        if hasattr(pydantic_model, 'address') and pydantic_model.address:
            addresses = pydantic_model.address
            if addresses:
                first_address = addresses[0]
                if first_address.city:
                    orm_data["ciudad"] = first_address.city
        
        return PatientORM(**orm_data)
    
    @staticmethod
    def orm_to_pydantic(orm_model: PatientORM) -> PydanticPatient:
        """
        Convierte modelo ORM Patient a Pydantic
        
        Args:
            orm_model: PatientORM instance
        
        Returns:
            PydanticPatient instance
        """
        from app.models import HumanName, AdministrativeGender, ContactPoint, Address
        
        pydantic_data = {
            "resource_type": "Patient",
            "id": str(orm_model.documento_id),  # Usar documento_id como ID FHIR
        }
        
        # Mapear nombre
        if orm_model.nombre or orm_model.apellido:
            names = []
            name_data = {}
            if orm_model.nombre:
                name_data["given"] = orm_model.nombre.split()
            if orm_model.apellido:
                name_data["family"] = orm_model.apellido
            
            names.append(HumanName(**name_data))
            pydantic_data["name"] = names
        
        # Mapear género
        if orm_model.sexo:
            gender_map = {
                "masculino": AdministrativeGender.MALE,
                "femenino": AdministrativeGender.FEMALE,
                "otro": AdministrativeGender.OTHER,
                "desconocido": AdministrativeGender.UNKNOWN
            }
            pydantic_data["gender"] = gender_map.get(orm_model.sexo, AdministrativeGender.UNKNOWN)
        
        # Mapear fecha de nacimiento
        if orm_model.fecha_nacimiento:
            pydantic_data["birth_date"] = orm_model.fecha_nacimiento
        
        # Mapear contacto
        if orm_model.contacto:
            try:
                import json
                telecom_data = json.loads(orm_model.contacto)
                telecom_objects = [ContactPoint(**tel) for tel in telecom_data]
                pydantic_data["telecom"] = telecom_objects
            except:
                # Si no es JSON válido, crear un contacto simple
                pydantic_data["telecom"] = [ContactPoint(value=orm_model.contacto)]
        
        # Mapear dirección
        if orm_model.ciudad:
            addresses = [Address(city=orm_model.ciudad)]
            pydantic_data["address"] = addresses
        
        # Mapear campos de auditoría y FHIR
        if orm_model.fhir_id:
            pydantic_data["id"] = orm_model.fhir_id
        
        return PydanticPatient(**pydantic_data)


class PractitionerMapper(ModelMapper):
    """Mapper para Practitioner/PractitionerORM"""
    
    @staticmethod
    def pydantic_to_orm(pydantic_model: Union[PydanticPractitioner, PractitionerCreate]) -> PractitionerORM:
        """Convierte modelo Pydantic Practitioner a ORM"""
        orm_data = {}
        
        # Mapear nombre
        if hasattr(pydantic_model, 'name') and pydantic_model.name:
            names = pydantic_model.name
            if names:
                first_name = names[0]
                if first_name.given:
                    orm_data["nombre"] = " ".join(first_name.given)
                if first_name.family:
                    orm_data["apellido"] = first_name.family
        
        # Mapear cualificaciones/especialidad (simplificado)
        if hasattr(pydantic_model, 'qualification') and pydantic_model.qualification:
            qualifications = pydantic_model.qualification
            if qualifications:
                first_qual = qualifications[0]
                if first_qual.code and first_qual.code.text:
                    orm_data["especialidad"] = first_qual.code.text
        
        # Mapear identificadores (buscar registro médico)
        if hasattr(pydantic_model, 'identifier') and pydantic_model.identifier:
            for identifier in pydantic_model.identifier:
                if identifier.type and identifier.type.text and "medical" in identifier.type.text.lower():
                    orm_data["registro_medico"] = identifier.value
                    break
        
        return PractitionerORM(**orm_data)
    
    @staticmethod
    def orm_to_pydantic(orm_model: PractitionerORM) -> PydanticPractitioner:
        """Convierte modelo ORM Practitioner a Pydantic"""
        from app.models import HumanName, PractitionerQualification, CodeableConcept, Identifier
        
        pydantic_data = {
            "resource_type": "Practitioner",
            "id": str(orm_model.profesional_id),
        }
        
        # Mapear nombre
        if orm_model.nombre or orm_model.apellido:
            names = []
            name_data = {}
            if orm_model.nombre:
                name_data["given"] = orm_model.nombre.split()
            if orm_model.apellido:
                name_data["family"] = orm_model.apellido
            
            names.append(HumanName(**name_data))
            pydantic_data["name"] = names
        
        # Mapear cualificaciones
        if orm_model.especialidad:
            qualifications = []
            qual_data = {
                "code": CodeableConcept(text=orm_model.especialidad)
            }
            qualifications.append(PractitionerQualification(**qual_data))
            pydantic_data["qualification"] = qualifications
        
        # Mapear identificadores
        if orm_model.registro_medico:
            identifiers = []
            id_data = {
                "type": CodeableConcept(text="Medical License"),
                "value": orm_model.registro_medico
            }
            identifiers.append(Identifier(**id_data))
            pydantic_data["identifier"] = identifiers
        
        return PydanticPractitioner(**pydantic_data)


class ObservationMapper(ModelMapper):
    """Mapper para Observation/ObservationORM"""
    
    @staticmethod
    def pydantic_to_orm(pydantic_model: Union[PydanticObservation, ObservationCreate],
                       documento_id: int, paciente_id: int, observacion_id: int = None) -> ObservationORM:
        """Convierte modelo Pydantic Observation a ORM"""
        orm_data = {
            "documento_id": documento_id,
            "paciente_id": paciente_id,
            "observacion_id": observacion_id or 1,
        }
        
        # Mapear código/tipo
        if hasattr(pydantic_model, 'code') and pydantic_model.code:
            if pydantic_model.code.text:
                orm_data["tipo"] = pydantic_model.code.text
            elif pydantic_model.code.coding:
                first_coding = pydantic_model.code.coding[0]
                orm_data["tipo"] = first_coding.display or first_coding.code
        
        # Mapear valor
        if hasattr(pydantic_model, 'value_quantity') and pydantic_model.value_quantity:
            orm_data["valor"] = str(pydantic_model.value_quantity.value)
            orm_data["unidad"] = pydantic_model.value_quantity.unit
        elif hasattr(pydantic_model, 'value_string') and pydantic_model.value_string:
            orm_data["valor"] = pydantic_model.value_string
        
        # Mapear fecha efectiva
        if hasattr(pydantic_model, 'effective_date_time') and pydantic_model.effective_date_time:
            orm_data["fecha"] = ModelMapper.safe_datetime_conversion(pydantic_model.effective_date_time)
        
        return ObservationORM(**orm_data)
    
    @staticmethod
    def orm_to_pydantic(orm_model: ObservationORM) -> PydanticObservation:
        """Convierte modelo ORM Observation a Pydantic"""
        from app.models import CodeableConcept, Quantity, Reference, ObservationStatus
        
        pydantic_data = {
            "resource_type": "Observation",
            "id": f"{orm_model.documento_id}-{orm_model.observacion_id}",
            "status": ObservationStatus.FINAL,
        }
        
        # Mapear código
        if orm_model.tipo:
            pydantic_data["code"] = CodeableConcept(text=orm_model.tipo)
        
        # Mapear sujeto
        pydantic_data["subject"] = Reference(
            reference=f"Patient/{orm_model.documento_id}"
        )
        
        # Mapear valor
        if orm_model.valor and orm_model.is_numeric_value():
            quantity_data = {"value": orm_model.get_numeric_value()}
            if orm_model.unidad:
                quantity_data["unit"] = orm_model.unidad
            pydantic_data["value_quantity"] = Quantity(**quantity_data)
        elif orm_model.valor:
            pydantic_data["value_string"] = orm_model.valor
        
        # Mapear fecha
        if orm_model.fecha:
            pydantic_data["effective_date_time"] = orm_model.fecha
        
        return PydanticObservation(**pydantic_data)


class ConditionMapper(ModelMapper):
    """Mapper para Condition/ConditionORM"""
    
    @staticmethod
    def pydantic_to_orm(pydantic_model: Union[PydanticCondition, ConditionCreate],
                       documento_id: int, paciente_id: int, condicion_id: int = None) -> ConditionORM:
        """Convierte modelo Pydantic Condition a ORM"""
        orm_data = {
            "documento_id": documento_id,
            "paciente_id": paciente_id,
            "condicion_id": condicion_id or 1,
        }
        
        # Mapear código
        if hasattr(pydantic_model, 'code') and pydantic_model.code:
            if pydantic_model.code.coding:
                first_coding = pydantic_model.code.coding[0]
                orm_data["codigo"] = first_coding.code
            orm_data["descripcion"] = pydantic_model.code.text or "Condición sin descripción"
        
        # Mapear severidad
        if hasattr(pydantic_model, 'severity') and pydantic_model.severity:
            if pydantic_model.severity.coding:
                severity_code = pydantic_model.severity.coding[0].code
                severity_map = {
                    "mild": "leve",
                    "moderate": "moderada", 
                    "severe": "severa",
                    "critical": "critica"
                }
                orm_data["gravedad"] = severity_map.get(severity_code, severity_code)
        
        # Mapear fechas de inicio
        if hasattr(pydantic_model, 'onset_date_time') and pydantic_model.onset_date_time:
            orm_data["fecha_inicio"] = ModelMapper.safe_date_conversion(pydantic_model.onset_date_time)
        
        # Mapear fechas de resolución
        if hasattr(pydantic_model, 'abatement_date_time') and pydantic_model.abatement_date_time:
            orm_data["fecha_fin"] = ModelMapper.safe_date_conversion(pydantic_model.abatement_date_time)
        
        return ConditionORM(**orm_data)
    
    @staticmethod
    def orm_to_pydantic(orm_model: ConditionORM) -> PydanticCondition:
        """Convierte modelo ORM Condition a Pydantic"""
        from app.models import CodeableConcept, Reference, ConditionClinicalStatus
        
        pydantic_data = {
            "resource_type": "Condition",
            "id": f"{orm_model.documento_id}-{orm_model.condicion_id}",
            "clinical_status": ConditionClinicalStatus.ACTIVE if orm_model.is_active else ConditionClinicalStatus.RESOLVED,
        }
        
        # Mapear código
        code_data = {"text": orm_model.descripcion}
        if orm_model.codigo:
            code_data["coding"] = [{"code": orm_model.codigo, "display": orm_model.descripcion}]
        pydantic_data["code"] = CodeableConcept(**code_data)
        
        # Mapear sujeto
        pydantic_data["subject"] = Reference(
            reference=f"Patient/{orm_model.documento_id}"
        )
        
        # Mapear severidad
        if orm_model.gravedad:
            severity_map = {
                "leve": "mild",
                "moderada": "moderate",
                "severa": "severe", 
                "critica": "critical"
            }
            severity_code = severity_map.get(orm_model.gravedad, orm_model.gravedad)
            pydantic_data["severity"] = CodeableConcept(
                coding=[{"code": severity_code, "display": orm_model.get_severity_display()}]
            )
        
        # Mapear fechas
        if orm_model.fecha_inicio:
            pydantic_data["onset_date_time"] = orm_model.fecha_inicio
        
        if orm_model.fecha_fin:
            pydantic_data["abatement_date_time"] = orm_model.fecha_fin
        
        return PydanticCondition(**pydantic_data)


# Factory para obtener el mapper apropiado
class MapperFactory:
    """Factory para obtener mappers específicos por tipo de recurso"""
    
    _mappers = {
        "Patient": PatientMapper,
        "Practitioner": PractitionerMapper,
        "Observation": ObservationMapper,
        "Condition": ConditionMapper,
        # TODO: Agregar MedicationRequestMapper y DiagnosticReportMapper
    }
    
    @classmethod
    def get_mapper(cls, resource_type: str):
        """
        Obtiene el mapper para un tipo de recurso específico
        
        Args:
            resource_type: Tipo de recurso FHIR
        
        Returns:
            Clase mapper correspondiente o None si no existe
        """
        return cls._mappers.get(resource_type)
    
    @classmethod
    def register_mapper(cls, resource_type: str, mapper_class):
        """
        Registra un nuevo mapper para un tipo de recurso
        
        Args:
            resource_type: Tipo de recurso FHIR
            mapper_class: Clase mapper a registrar
        """
        cls._mappers[resource_type] = mapper_class
    
    @classmethod
    def get_available_mappers(cls) -> List[str]:
        """
        Obtiene lista de tipos de recursos con mappers disponibles
        
        Returns:
            Lista de tipos de recursos
        """
        return list(cls._mappers.keys())


# Exportaciones del módulo
__all__ = [
    "ModelMapper",
    "PatientMapper",
    "PractitionerMapper", 
    "ObservationMapper",
    "ConditionMapper",
    "MapperFactory"
]