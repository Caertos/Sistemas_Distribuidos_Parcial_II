"""
MedicationRequest Service - Servicio de negocio para gestión de solicitudes de medicamentos FHIR
Implementa operaciones CRUD específicas para recursos MedicationRequest
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime, date

from app.models import (
    MedicationRequest as PydanticMedicationRequest,
    MedicationRequestCreate,
    MedicationRequestUpdate,
    MedicationRequestResponse,
    MedicationRequestSearchParams
)
from app.models.orm import MedicationRequestORM
from app.models.orm.mappers import MedicationRequestMapper
from .base import DistributedService, ResourceNotFoundException, ValidationException


class MedicationRequestService(DistributedService):
    """
    Servicio de negocio para gestión de solicitudes de medicamentos
    
    Implementa operaciones CRUD y lógica de negocio específica para MedicationRequest FHIR
    """
    
    def __init__(self):
        super().__init__(
            pydantic_model=PydanticMedicationRequest,
            orm_model=MedicationRequestORM,
            create_model=MedicationRequestCreate,
            update_model=MedicationRequestUpdate,
            resource_name="MedicationRequest"
        )
    
    async def create(self, session: AsyncSession, medication_request_data: MedicationRequestCreate, 
                    documento_id: int, **kwargs) -> MedicationRequestResponse:
        """
        Crear una nueva solicitud de medicamento
        
        Args:
            session: Sesión de base de datos
            medication_request_data: Datos de la solicitud a crear
            documento_id: ID del documento asociado (co-location key)
            
        Returns:
            MedicationRequestResponse con la solicitud creada
        """
        try:
            # Validar que exista el paciente y el profesional (opcional)
            # TODO: Implementar validación de existencia de paciente y profesional si es necesario
            
            # Convertir a modelo ORM usando mapper
            orm_medication_request = MedicationRequestMapper.pydantic_to_orm(medication_request_data)
            orm_medication_request.documento_id = documento_id
            
            # Guardar en base de datos (Citus co-localizará por documento_id)
            session.add(orm_medication_request)
            await session.commit()
            await session.refresh(orm_medication_request)
            
            self.logger.info(f"Created medication request with ID: {orm_medication_request.prescripcion_id} for document: {documento_id}")
            
            # Convertir a respuesta Pydantic
            pydantic_medication_request = MedicationRequestMapper.orm_to_pydantic(orm_medication_request)
            return MedicationRequestResponse(**pydantic_medication_request.dict())
            
        except ValidationException:
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "create_medication_request")
    
    async def get_by_id(self, session: AsyncSession, resource_id: str, 
                       documento_id: int) -> Optional[MedicationRequestResponse]:
        """
        Obtener solicitud de medicamento por ID
        
        Args:
            session: Sesión de base de datos
            resource_id: ID de la solicitud
            documento_id: ID del documento (co-location key)
            
        Returns:
            MedicationRequestResponse o None si no se encuentra
        """
        try:
            prescripcion_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            result = await session.execute(
                select(MedicationRequestORM).where(
                    and_(
                        MedicationRequestORM.prescripcion_id == prescripcion_id,
                        MedicationRequestORM.documento_id == documento_id
                    )
                )
            )
            orm_medication_request = result.scalar_one_or_none()
            
            if not orm_medication_request:
                return None
            
            pydantic_medication_request = MedicationRequestMapper.orm_to_pydantic(orm_medication_request)
            return MedicationRequestResponse(**pydantic_medication_request.dict())
            
        except Exception as e:
            self._handle_database_error(e, "get_medication_request_by_id")
    
    async def update(self, session: AsyncSession, resource_id: str, 
                    medication_request_data: MedicationRequestUpdate, documento_id: int) -> MedicationRequestResponse:
        """
        Actualizar solicitud de medicamento existente
        
        Args:
            session: Sesión de base de datos
            resource_id: ID de la solicitud
            medication_request_data: Datos de actualización
            documento_id: ID del documento (co-location key)
            
        Returns:
            MedicationRequestResponse con la solicitud actualizada
        """
        try:
            prescripcion_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            # Buscar solicitud existente
            result = await session.execute(
                select(MedicationRequestORM).where(
                    and_(
                        MedicationRequestORM.prescripcion_id == prescripcion_id,
                        MedicationRequestORM.documento_id == documento_id
                    )
                )
            )
            orm_medication_request = result.scalar_one_or_none()
            
            if not orm_medication_request:
                raise ResourceNotFoundException("MedicationRequest", resource_id)
            
            # Actualizar campos modificados
            update_data = medication_request_data.dict(exclude_unset=True)
            
            # Mapear actualizaciones específicas
            if 'status' in update_data:
                orm_medication_request.estado = update_data['status']
            
            if 'intent' in update_data:
                orm_medication_request.intencion = update_data['intent']
            
            if 'priority' in update_data:
                orm_medication_request.prioridad = update_data['priority']
            
            if 'medicationCodeableConcept' in update_data and update_data['medicationCodeableConcept']:
                medication = update_data['medicationCodeableConcept']
                if 'coding' in medication and medication['coding']:
                    first_coding = medication['coding'][0]
                    if 'code' in first_coding:
                        orm_medication_request.codigo_medicamento = first_coding['code']
                    if 'display' in first_coding:
                        orm_medication_request.nombre_medicamento = first_coding['display']
                elif 'text' in medication:
                    orm_medication_request.nombre_medicamento = medication['text']
            
            if 'dosageInstruction' in update_data and update_data['dosageInstruction']:
                first_dosage = update_data['dosageInstruction'][0]
                if 'text' in first_dosage:
                    orm_medication_request.instrucciones_dosificacion = first_dosage['text']
                if 'doseAndRate' in first_dosage and first_dosage['doseAndRate']:
                    dose_rate = first_dosage['doseAndRate'][0]
                    if 'doseQuantity' in dose_rate and dose_rate['doseQuantity']:
                        dose_qty = dose_rate['doseQuantity']
                        if 'value' in dose_qty:
                            orm_medication_request.dosis = str(dose_qty['value'])
                        if 'unit' in dose_qty:
                            orm_medication_request.unidad_dosis = dose_qty['unit']
                if 'timing' in first_dosage and first_dosage['timing']:
                    timing = first_dosage['timing']
                    if 'repeat' in timing and timing['repeat']:
                        repeat = timing['repeat']
                        if 'frequency' in repeat:
                            orm_medication_request.frecuencia = str(repeat['frequency'])
                        if 'period' in repeat:
                            orm_medication_request.periodo = str(repeat['period'])
                        if 'periodUnit' in repeat:
                            orm_medication_request.unidad_periodo = repeat['periodUnit']
            
            if 'dispenseRequest' in update_data and update_data['dispenseRequest']:
                dispense = update_data['dispenseRequest']
                if 'quantity' in dispense and dispense['quantity']:
                    quantity = dispense['quantity']
                    if 'value' in quantity:
                        orm_medication_request.cantidad_solicitada = int(quantity['value'])
                    if 'unit' in quantity:
                        orm_medication_request.unidad_cantidad = quantity['unit']
                if 'numberOfRepeatsAllowed' in dispense:
                    orm_medication_request.renovaciones_permitidas = dispense['numberOfRepeatsAllowed']
                if 'expectedSupplyDuration' in dispense and dispense['expectedSupplyDuration']:
                    duration = dispense['expectedSupplyDuration']
                    if 'value' in duration:
                        orm_medication_request.duracion_tratamiento = int(duration['value'])
                    if 'unit' in duration:
                        orm_medication_request.unidad_duracion = duration['unit']
            
            if 'authoredOn' in update_data:
                if isinstance(update_data['authoredOn'], str):
                    orm_medication_request.fecha_prescripcion = datetime.fromisoformat(
                        update_data['authoredOn'].replace('Z', '+00:00')
                    )
                else:
                    orm_medication_request.fecha_prescripcion = update_data['authoredOn']
            
            # Actualizar timestamp de modificación
            orm_medication_request.updated_at = datetime.utcnow()
            orm_medication_request.fhir_last_updated = datetime.utcnow()
            
            await session.commit()
            await session.refresh(orm_medication_request)
            
            self.logger.info(f"Updated medication request with ID: {prescripcion_id}")
            
            pydantic_medication_request = MedicationRequestMapper.orm_to_pydantic(orm_medication_request)
            return MedicationRequestResponse(**pydantic_medication_request.dict())
            
        except (ResourceNotFoundException, ValidationException):
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "update_medication_request")
    
    async def delete(self, session: AsyncSession, resource_id: str, 
                    documento_id: int) -> bool:
        """
        Eliminar solicitud de medicamento
        
        Args:
            session: Sesión de base de datos
            resource_id: ID de la solicitud
            documento_id: ID del documento (co-location key)
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            prescripcion_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            # Buscar solicitud existente
            result = await session.execute(
                select(MedicationRequestORM).where(
                    and_(
                        MedicationRequestORM.prescripcion_id == prescripcion_id,
                        MedicationRequestORM.documento_id == documento_id
                    )
                )
            )
            orm_medication_request = result.scalar_one_or_none()
            
            if not orm_medication_request:
                raise ResourceNotFoundException("MedicationRequest", resource_id)
            
            # Eliminar solicitud (considerar cambiar estado en lugar de eliminar físicamente)
            await session.delete(orm_medication_request)
            await session.commit()
            
            self.logger.info(f"Deleted medication request with ID: {prescripcion_id}")
            return True
            
        except ResourceNotFoundException:
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "delete_medication_request")
    
    async def search(self, session: AsyncSession, search_params: MedicationRequestSearchParams, 
                    documento_id: int = None) -> Dict[str, Any]:
        """
        Buscar solicitudes de medicamentos con filtros y paginación
        
        Args:
            session: Sesión de base de datos
            search_params: Parámetros de búsqueda
            documento_id: ID del documento (opcional para búsqueda global)
            
        Returns:
            Resultado paginado con solicitudes encontradas
        """
        try:
            # Construir query base
            query = select(MedicationRequestORM)
            count_query = select(func.count()).select_from(MedicationRequestORM)
            
            # Aplicar filtros
            filters = []
            
            # Filtro por documento si se especifica
            if documento_id:
                filters.append(MedicationRequestORM.documento_id == documento_id)
            
            if search_params.patient:
                # Asumir que search_params.patient contiene el ID del paciente
                filters.append(MedicationRequestORM.paciente_id == int(search_params.patient))
            
            if search_params.medication:
                filters.append(
                    or_(
                        MedicationRequestORM.codigo_medicamento == search_params.medication,
                        MedicationRequestORM.nombre_medicamento.ilike(f"%{search_params.medication}%")
                    )
                )
            
            if search_params.status:
                filters.append(MedicationRequestORM.estado == search_params.status)
            
            if search_params.intent:
                filters.append(MedicationRequestORM.intencion == search_params.intent)
            
            if search_params.priority:
                filters.append(MedicationRequestORM.prioridad == search_params.priority)
            
            if search_params.requester:
                filters.append(MedicationRequestORM.profesional_id == int(search_params.requester))
            
            if search_params.authored_on:
                # Parsear fecha para búsqueda
                if isinstance(search_params.authored_on, str):
                    search_date = datetime.fromisoformat(search_params.authored_on.replace('Z', '+00:00')).date()
                else:
                    search_date = search_params.authored_on
                
                filters.append(func.date(MedicationRequestORM.fecha_prescripcion) == search_date)
            
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
                if search_params.sort == "authored-on":
                    order_field = MedicationRequestORM.fecha_prescripcion
                elif search_params.sort == "status":
                    order_field = MedicationRequestORM.estado
                elif search_params.sort == "medication":
                    order_field = MedicationRequestORM.nombre_medicamento
                elif search_params.sort == "priority":
                    order_field = MedicationRequestORM.prioridad
                else:
                    order_field = MedicationRequestORM.created_at
                
                if search_params.order == "asc":
                    query = query.order_by(order_field.asc())
                else:
                    query = query.order_by(order_field.desc())
            else:
                query = query.order_by(MedicationRequestORM.fecha_prescripcion.desc())
            
            query = query.limit(search_params.size).offset(offset)
            
            # Ejecutar query
            result = await session.execute(query)
            orm_medication_requests = result.scalars().all()
            
            # Convertir a modelos Pydantic
            pydantic_medication_requests = []
            for orm_medication_request in orm_medication_requests:
                pydantic_medication_request = MedicationRequestMapper.orm_to_pydantic(orm_medication_request)
                pydantic_medication_requests.append(MedicationRequestResponse(**pydantic_medication_request.dict()))
            
            return self._create_search_response(
                pydantic_medication_requests, total, search_params.page, search_params.size
            )
            
        except Exception as e:
            self._handle_database_error(e, "search_medication_requests")
    
    async def get_by_patient(self, session: AsyncSession, paciente_id: int, 
                           documento_id: int = None) -> List[MedicationRequestResponse]:
        """
        Obtener todas las solicitudes de medicamentos de un paciente
        
        Args:
            session: Sesión de base de datos
            paciente_id: ID del paciente
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de solicitudes de medicamentos del paciente
        """
        try:
            filters = [MedicationRequestORM.paciente_id == paciente_id]
            if documento_id:
                filters.append(MedicationRequestORM.documento_id == documento_id)
            
            result = await session.execute(
                select(MedicationRequestORM)
                .where(and_(*filters))
                .order_by(MedicationRequestORM.fecha_prescripcion.desc())
            )
            orm_medication_requests = result.scalars().all()
            
            medication_requests = []
            for orm_medication_request in orm_medication_requests:
                pydantic_medication_request = MedicationRequestMapper.orm_to_pydantic(orm_medication_request)
                medication_requests.append(MedicationRequestResponse(**pydantic_medication_request.dict()))
            
            return medication_requests
            
        except Exception as e:
            self._handle_database_error(e, "get_medication_requests_by_patient")
    
    async def get_active_prescriptions(self, session: AsyncSession, paciente_id: int, 
                                     documento_id: int = None) -> List[MedicationRequestResponse]:
        """
        Obtener prescripciones activas de un paciente
        
        Args:
            session: Sesión de base de datos
            paciente_id: ID del paciente
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de prescripciones activas del paciente
        """
        try:
            filters = [
                MedicationRequestORM.paciente_id == paciente_id,
                MedicationRequestORM.estado.in_(["active", "completed"])
            ]
            if documento_id:
                filters.append(MedicationRequestORM.documento_id == documento_id)
            
            result = await session.execute(
                select(MedicationRequestORM)
                .where(and_(*filters))
                .order_by(MedicationRequestORM.fecha_prescripcion.desc())
            )
            orm_medication_requests = result.scalars().all()
            
            medication_requests = []
            for orm_medication_request in orm_medication_requests:
                pydantic_medication_request = MedicationRequestMapper.orm_to_pydantic(orm_medication_request)
                medication_requests.append(MedicationRequestResponse(**pydantic_medication_request.dict()))
            
            return medication_requests
            
        except Exception as e:
            self._handle_database_error(e, "get_active_prescriptions_by_patient")
    
    async def get_by_professional(self, session: AsyncSession, profesional_id: int, 
                                documento_id: int = None) -> List[MedicationRequestResponse]:
        """
        Obtener solicitudes de medicamentos por profesional prescriptor
        
        Args:
            session: Sesión de base de datos
            profesional_id: ID del profesional
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de solicitudes del profesional
        """
        try:
            filters = [MedicationRequestORM.profesional_id == profesional_id]
            if documento_id:
                filters.append(MedicationRequestORM.documento_id == documento_id)
            
            result = await session.execute(
                select(MedicationRequestORM)
                .where(and_(*filters))
                .order_by(MedicationRequestORM.fecha_prescripcion.desc())
            )
            orm_medication_requests = result.scalars().all()
            
            medication_requests = []
            for orm_medication_request in orm_medication_requests:
                pydantic_medication_request = MedicationRequestMapper.orm_to_pydantic(orm_medication_request)
                medication_requests.append(MedicationRequestResponse(**pydantic_medication_request.dict()))
            
            return medication_requests
            
        except Exception as e:
            self._handle_database_error(e, "get_medication_requests_by_professional")
    
    async def get_by_medication(self, session: AsyncSession, codigo_medicamento: str, 
                              documento_id: int = None) -> List[MedicationRequestResponse]:
        """
        Obtener solicitudes por medicamento específico
        
        Args:
            session: Sesión de base de datos
            codigo_medicamento: Código del medicamento
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de solicitudes del medicamento
        """
        try:
            filters = [MedicationRequestORM.codigo_medicamento == codigo_medicamento]
            if documento_id:
                filters.append(MedicationRequestORM.documento_id == documento_id)
            
            result = await session.execute(
                select(MedicationRequestORM)
                .where(and_(*filters))
                .order_by(MedicationRequestORM.fecha_prescripcion.desc())
            )
            orm_medication_requests = result.scalars().all()
            
            medication_requests = []
            for orm_medication_request in orm_medication_requests:
                pydantic_medication_request = MedicationRequestMapper.orm_to_pydantic(orm_medication_request)
                medication_requests.append(MedicationRequestResponse(**pydantic_medication_request.dict()))
            
            return medication_requests
            
        except Exception as e:
            self._handle_database_error(e, "get_medication_requests_by_medication")


# Instancia global del servicio (singleton)
medication_request_service = MedicationRequestService()

# Exportaciones del módulo
__all__ = [
    "MedicationRequestService",
    "medication_request_service"
]