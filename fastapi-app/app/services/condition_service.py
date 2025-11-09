"""
Condition Service - Servicio de negocio para gestión de condiciones FHIR
Implementa operaciones CRUD específicas para recursos Condition
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime, date

from app.models import (
    Condition as PydanticCondition,
    ConditionCreate,
    ConditionUpdate,
    ConditionResponse,
    ConditionSearchParams
)
from app.models.orm import ConditionORM
from app.models.orm.mappers import ConditionMapper
from .base import DistributedService, ResourceNotFoundException, ValidationException


class ConditionService(DistributedService):
    """
    Servicio de negocio para gestión de condiciones médicas
    
    Implementa operaciones CRUD y lógica de negocio específica para condiciones FHIR
    """
    
    def __init__(self):
        super().__init__(
            pydantic_model=PydanticCondition,
            orm_model=ConditionORM,
            create_model=ConditionCreate,
            update_model=ConditionUpdate,
            resource_name="Condition"
        )
    
    async def create(self, session: AsyncSession, condition_data: ConditionCreate, 
                    documento_id: int, **kwargs) -> ConditionResponse:
        """
        Crear una nueva condición médica
        
        Args:
            session: Sesión de base de datos
            condition_data: Datos de la condición a crear
            documento_id: ID del documento asociado (co-location key)
            
        Returns:
            ConditionResponse con la condición creada
        """
        try:
            # Validar que exista el paciente (opcional, dependiendo de reglas de negocio)
            # TODO: Implementar validación de existencia de paciente si es necesario
            
            # Convertir a modelo ORM usando mapper
            orm_condition = ConditionMapper.pydantic_to_orm(condition_data)
            orm_condition.documento_id = documento_id
            
            # Guardar en base de datos (Citus co-localizará por documento_id)
            session.add(orm_condition)
            await session.commit()
            await session.refresh(orm_condition)
            
            self.logger.info(f"Created condition with ID: {orm_condition.condicion_id} for document: {documento_id}")
            
            # Convertir a respuesta Pydantic
            pydantic_condition = ConditionMapper.orm_to_pydantic(orm_condition)
            return ConditionResponse(**pydantic_condition.dict())
            
        except ValidationException:
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "create_condition")
    
    async def get_by_id(self, session: AsyncSession, resource_id: str, 
                       documento_id: int) -> Optional[ConditionResponse]:
        """
        Obtener condición por ID
        
        Args:
            session: Sesión de base de datos
            resource_id: ID de la condición
            documento_id: ID del documento (co-location key)
            
        Returns:
            ConditionResponse o None si no se encuentra
        """
        try:
            condicion_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            result = await session.execute(
                select(ConditionORM).where(
                    and_(
                        ConditionORM.condicion_id == condicion_id,
                        ConditionORM.documento_id == documento_id
                    )
                )
            )
            orm_condition = result.scalar_one_or_none()
            
            if not orm_condition:
                return None
            
            pydantic_condition = ConditionMapper.orm_to_pydantic(orm_condition)
            return ConditionResponse(**pydantic_condition.dict())
            
        except Exception as e:
            self._handle_database_error(e, "get_condition_by_id")
    
    async def update(self, session: AsyncSession, resource_id: str, 
                    condition_data: ConditionUpdate, documento_id: int) -> ConditionResponse:
        """
        Actualizar condición existente
        
        Args:
            session: Sesión de base de datos
            resource_id: ID de la condición
            condition_data: Datos de actualización
            documento_id: ID del documento (co-location key)
            
        Returns:
            ConditionResponse con la condición actualizada
        """
        try:
            condicion_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            # Buscar condición existente
            result = await session.execute(
                select(ConditionORM).where(
                    and_(
                        ConditionORM.condicion_id == condicion_id,
                        ConditionORM.documento_id == documento_id
                    )
                )
            )
            orm_condition = result.scalar_one_or_none()
            
            if not orm_condition:
                raise ResourceNotFoundException("Condition", resource_id)
            
            # Actualizar campos modificados
            update_data = condition_data.dict(exclude_unset=True)
            
            # Mapear actualizaciones específicas
            if 'clinicalStatus' in update_data and update_data['clinicalStatus']:
                status = update_data['clinicalStatus']
                if 'coding' in status and status['coding']:
                    first_coding = status['coding'][0]
                    if 'code' in first_coding:
                        orm_condition.estado_clinico = first_coding['code']
            
            if 'verificationStatus' in update_data and update_data['verificationStatus']:
                status = update_data['verificationStatus']
                if 'coding' in status and status['coding']:
                    first_coding = status['coding'][0]
                    if 'code' in first_coding:
                        orm_condition.estado_verificacion = first_coding['code']
            
            if 'category' in update_data and update_data['category']:
                first_category = update_data['category'][0]
                if 'coding' in first_category and first_category['coding']:
                    first_coding = first_category['coding'][0]
                    if 'code' in first_coding:
                        orm_condition.categoria = first_coding['code']
            
            if 'severity' in update_data and update_data['severity']:
                severity = update_data['severity']
                if 'coding' in severity and severity['coding']:
                    first_coding = severity['coding'][0]
                    if 'code' in first_coding:
                        orm_condition.severidad = first_coding['code']
            
            if 'code' in update_data and update_data['code']:
                code = update_data['code']
                if 'coding' in code and code['coding']:
                    first_coding = code['coding'][0]
                    if 'code' in first_coding:
                        orm_condition.codigo_snomed = first_coding['code']
                    if 'display' in first_coding:
                        orm_condition.descripcion = first_coding['display']
                elif 'text' in code:
                    orm_condition.descripcion = code['text']
            
            if 'onsetDateTime' in update_data:
                if isinstance(update_data['onsetDateTime'], str):
                    orm_condition.fecha_inicio = datetime.fromisoformat(
                        update_data['onsetDateTime'].replace('Z', '+00:00')
                    )
                else:
                    orm_condition.fecha_inicio = update_data['onsetDateTime']
            
            if 'abatementDateTime' in update_data:
                if isinstance(update_data['abatementDateTime'], str):
                    orm_condition.fecha_resolucion = datetime.fromisoformat(
                        update_data['abatementDateTime'].replace('Z', '+00:00')
                    )
                else:
                    orm_condition.fecha_resolucion = update_data['abatementDateTime']
            
            if 'recordedDate' in update_data:
                if isinstance(update_data['recordedDate'], str):
                    orm_condition.fecha_registro = datetime.fromisoformat(
                        update_data['recordedDate'].replace('Z', '+00:00')
                    )
                else:
                    orm_condition.fecha_registro = update_data['recordedDate']
            
            # Actualizar timestamp de modificación
            orm_condition.updated_at = datetime.utcnow()
            orm_condition.fhir_last_updated = datetime.utcnow()
            
            await session.commit()
            await session.refresh(orm_condition)
            
            self.logger.info(f"Updated condition with ID: {condicion_id}")
            
            pydantic_condition = ConditionMapper.orm_to_pydantic(orm_condition)
            return ConditionResponse(**pydantic_condition.dict())
            
        except (ResourceNotFoundException, ValidationException):
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "update_condition")
    
    async def delete(self, session: AsyncSession, resource_id: str, 
                    documento_id: int) -> bool:
        """
        Eliminar condición
        
        Args:
            session: Sesión de base de datos
            resource_id: ID de la condición
            documento_id: ID del documento (co-location key)
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            condicion_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            # Buscar condición existente
            result = await session.execute(
                select(ConditionORM).where(
                    and_(
                        ConditionORM.condicion_id == condicion_id,
                        ConditionORM.documento_id == documento_id
                    )
                )
            )
            orm_condition = result.scalar_one_or_none()
            
            if not orm_condition:
                raise ResourceNotFoundException("Condition", resource_id)
            
            # Eliminar condición
            await session.delete(orm_condition)
            await session.commit()
            
            self.logger.info(f"Deleted condition with ID: {condicion_id}")
            return True
            
        except ResourceNotFoundException:
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "delete_condition")
    
    async def search(self, session: AsyncSession, search_params: ConditionSearchParams, 
                    documento_id: int = None) -> Dict[str, Any]:
        """
        Buscar condiciones con filtros y paginación
        
        Args:
            session: Sesión de base de datos
            search_params: Parámetros de búsqueda
            documento_id: ID del documento (opcional para búsqueda global)
            
        Returns:
            Resultado paginado con condiciones encontradas
        """
        try:
            # Construir query base
            query = select(ConditionORM)
            count_query = select(func.count()).select_from(ConditionORM)
            
            # Aplicar filtros
            filters = []
            
            # Filtro por documento si se especifica
            if documento_id:
                filters.append(ConditionORM.documento_id == documento_id)
            
            if search_params.patient:
                # Asumir que search_params.patient contiene el ID del paciente
                filters.append(ConditionORM.paciente_id == int(search_params.patient))
            
            if search_params.code:
                filters.append(ConditionORM.codigo_snomed == search_params.code)
            
            if search_params.category:
                filters.append(ConditionORM.categoria == search_params.category)
            
            if search_params.clinical_status:
                filters.append(ConditionORM.estado_clinico == search_params.clinical_status)
            
            if search_params.verification_status:
                filters.append(ConditionORM.estado_verificacion == search_params.verification_status)
            
            if search_params.severity:
                filters.append(ConditionORM.severidad == search_params.severity)
            
            if search_params.onset_date:
                # Parsear fecha para búsqueda
                if isinstance(search_params.onset_date, str):
                    search_date = datetime.fromisoformat(search_params.onset_date.replace('Z', '+00:00')).date()
                else:
                    search_date = search_params.onset_date
                
                filters.append(func.date(ConditionORM.fecha_inicio) == search_date)
            
            if search_params.recorded_date:
                # Parsear fecha para búsqueda
                if isinstance(search_params.recorded_date, str):
                    search_date = datetime.fromisoformat(search_params.recorded_date.replace('Z', '+00:00')).date()
                else:
                    search_date = search_params.recorded_date
                
                filters.append(func.date(ConditionORM.fecha_registro) == search_date)
            
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
                if search_params.sort == "onset-date":
                    order_field = ConditionORM.fecha_inicio
                elif search_params.sort == "recorded-date":
                    order_field = ConditionORM.fecha_registro
                elif search_params.sort == "clinical-status":
                    order_field = ConditionORM.estado_clinico
                elif search_params.sort == "code":
                    order_field = ConditionORM.codigo_snomed
                else:
                    order_field = ConditionORM.created_at
                
                if search_params.order == "asc":
                    query = query.order_by(order_field.asc())
                else:
                    query = query.order_by(order_field.desc())
            else:
                query = query.order_by(ConditionORM.fecha_inicio.desc())
            
            query = query.limit(search_params.size).offset(offset)
            
            # Ejecutar query
            result = await session.execute(query)
            orm_conditions = result.scalars().all()
            
            # Convertir a modelos Pydantic
            pydantic_conditions = []
            for orm_condition in orm_conditions:
                pydantic_condition = ConditionMapper.orm_to_pydantic(orm_condition)
                pydantic_conditions.append(ConditionResponse(**pydantic_condition.dict()))
            
            return self._create_search_response(
                pydantic_conditions, total, search_params.page, search_params.size
            )
            
        except Exception as e:
            self._handle_database_error(e, "search_conditions")
    
    async def get_by_patient(self, session: AsyncSession, paciente_id: int, 
                           documento_id: int = None) -> List[ConditionResponse]:
        """
        Obtener todas las condiciones de un paciente
        
        Args:
            session: Sesión de base de datos
            paciente_id: ID del paciente
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de condiciones del paciente
        """
        try:
            filters = [ConditionORM.paciente_id == paciente_id]
            if documento_id:
                filters.append(ConditionORM.documento_id == documento_id)
            
            result = await session.execute(
                select(ConditionORM)
                .where(and_(*filters))
                .order_by(ConditionORM.fecha_inicio.desc())
            )
            orm_conditions = result.scalars().all()
            
            conditions = []
            for orm_condition in orm_conditions:
                pydantic_condition = ConditionMapper.orm_to_pydantic(orm_condition)
                conditions.append(ConditionResponse(**pydantic_condition.dict()))
            
            return conditions
            
        except Exception as e:
            self._handle_database_error(e, "get_conditions_by_patient")
    
    async def get_active_conditions(self, session: AsyncSession, paciente_id: int, 
                                  documento_id: int = None) -> List[ConditionResponse]:
        """
        Obtener condiciones activas de un paciente
        
        Args:
            session: Sesión de base de datos
            paciente_id: ID del paciente
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de condiciones activas del paciente
        """
        try:
            filters = [
                ConditionORM.paciente_id == paciente_id,
                ConditionORM.estado_clinico == "active"
            ]
            if documento_id:
                filters.append(ConditionORM.documento_id == documento_id)
            
            result = await session.execute(
                select(ConditionORM)
                .where(and_(*filters))
                .order_by(ConditionORM.fecha_inicio.desc())
            )
            orm_conditions = result.scalars().all()
            
            conditions = []
            for orm_condition in orm_conditions:
                pydantic_condition = ConditionMapper.orm_to_pydantic(orm_condition)
                conditions.append(ConditionResponse(**pydantic_condition.dict()))
            
            return conditions
            
        except Exception as e:
            self._handle_database_error(e, "get_active_conditions_by_patient")
    
    async def get_by_category(self, session: AsyncSession, categoria: str, 
                            documento_id: int = None) -> List[ConditionResponse]:
        """
        Obtener condiciones por categoría
        
        Args:
            session: Sesión de base de datos
            categoria: Categoría a buscar
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de condiciones de la categoría especificada
        """
        try:
            filters = [ConditionORM.categoria == categoria]
            if documento_id:
                filters.append(ConditionORM.documento_id == documento_id)
            
            result = await session.execute(
                select(ConditionORM)
                .where(and_(*filters))
                .order_by(ConditionORM.fecha_inicio.desc())
            )
            orm_conditions = result.scalars().all()
            
            conditions = []
            for orm_condition in orm_conditions:
                pydantic_condition = ConditionMapper.orm_to_pydantic(orm_condition)
                conditions.append(ConditionResponse(**pydantic_condition.dict()))
            
            return conditions
            
        except Exception as e:
            self._handle_database_error(e, "get_conditions_by_category")
    
    async def get_chronic_conditions(self, session: AsyncSession, paciente_id: int, 
                                   documento_id: int = None) -> List[ConditionResponse]:
        """
        Obtener condiciones crónicas de un paciente
        
        Args:
            session: Sesión de base de datos
            paciente_id: ID del paciente
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de condiciones crónicas del paciente
        """
        try:
            filters = [
                ConditionORM.paciente_id == paciente_id,
                or_(
                    ConditionORM.categoria == "problem-list-item",
                    ConditionORM.severidad.in_(["severe", "moderate"])
                ),
                ConditionORM.fecha_resolucion.is_(None)  # Sin fecha de resolución
            ]
            if documento_id:
                filters.append(ConditionORM.documento_id == documento_id)
            
            result = await session.execute(
                select(ConditionORM)
                .where(and_(*filters))
                .order_by(ConditionORM.fecha_inicio.desc())
            )
            orm_conditions = result.scalars().all()
            
            conditions = []
            for orm_condition in orm_conditions:
                pydantic_condition = ConditionMapper.orm_to_pydantic(orm_condition)
                conditions.append(ConditionResponse(**pydantic_condition.dict()))
            
            return conditions
            
        except Exception as e:
            self._handle_database_error(e, "get_chronic_conditions_by_patient")


# Instancia global del servicio (singleton)
condition_service = ConditionService()

# Exportaciones del módulo
__all__ = [
    "ConditionService",
    "condition_service"
]