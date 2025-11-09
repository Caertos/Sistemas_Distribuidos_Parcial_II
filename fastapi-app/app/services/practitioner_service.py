"""
Practitioner Service - Servicio de negocio para gestión de profesionales FHIR
Implementa operaciones CRUD específicas para recursos Practitioner
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime

from app.models import (
    Practitioner as PydanticPractitioner,
    PractitionerCreate,
    PractitionerUpdate,
    PractitionerResponse,
    PractitionerSearchParams
)
from app.models.orm import PractitionerORM
from app.models.orm.mappers import PractitionerMapper
from .base import ReferenceService, ResourceNotFoundException, ValidationException


class PractitionerService(ReferenceService):
    """
    Servicio de negocio para gestión de profesionales de salud
    
    Implementa operaciones CRUD y lógica de negocio específica para profesionales FHIR
    """
    
    def __init__(self):
        super().__init__(
            pydantic_model=PydanticPractitioner,
            orm_model=PractitionerORM,
            create_model=PractitionerCreate,
            update_model=PractitionerUpdate,
            resource_name="Practitioner"
        )
    
    async def create(self, session: AsyncSession, practitioner_data: PractitionerCreate, 
                    **kwargs) -> PractitionerResponse:
        """
        Crear un nuevo profesional de salud
        
        Args:
            session: Sesión de base de datos
            practitioner_data: Datos del profesional a crear
            
        Returns:
            PractitionerResponse con el profesional creado
        """
        try:
            # Validar registro médico único si está presente
            if hasattr(practitioner_data, 'identifier') and practitioner_data.identifier:
                for identifier in practitioner_data.identifier:
                    if identifier.value:
                        existing = await self._get_by_registro_medico_orm(session, identifier.value)
                        if existing:
                            raise ValidationException(
                                f"Practitioner with medical license {identifier.value} already exists"
                            )
            
            # Convertir a modelo ORM usando mapper
            orm_practitioner = PractitionerMapper.pydantic_to_orm(practitioner_data)
            
            # Guardar en base de datos
            session.add(orm_practitioner)
            await session.commit()
            await session.refresh(orm_practitioner)
            
            self.logger.info(f"Created practitioner with ID: {orm_practitioner.profesional_id}")
            
            # Convertir a respuesta Pydantic
            pydantic_practitioner = PractitionerMapper.orm_to_pydantic(orm_practitioner)
            return PractitionerResponse(**pydantic_practitioner.dict())
            
        except ValidationException:
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "create_practitioner")
    
    async def get_by_id(self, session: AsyncSession, resource_id: str, 
                       documento_id: int = None) -> Optional[PractitionerResponse]:
        """
        Obtener profesional por ID
        
        Args:
            session: Sesión de base de datos
            resource_id: ID del profesional
            documento_id: No utilizado para profesionales (tablas de referencia)
            
        Returns:
            PractitionerResponse o None si no se encuentra
        """
        try:
            profesional_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            result = await session.execute(
                select(PractitionerORM).where(PractitionerORM.profesional_id == profesional_id)
            )
            orm_practitioner = result.scalar_one_or_none()
            
            if not orm_practitioner:
                return None
            
            pydantic_practitioner = PractitionerMapper.orm_to_pydantic(orm_practitioner)
            return PractitionerResponse(**pydantic_practitioner.dict())
            
        except Exception as e:
            self._handle_database_error(e, "get_practitioner_by_id")
    
    async def update(self, session: AsyncSession, resource_id: str, 
                    practitioner_data: PractitionerUpdate, documento_id: int = None) -> PractitionerResponse:
        """
        Actualizar profesional existente
        
        Args:
            session: Sesión de base de datos
            resource_id: ID del profesional
            practitioner_data: Datos de actualización
            documento_id: No utilizado para profesionales
            
        Returns:
            PractitionerResponse con el profesional actualizado
        """
        try:
            profesional_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            # Buscar profesional existente
            result = await session.execute(
                select(PractitionerORM).where(PractitionerORM.profesional_id == profesional_id)
            )
            orm_practitioner = result.scalar_one_or_none()
            
            if not orm_practitioner:
                raise ResourceNotFoundException("Practitioner", resource_id)
            
            # Actualizar campos modificados
            update_data = practitioner_data.dict(exclude_unset=True)
            
            # Mapear actualizaciones específicas
            if 'name' in update_data and update_data['name']:
                first_name = update_data['name'][0]
                if 'given' in first_name:
                    orm_practitioner.nombre = " ".join(first_name['given'])
                if 'family' in first_name:
                    orm_practitioner.apellido = first_name['family']
            
            if 'qualification' in update_data and update_data['qualification']:
                first_qual = update_data['qualification'][0]
                if 'code' in first_qual and first_qual['code'] and first_qual['code'].get('text'):
                    orm_practitioner.especialidad = first_qual['code']['text']
            
            if 'identifier' in update_data and update_data['identifier']:
                for identifier in update_data['identifier']:
                    if identifier.get('value'):
                        # Validar que el nuevo registro médico no exista
                        existing = await self._get_by_registro_medico_orm(session, identifier['value'])
                        if existing and existing.profesional_id != profesional_id:
                            raise ValidationException(
                                f"Medical license {identifier['value']} already exists for another practitioner"
                            )
                        orm_practitioner.registro_medico = identifier['value']
                        break
            
            # Actualizar timestamp de modificación
            orm_practitioner.updated_at = datetime.utcnow()
            orm_practitioner.fhir_last_updated = datetime.utcnow()
            
            await session.commit()
            await session.refresh(orm_practitioner)
            
            self.logger.info(f"Updated practitioner with ID: {profesional_id}")
            
            pydantic_practitioner = PractitionerMapper.orm_to_pydantic(orm_practitioner)
            return PractitionerResponse(**pydantic_practitioner.dict())
            
        except (ResourceNotFoundException, ValidationException):
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "update_practitioner")
    
    async def delete(self, session: AsyncSession, resource_id: str, 
                    documento_id: int = None) -> bool:
        """
        Eliminar profesional
        
        Args:
            session: Sesión de base de datos
            resource_id: ID del profesional
            documento_id: No utilizado para profesionales
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            profesional_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            # Buscar profesional existente
            result = await session.execute(
                select(PractitionerORM).where(PractitionerORM.profesional_id == profesional_id)
            )
            orm_practitioner = result.scalar_one_or_none()
            
            if not orm_practitioner:
                raise ResourceNotFoundException("Practitioner", resource_id)
            
            # Verificar que no tenga referencias activas (opcional, depende de reglas de negocio)
            # TODO: Implementar validación de referencias si es necesario
            
            # Eliminar profesional
            await session.delete(orm_practitioner)
            await session.commit()
            
            self.logger.info(f"Deleted practitioner with ID: {profesional_id}")
            return True
            
        except ResourceNotFoundException:
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "delete_practitioner")
    
    async def search(self, session: AsyncSession, search_params: PractitionerSearchParams) -> Dict[str, Any]:
        """
        Buscar profesionales con filtros y paginación
        
        Args:
            session: Sesión de base de datos
            search_params: Parámetros de búsqueda
            
        Returns:
            Resultado paginado con profesionales encontrados
        """
        try:
            # Construir query base
            query = select(PractitionerORM)
            count_query = select(func.count()).select_from(PractitionerORM)
            
            # Aplicar filtros
            filters = []
            
            if search_params.name:
                name_filter = or_(
                    PractitionerORM.nombre.ilike(f"%{search_params.name}%"),
                    PractitionerORM.apellido.ilike(f"%{search_params.name}%")
                )
                filters.append(name_filter)
            
            if search_params.family:
                filters.append(PractitionerORM.apellido.ilike(f"%{search_params.family}%"))
            
            if search_params.given:
                filters.append(PractitionerORM.nombre.ilike(f"%{search_params.given}%"))
            
            if search_params.specialty:
                filters.append(PractitionerORM.especialidad.ilike(f"%{search_params.specialty}%"))
            
            if search_params.identifier:
                filters.append(PractitionerORM.registro_medico == search_params.identifier)
            
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
                    order_field = PractitionerORM.nombre
                elif search_params.sort == "specialty":
                    order_field = PractitionerORM.especialidad
                else:
                    order_field = PractitionerORM.created_at
                
                if search_params.order == "asc":
                    query = query.order_by(order_field.asc())
                else:
                    query = query.order_by(order_field.desc())
            else:
                query = query.order_by(PractitionerORM.created_at.desc())
            
            query = query.limit(search_params.size).offset(offset)
            
            # Ejecutar query
            result = await session.execute(query)
            orm_practitioners = result.scalars().all()
            
            # Convertir a modelos Pydantic
            pydantic_practitioners = []
            for orm_practitioner in orm_practitioners:
                pydantic_practitioner = PractitionerMapper.orm_to_pydantic(orm_practitioner)
                pydantic_practitioners.append(PractitionerResponse(**pydantic_practitioner.dict()))
            
            return self._create_search_response(
                pydantic_practitioners, total, search_params.page, search_params.size
            )
            
        except Exception as e:
            self._handle_database_error(e, "search_practitioners")
    
    async def get_by_specialty(self, session: AsyncSession, specialty: str) -> List[PractitionerResponse]:
        """
        Obtener profesionales por especialidad
        
        Args:
            session: Sesión de base de datos
            specialty: Especialidad a buscar
            
        Returns:
            Lista de profesionales con la especialidad especificada
        """
        try:
            query = PractitionerORM.get_by_especialidad(session, specialty)
            result = await session.execute(query.statement)
            orm_practitioners = result.scalars().all()
            
            practitioners = []
            for orm_practitioner in orm_practitioners:
                pydantic_practitioner = PractitionerMapper.orm_to_pydantic(orm_practitioner)
                practitioners.append(PractitionerResponse(**pydantic_practitioner.dict()))
            
            return practitioners
            
        except Exception as e:
            self._handle_database_error(e, "get_practitioners_by_specialty")
    
    async def get_by_registro_medico(self, session: AsyncSession, 
                                   registro_medico: str) -> Optional[PractitionerResponse]:
        """
        Obtener profesional por registro médico
        
        Args:
            session: Sesión de base de datos
            registro_medico: Número de registro médico
            
        Returns:
            PractitionerResponse o None si no se encuentra
        """
        try:
            orm_practitioner = await self._get_by_registro_medico_orm(session, registro_medico)
            if not orm_practitioner:
                return None
            
            pydantic_practitioner = PractitionerMapper.orm_to_pydantic(orm_practitioner)
            return PractitionerResponse(**pydantic_practitioner.dict())
            
        except Exception as e:
            self._handle_database_error(e, "get_practitioner_by_registro_medico")
    
    async def get_all_specialties(self, session: AsyncSession) -> List[str]:
        """
        Obtener todas las especialidades disponibles
        
        Args:
            session: Sesión de base de datos
            
        Returns:
            Lista de especialidades únicas
        """
        try:
            specialties = await PractitionerORM.get_all_especialidades(session)
            return specialties
            
        except Exception as e:
            self._handle_database_error(e, "get_all_specialties")
    
    # Métodos auxiliares privados
    
    async def _get_by_registro_medico_orm(self, session: AsyncSession, 
                                        registro_medico: str) -> Optional[PractitionerORM]:
        """Obtiene profesional ORM por registro médico"""
        result = await session.execute(
            select(PractitionerORM).where(PractitionerORM.registro_medico == registro_medico)
        )
        return result.scalar_one_or_none()


# Instancia global del servicio (singleton)
practitioner_service = PractitionerService()

# Exportaciones del módulo
__all__ = [
    "PractitionerService",
    "practitioner_service"
]