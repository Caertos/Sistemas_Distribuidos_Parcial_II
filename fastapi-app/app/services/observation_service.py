"""
Observation Service - Servicio de negocio para gestión de observaciones FHIR
Implementa operaciones CRUD específicas para recursos Observation
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime, date

from app.models import (
    Observation as PydanticObservation,
    ObservationCreate,
    ObservationUpdate,
    ObservationResponse,
    ObservationSearchParams
)
from app.models.orm import ObservationORM
from app.models.orm.mappers import ObservationMapper
from .base import DistributedService, ResourceNotFoundException, ValidationException


class ObservationService(DistributedService):
    """
    Servicio de negocio para gestión de observaciones médicas
    
    Implementa operaciones CRUD y lógica de negocio específica para observaciones FHIR
    """
    
    def __init__(self):
        super().__init__(
            pydantic_model=PydanticObservation,
            orm_model=ObservationORM,
            create_model=ObservationCreate,
            update_model=ObservationUpdate,
            resource_name="Observation"
        )
    
    async def create(self, session: AsyncSession, observation_data: ObservationCreate, 
                    documento_id: int, **kwargs) -> ObservationResponse:
        """
        Crear una nueva observación médica
        
        Args:
            session: Sesión de base de datos
            observation_data: Datos de la observación a crear
            documento_id: ID del documento asociado (co-location key)
            
        Returns:
            ObservationResponse con la observación creada
        """
        try:
            # Validar que exista el paciente (opcional, dependiendo de reglas de negocio)
            # TODO: Implementar validación de existencia de paciente si es necesario
            
            # Convertir a modelo ORM usando mapper
            orm_observation = ObservationMapper.pydantic_to_orm(observation_data)
            orm_observation.documento_id = documento_id
            
            # Guardar en base de datos (Citus co-localizará por documento_id)
            session.add(orm_observation)
            await session.commit()
            await session.refresh(orm_observation)
            
            self.logger.info(f"Created observation with ID: {orm_observation.observacion_id} for document: {documento_id}")
            
            # Convertir a respuesta Pydantic
            pydantic_observation = ObservationMapper.orm_to_pydantic(orm_observation)
            return ObservationResponse(**pydantic_observation.dict())
            
        except ValidationException:
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "create_observation")
    
    async def get_by_id(self, session: AsyncSession, resource_id: str, 
                       documento_id: int) -> Optional[ObservationResponse]:
        """
        Obtener observación por ID
        
        Args:
            session: Sesión de base de datos
            resource_id: ID de la observación
            documento_id: ID del documento (co-location key)
            
        Returns:
            ObservationResponse o None si no se encuentra
        """
        try:
            observacion_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            result = await session.execute(
                select(ObservationORM).where(
                    and_(
                        ObservationORM.observacion_id == observacion_id,
                        ObservationORM.documento_id == documento_id
                    )
                )
            )
            orm_observation = result.scalar_one_or_none()
            
            if not orm_observation:
                return None
            
            pydantic_observation = ObservationMapper.orm_to_pydantic(orm_observation)
            return ObservationResponse(**pydantic_observation.dict())
            
        except Exception as e:
            self._handle_database_error(e, "get_observation_by_id")
    
    async def update(self, session: AsyncSession, resource_id: str, 
                    observation_data: ObservationUpdate, documento_id: int) -> ObservationResponse:
        """
        Actualizar observación existente
        
        Args:
            session: Sesión de base de datos
            resource_id: ID de la observación
            observation_data: Datos de actualización
            documento_id: ID del documento (co-location key)
            
        Returns:
            ObservationResponse con la observación actualizada
        """
        try:
            observacion_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            # Buscar observación existente
            result = await session.execute(
                select(ObservationORM).where(
                    and_(
                        ObservationORM.observacion_id == observacion_id,
                        ObservationORM.documento_id == documento_id
                    )
                )
            )
            orm_observation = result.scalar_one_or_none()
            
            if not orm_observation:
                raise ResourceNotFoundException("Observation", resource_id)
            
            # Actualizar campos modificados
            update_data = observation_data.dict(exclude_unset=True)
            
            # Mapear actualizaciones específicas
            if 'status' in update_data:
                orm_observation.estado = update_data['status']
            
            if 'code' in update_data and update_data['code']:
                code = update_data['code']
                if 'coding' in code and code['coding']:
                    first_coding = code['coding'][0]
                    if 'code' in first_coding:
                        orm_observation.codigo_loinc = first_coding['code']
                    if 'display' in first_coding:
                        orm_observation.descripcion = first_coding['display']
                elif 'text' in code:
                    orm_observation.descripcion = code['text']
            
            if 'valueQuantity' in update_data and update_data['valueQuantity']:
                value_qty = update_data['valueQuantity']
                if 'value' in value_qty:
                    orm_observation.valor_numerico = float(value_qty['value'])
                if 'unit' in value_qty:
                    orm_observation.unidad = value_qty['unit']
            
            if 'valueString' in update_data:
                orm_observation.valor_texto = update_data['valueString']
            
            if 'valueBoolean' in update_data:
                orm_observation.valor_booleano = update_data['valueBoolean']
            
            if 'effectiveDateTime' in update_data:
                if isinstance(update_data['effectiveDateTime'], str):
                    orm_observation.fecha_efectiva = datetime.fromisoformat(
                        update_data['effectiveDateTime'].replace('Z', '+00:00')
                    )
                else:
                    orm_observation.fecha_efectiva = update_data['effectiveDateTime']
            
            if 'category' in update_data and update_data['category']:
                first_category = update_data['category'][0]
                if 'coding' in first_category and first_category['coding']:
                    first_coding = first_category['coding'][0]
                    if 'code' in first_coding:
                        orm_observation.categoria = first_coding['code']
            
            # Actualizar timestamp de modificación
            orm_observation.updated_at = datetime.utcnow()
            orm_observation.fhir_last_updated = datetime.utcnow()
            
            await session.commit()
            await session.refresh(orm_observation)
            
            self.logger.info(f"Updated observation with ID: {observacion_id}")
            
            pydantic_observation = ObservationMapper.orm_to_pydantic(orm_observation)
            return ObservationResponse(**pydantic_observation.dict())
            
        except (ResourceNotFoundException, ValidationException):
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "update_observation")
    
    async def delete(self, session: AsyncSession, resource_id: str, 
                    documento_id: int) -> bool:
        """
        Eliminar observación
        
        Args:
            session: Sesión de base de datos
            resource_id: ID de la observación
            documento_id: ID del documento (co-location key)
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            observacion_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            # Buscar observación existente
            result = await session.execute(
                select(ObservationORM).where(
                    and_(
                        ObservationORM.observacion_id == observacion_id,
                        ObservationORM.documento_id == documento_id
                    )
                )
            )
            orm_observation = result.scalar_one_or_none()
            
            if not orm_observation:
                raise ResourceNotFoundException("Observation", resource_id)
            
            # Eliminar observación
            await session.delete(orm_observation)
            await session.commit()
            
            self.logger.info(f"Deleted observation with ID: {observacion_id}")
            return True
            
        except ResourceNotFoundException:
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "delete_observation")
    
    async def search(self, session: AsyncSession, search_params: ObservationSearchParams, 
                    documento_id: int = None) -> Dict[str, Any]:
        """
        Buscar observaciones con filtros y paginación
        
        Args:
            session: Sesión de base de datos
            search_params: Parámetros de búsqueda
            documento_id: ID del documento (opcional para búsqueda global)
            
        Returns:
            Resultado paginado con observaciones encontradas
        """
        try:
            # Construir query base
            query = select(ObservationORM)
            count_query = select(func.count()).select_from(ObservationORM)
            
            # Aplicar filtros
            filters = []
            
            # Filtro por documento si se especifica
            if documento_id:
                filters.append(ObservationORM.documento_id == documento_id)
            
            if search_params.patient:
                # Asumir que search_params.patient contiene el ID del paciente
                filters.append(ObservationORM.paciente_id == int(search_params.patient))
            
            if search_params.code:
                filters.append(ObservationORM.codigo_loinc == search_params.code)
            
            if search_params.category:
                filters.append(ObservationORM.categoria == search_params.category)
            
            if search_params.status:
                filters.append(ObservationORM.estado == search_params.status)
            
            if search_params.date:
                # Parsear fecha para búsqueda
                if isinstance(search_params.date, str):
                    search_date = datetime.fromisoformat(search_params.date.replace('Z', '+00:00')).date()
                else:
                    search_date = search_params.date
                
                filters.append(func.date(ObservationORM.fecha_efectiva) == search_date)
            
            if search_params.value_quantity:
                try:
                    value = float(search_params.value_quantity)
                    filters.append(ObservationORM.valor_numerico == value)
                except ValueError:
                    pass  # Ignorar si no es un número válido
            
            if search_params.value_string:
                filters.append(ObservationORM.valor_texto.ilike(f"%{search_params.value_string}%"))
            
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
                if search_params.sort == "date":
                    order_field = ObservationORM.fecha_efectiva
                elif search_params.sort == "code":
                    order_field = ObservationORM.codigo_loinc
                elif search_params.sort == "status":
                    order_field = ObservationORM.estado
                else:
                    order_field = ObservationORM.created_at
                
                if search_params.order == "asc":
                    query = query.order_by(order_field.asc())
                else:
                    query = query.order_by(order_field.desc())
            else:
                query = query.order_by(ObservationORM.fecha_efectiva.desc())
            
            query = query.limit(search_params.size).offset(offset)
            
            # Ejecutar query
            result = await session.execute(query)
            orm_observations = result.scalars().all()
            
            # Convertir a modelos Pydantic
            pydantic_observations = []
            for orm_observation in orm_observations:
                pydantic_observation = ObservationMapper.orm_to_pydantic(orm_observation)
                pydantic_observations.append(ObservationResponse(**pydantic_observation.dict()))
            
            return self._create_search_response(
                pydantic_observations, total, search_params.page, search_params.size
            )
            
        except Exception as e:
            self._handle_database_error(e, "search_observations")
    
    async def get_by_patient(self, session: AsyncSession, paciente_id: int, 
                           documento_id: int = None) -> List[ObservationResponse]:
        """
        Obtener todas las observaciones de un paciente
        
        Args:
            session: Sesión de base de datos
            paciente_id: ID del paciente
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de observaciones del paciente
        """
        try:
            filters = [ObservationORM.paciente_id == paciente_id]
            if documento_id:
                filters.append(ObservationORM.documento_id == documento_id)
            
            result = await session.execute(
                select(ObservationORM)
                .where(and_(*filters))
                .order_by(ObservationORM.fecha_efectiva.desc())
            )
            orm_observations = result.scalars().all()
            
            observations = []
            for orm_observation in orm_observations:
                pydantic_observation = ObservationMapper.orm_to_pydantic(orm_observation)
                observations.append(ObservationResponse(**pydantic_observation.dict()))
            
            return observations
            
        except Exception as e:
            self._handle_database_error(e, "get_observations_by_patient")
    
    async def get_by_category(self, session: AsyncSession, categoria: str, 
                            documento_id: int = None) -> List[ObservationResponse]:
        """
        Obtener observaciones por categoría
        
        Args:
            session: Sesión de base de datos
            categoria: Categoría a buscar
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de observaciones de la categoría especificada
        """
        try:
            filters = [ObservationORM.categoria == categoria]
            if documento_id:
                filters.append(ObservationORM.documento_id == documento_id)
            
            result = await session.execute(
                select(ObservationORM)
                .where(and_(*filters))
                .order_by(ObservationORM.fecha_efectiva.desc())
            )
            orm_observations = result.scalars().all()
            
            observations = []
            for orm_observation in orm_observations:
                pydantic_observation = ObservationMapper.orm_to_pydantic(orm_observation)
                observations.append(ObservationResponse(**pydantic_observation.dict()))
            
            return observations
            
        except Exception as e:
            self._handle_database_error(e, "get_observations_by_category")
    
    async def get_vital_signs(self, session: AsyncSession, paciente_id: int, 
                            documento_id: int = None) -> List[ObservationResponse]:
        """
        Obtener signos vitales de un paciente
        
        Args:
            session: Sesión de base de datos
            paciente_id: ID del paciente
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de observaciones de signos vitales
        """
        return await self.get_by_category(session, "vital-signs", documento_id)
    
    async def get_laboratory_results(self, session: AsyncSession, paciente_id: int, 
                                   documento_id: int = None) -> List[ObservationResponse]:
        """
        Obtener resultados de laboratorio de un paciente
        
        Args:
            session: Sesión de base de datos
            paciente_id: ID del paciente
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de observaciones de laboratorio
        """
        return await self.get_by_category(session, "laboratory", documento_id)


# Instancia global del servicio (singleton)
observation_service = ObservationService()

# Exportaciones del módulo
__all__ = [
    "ObservationService",
    "observation_service"
]