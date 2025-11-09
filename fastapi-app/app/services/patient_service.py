"""
Patient Service - Servicio de negocio para gestión de pacientes FHIR
Implementa operaciones CRUD específicas para recursos Patient
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, date

from app.models import (
    Patient as PydanticPatient,
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientSearchParams
)
from app.models.orm import PatientORM
from app.models.orm.mappers import PatientMapper
from .base import DistributedService, ResourceNotFoundException, ValidationException


class PatientService(DistributedService):
    """
    Servicio de negocio para gestión de pacientes
    
    Implementa operaciones CRUD y lógica de negocio específica para pacientes FHIR
    """
    
    def __init__(self):
        super().__init__(
            pydantic_model=PydanticPatient,
            orm_model=PatientORM,
            create_model=PatientCreate,
            update_model=PatientUpdate,
            resource_name="Patient"
        )
    
    async def create(self, session: AsyncSession, patient_data: PatientCreate, 
                    documento_id: int) -> PatientResponse:
        """
        Crear un nuevo paciente
        
        Args:
            session: Sesión de base de datos
            patient_data: Datos del paciente a crear
            documento_id: ID del documento del paciente
            
        Returns:
            PatientResponse con el paciente creado
        """
        try:
            # Validar que no exista otro paciente con el mismo documento_id
            existing = await self._get_by_documento_id_orm(session, documento_id)
            if existing:
                raise ValidationException(
                    f"Patient with documento_id {documento_id} already exists"
                )
            
            # Obtener siguiente ID de paciente
            paciente_id = await self._get_next_patient_id(session, documento_id)
            
            # Convertir a modelo ORM usando mapper
            orm_patient = PatientMapper.pydantic_to_orm(
                patient_data, 
                documento_id=documento_id,
                paciente_id=paciente_id
            )
            
            # Guardar en base de datos
            session.add(orm_patient)
            await session.commit()
            await session.refresh(orm_patient)
            
            self.logger.info(f"Created patient with documento_id: {documento_id}")
            
            # Convertir a respuesta Pydantic
            pydantic_patient = PatientMapper.orm_to_pydantic(orm_patient)
            return PatientResponse(**pydantic_patient.dict())
            
        except ValidationException:
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "create_patient")
    
    async def get_by_id(self, session: AsyncSession, resource_id: str, 
                       documento_id: int = None) -> Optional[PatientResponse]:
        """
        Obtener paciente por ID
        
        Args:
            session: Sesión de base de datos
            resource_id: ID del recurso (documento_id en este caso)
            documento_id: Documento ID (mismo que resource_id para pacientes)
            
        Returns:
            PatientResponse o None si no se encuentra
        """
        try:
            # Para pacientes, el resource_id es el documento_id
            doc_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            orm_patient = await self._get_by_documento_id_orm(session, doc_id)
            if not orm_patient:
                return None
            
            pydantic_patient = PatientMapper.orm_to_pydantic(orm_patient)
            return PatientResponse(**pydantic_patient.dict())
            
        except Exception as e:
            self._handle_database_error(e, "get_patient_by_id")
    
    async def update(self, session: AsyncSession, resource_id: str, 
                    patient_data: PatientUpdate, documento_id: int = None) -> PatientResponse:
        """
        Actualizar paciente existente
        
        Args:
            session: Sesión de base de datos
            resource_id: ID del recurso (documento_id)
            patient_data: Datos de actualización
            documento_id: Documento ID
            
        Returns:
            PatientResponse con el paciente actualizado
        """
        try:
            doc_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            # Buscar paciente existente
            orm_patient = await self._get_by_documento_id_orm(session, doc_id)
            if not orm_patient:
                raise ResourceNotFoundException("Patient", resource_id)
            
            # Actualizar campos modificados
            update_data = patient_data.dict(exclude_unset=True)
            
            # Mapear actualizaciones específicas
            if 'name' in update_data and update_data['name']:
                first_name = update_data['name'][0]
                if 'given' in first_name:
                    orm_patient.nombre = " ".join(first_name['given'])
                if 'family' in first_name:
                    orm_patient.apellido = first_name['family']
            
            if 'gender' in update_data:
                gender_map = {
                    "male": "masculino",
                    "female": "femenino", 
                    "other": "otro",
                    "unknown": "desconocido"
                }
                orm_patient.sexo = gender_map.get(update_data['gender'], "desconocido")
            
            if 'birth_date' in update_data:
                orm_patient.fecha_nacimiento = update_data['birth_date']
            
            # Actualizar timestamp de modificación
            orm_patient.updated_at = datetime.utcnow()
            orm_patient.fhir_last_updated = datetime.utcnow()
            
            await session.commit()
            await session.refresh(orm_patient)
            
            self.logger.info(f"Updated patient with documento_id: {doc_id}")
            
            pydantic_patient = PatientMapper.orm_to_pydantic(orm_patient)
            return PatientResponse(**pydantic_patient.dict())
            
        except ResourceNotFoundException:
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "update_patient")
    
    async def delete(self, session: AsyncSession, resource_id: str, 
                    documento_id: int = None) -> bool:
        """
        Eliminar paciente
        
        Args:
            session: Sesión de base de datos
            resource_id: ID del recurso (documento_id)
            documento_id: Documento ID
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            doc_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            # Buscar paciente existente
            orm_patient = await self._get_by_documento_id_orm(session, doc_id)
            if not orm_patient:
                raise ResourceNotFoundException("Patient", resource_id)
            
            # Eliminar paciente
            await session.delete(orm_patient)
            await session.commit()
            
            self.logger.info(f"Deleted patient with documento_id: {doc_id}")
            return True
            
        except ResourceNotFoundException:
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "delete_patient")
    
    async def search(self, session: AsyncSession, search_params: PatientSearchParams) -> Dict[str, Any]:
        """
        Buscar pacientes con filtros y paginación
        
        Args:
            session: Sesión de base de datos
            search_params: Parámetros de búsqueda
            
        Returns:
            Resultado paginado con pacientes encontrados
        """
        try:
            # Construir query base
            query = select(PatientORM)
            count_query = select(func.count()).select_from(PatientORM)
            
            # Aplicar filtros
            filters = []
            
            if search_params.gender:
                gender_map = {
                    "male": "masculino",
                    "female": "femenino",
                    "other": "otro", 
                    "unknown": "desconocido"
                }
                mapped_gender = gender_map.get(search_params.gender)
                if mapped_gender:
                    filters.append(PatientORM.sexo == mapped_gender)
            
            if search_params.birthdate:
                filters.append(PatientORM.fecha_nacimiento == search_params.birthdate)
            
            if search_params.name:
                name_filter = or_(
                    PatientORM.nombre.ilike(f"%{search_params.name}%"),
                    PatientORM.apellido.ilike(f"%{search_params.name}%")
                )
                filters.append(name_filter)
            
            if search_params.family:
                filters.append(PatientORM.apellido.ilike(f"%{search_params.family}%"))
            
            if search_params.given:
                filters.append(PatientORM.nombre.ilike(f"%{search_params.given}%"))
            
            if search_params.city:
                filters.append(PatientORM.ciudad.ilike(f"%{search_params.city}%"))
            
            # Aplicar filtros a las queries
            if filters:
                query = query.where(and_(*filters))
                count_query = count_query.where(and_(*filters))
            
            # Obtener total de resultados
            total_result = await session.execute(count_query)
            total = total_result.scalar()
            
            # Aplicar paginación y ordenamiento
            offset = (search_params.page - 1) * search_params.size
            
            if search_params.sort:
                if search_params.sort == "name":
                    order_field = PatientORM.nombre
                elif search_params.sort == "birthdate":
                    order_field = PatientORM.fecha_nacimiento
                else:
                    order_field = PatientORM.created_at
                
                if search_params.order == "asc":
                    query = query.order_by(order_field.asc())
                else:
                    query = query.order_by(order_field.desc())
            else:
                query = query.order_by(PatientORM.created_at.desc())
            
            query = query.limit(search_params.size).offset(offset)
            
            # Ejecutar query
            result = await session.execute(query)
            orm_patients = result.scalars().all()
            
            # Convertir a modelos Pydantic
            pydantic_patients = []
            for orm_patient in orm_patients:
                pydantic_patient = PatientMapper.orm_to_pydantic(orm_patient)
                pydantic_patients.append(PatientResponse(**pydantic_patient.dict()))
            
            return self._create_search_response(
                pydantic_patients, total, search_params.page, search_params.size
            )
            
        except Exception as e:
            self._handle_database_error(e, "search_patients")
    
    async def get_by_name(self, session: AsyncSession, nombre: str = None, 
                         apellido: str = None) -> List[PatientResponse]:
        """
        Buscar pacientes por nombre y apellido
        
        Args:
            session: Sesión de base de datos
            nombre: Nombre a buscar (opcional)
            apellido: Apellido a buscar (opcional)
            
        Returns:
            Lista de pacientes encontrados
        """
        try:
            query = PatientORM.search_by_name(session, nombre, apellido)
            result = await session.execute(query.statement)
            orm_patients = result.scalars().all()
            
            patients = []
            for orm_patient in orm_patients:
                pydantic_patient = PatientMapper.orm_to_pydantic(orm_patient)
                patients.append(PatientResponse(**pydantic_patient.dict()))
            
            return patients
            
        except Exception as e:
            self._handle_database_error(e, "get_patients_by_name")
    
    async def get_by_age_range(self, session: AsyncSession, min_age: int = None, 
                              max_age: int = None) -> List[PatientResponse]:
        """
        Obtener pacientes por rango de edad
        
        Args:
            session: Sesión de base de datos
            min_age: Edad mínima (opcional)
            max_age: Edad máxima (opcional)
            
        Returns:
            Lista de pacientes en el rango de edad
        """
        try:
            query = PatientORM.get_by_age_range(session, min_age, max_age)
            result = await session.execute(query.statement)
            orm_patients = result.scalars().all()
            
            patients = []
            for orm_patient in orm_patients:
                pydantic_patient = PatientMapper.orm_to_pydantic(orm_patient)
                patients.append(PatientResponse(**pydantic_patient.dict()))
            
            return patients
            
        except Exception as e:
            self._handle_database_error(e, "get_patients_by_age_range")
    
    # Métodos auxiliares privados
    
    async def _get_by_documento_id_orm(self, session: AsyncSession, documento_id: int) -> Optional[PatientORM]:
        """Obtiene paciente ORM por documento_id"""
        result = await session.execute(
            select(PatientORM).where(PatientORM.documento_id == documento_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_next_patient_id(self, session: AsyncSession, documento_id: int) -> int:
        """Obtiene el siguiente ID de paciente para un documento"""
        # Para pacientes, generalmente hay un paciente por documento, así que usar 1
        return 1


# Instancia global del servicio (singleton)
patient_service = PatientService()

# Exportaciones del módulo
__all__ = [
    "PatientService",
    "patient_service"
]