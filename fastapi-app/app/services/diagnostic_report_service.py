"""
DiagnosticReport Service - Servicio de negocio para gestión de reportes diagnósticos FHIR
Implementa operaciones CRUD específicas para recursos DiagnosticReport
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime, date

from app.models import (
    DiagnosticReport as PydanticDiagnosticReport,
    DiagnosticReportCreate,
    DiagnosticReportUpdate,
    DiagnosticReportResponse,
    DiagnosticReportSearchParams
)
from app.models.orm import DiagnosticReportORM
from app.models.orm.mappers import DiagnosticReportMapper
from .base import DistributedService, ResourceNotFoundException, ValidationException


class DiagnosticReportService(DistributedService):
    """
    Servicio de negocio para gestión de reportes diagnósticos
    
    Implementa operaciones CRUD y lógica de negocio específica para DiagnosticReport FHIR
    """
    
    def __init__(self):
        super().__init__(
            pydantic_model=PydanticDiagnosticReport,
            orm_model=DiagnosticReportORM,
            create_model=DiagnosticReportCreate,
            update_model=DiagnosticReportUpdate,
            resource_name="DiagnosticReport"
        )
    
    async def create(self, session: AsyncSession, diagnostic_report_data: DiagnosticReportCreate, 
                    documento_id: int, **kwargs) -> DiagnosticReportResponse:
        """
        Crear un nuevo reporte diagnóstico
        
        Args:
            session: Sesión de base de datos
            diagnostic_report_data: Datos del reporte a crear
            documento_id: ID del documento asociado (co-location key)
            
        Returns:
            DiagnosticReportResponse con el reporte creado
        """
        try:
            # Validar que exista el paciente y el profesional (opcional)
            # TODO: Implementar validación de existencia de paciente y profesional si es necesario
            
            # Convertir a modelo ORM usando mapper
            orm_diagnostic_report = DiagnosticReportMapper.pydantic_to_orm(diagnostic_report_data)
            orm_diagnostic_report.documento_id = documento_id
            
            # Guardar en base de datos (Citus co-localizará por documento_id)
            session.add(orm_diagnostic_report)
            await session.commit()
            await session.refresh(orm_diagnostic_report)
            
            self.logger.info(f"Created diagnostic report with ID: {orm_diagnostic_report.reporte_id} for document: {documento_id}")
            
            # Convertir a respuesta Pydantic
            pydantic_diagnostic_report = DiagnosticReportMapper.orm_to_pydantic(orm_diagnostic_report)
            return DiagnosticReportResponse(**pydantic_diagnostic_report.dict())
            
        except ValidationException:
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "create_diagnostic_report")
    
    async def get_by_id(self, session: AsyncSession, resource_id: str, 
                       documento_id: int) -> Optional[DiagnosticReportResponse]:
        """
        Obtener reporte diagnóstico por ID
        
        Args:
            session: Sesión de base de datos
            resource_id: ID del reporte
            documento_id: ID del documento (co-location key)
            
        Returns:
            DiagnosticReportResponse o None si no se encuentra
        """
        try:
            reporte_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            result = await session.execute(
                select(DiagnosticReportORM).where(
                    and_(
                        DiagnosticReportORM.reporte_id == reporte_id,
                        DiagnosticReportORM.documento_id == documento_id
                    )
                )
            )
            orm_diagnostic_report = result.scalar_one_or_none()
            
            if not orm_diagnostic_report:
                return None
            
            pydantic_diagnostic_report = DiagnosticReportMapper.orm_to_pydantic(orm_diagnostic_report)
            return DiagnosticReportResponse(**pydantic_diagnostic_report.dict())
            
        except Exception as e:
            self._handle_database_error(e, "get_diagnostic_report_by_id")
    
    async def update(self, session: AsyncSession, resource_id: str, 
                    diagnostic_report_data: DiagnosticReportUpdate, documento_id: int) -> DiagnosticReportResponse:
        """
        Actualizar reporte diagnóstico existente
        
        Args:
            session: Sesión de base de datos
            resource_id: ID del reporte
            diagnostic_report_data: Datos de actualización
            documento_id: ID del documento (co-location key)
            
        Returns:
            DiagnosticReportResponse con el reporte actualizado
        """
        try:
            reporte_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            # Buscar reporte existente
            result = await session.execute(
                select(DiagnosticReportORM).where(
                    and_(
                        DiagnosticReportORM.reporte_id == reporte_id,
                        DiagnosticReportORM.documento_id == documento_id
                    )
                )
            )
            orm_diagnostic_report = result.scalar_one_or_none()
            
            if not orm_diagnostic_report:
                raise ResourceNotFoundException("DiagnosticReport", resource_id)
            
            # Actualizar campos modificados
            update_data = diagnostic_report_data.dict(exclude_unset=True)
            
            # Mapear actualizaciones específicas
            if 'status' in update_data:
                orm_diagnostic_report.estado = update_data['status']
            
            if 'category' in update_data and update_data['category']:
                first_category = update_data['category'][0]
                if 'coding' in first_category and first_category['coding']:
                    first_coding = first_category['coding'][0]
                    if 'code' in first_coding:
                        orm_diagnostic_report.categoria = first_coding['code']
            
            if 'code' in update_data and update_data['code']:
                code = update_data['code']
                if 'coding' in code and code['coding']:
                    first_coding = code['coding'][0]
                    if 'code' in first_coding:
                        orm_diagnostic_report.codigo_loinc = first_coding['code']
                    if 'display' in first_coding:
                        orm_diagnostic_report.nombre_estudio = first_coding['display']
                elif 'text' in code:
                    orm_diagnostic_report.nombre_estudio = code['text']
            
            if 'conclusion' in update_data:
                orm_diagnostic_report.conclusion = update_data['conclusion']
            
            if 'presentedForm' in update_data and update_data['presentedForm']:
                first_form = update_data['presentedForm'][0]
                if 'data' in first_form:
                    orm_diagnostic_report.resultado_completo = first_form['data']
                if 'contentType' in first_form:
                    orm_diagnostic_report.tipo_contenido = first_form['contentType']
            
            if 'conclusionCode' in update_data and update_data['conclusionCode']:
                first_conclusion_code = update_data['conclusionCode'][0]
                if 'coding' in first_conclusion_code and first_conclusion_code['coding']:
                    first_coding = first_conclusion_code['coding'][0]
                    if 'code' in first_coding:
                        orm_diagnostic_report.codigo_conclusion = first_coding['code']
            
            if 'effectiveDateTime' in update_data:
                if isinstance(update_data['effectiveDateTime'], str):
                    orm_diagnostic_report.fecha_estudio = datetime.fromisoformat(
                        update_data['effectiveDateTime'].replace('Z', '+00:00')
                    )
                else:
                    orm_diagnostic_report.fecha_estudio = update_data['effectiveDateTime']
            
            if 'issued' in update_data:
                if isinstance(update_data['issued'], str):
                    orm_diagnostic_report.fecha_emision = datetime.fromisoformat(
                        update_data['issued'].replace('Z', '+00:00')
                    )
                else:
                    orm_diagnostic_report.fecha_emision = update_data['issued']
            
            # Actualizar timestamp de modificación
            orm_diagnostic_report.updated_at = datetime.utcnow()
            orm_diagnostic_report.fhir_last_updated = datetime.utcnow()
            
            await session.commit()
            await session.refresh(orm_diagnostic_report)
            
            self.logger.info(f"Updated diagnostic report with ID: {reporte_id}")
            
            pydantic_diagnostic_report = DiagnosticReportMapper.orm_to_pydantic(orm_diagnostic_report)
            return DiagnosticReportResponse(**pydantic_diagnostic_report.dict())
            
        except (ResourceNotFoundException, ValidationException):
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "update_diagnostic_report")
    
    async def delete(self, session: AsyncSession, resource_id: str, 
                    documento_id: int) -> bool:
        """
        Eliminar reporte diagnóstico
        
        Args:
            session: Sesión de base de datos
            resource_id: ID del reporte
            documento_id: ID del documento (co-location key)
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            reporte_id = int(resource_id) if isinstance(resource_id, str) else resource_id
            
            # Buscar reporte existente
            result = await session.execute(
                select(DiagnosticReportORM).where(
                    and_(
                        DiagnosticReportORM.reporte_id == reporte_id,
                        DiagnosticReportORM.documento_id == documento_id
                    )
                )
            )
            orm_diagnostic_report = result.scalar_one_or_none()
            
            if not orm_diagnostic_report:
                raise ResourceNotFoundException("DiagnosticReport", resource_id)
            
            # Eliminar reporte
            await session.delete(orm_diagnostic_report)
            await session.commit()
            
            self.logger.info(f"Deleted diagnostic report with ID: {reporte_id}")
            return True
            
        except ResourceNotFoundException:
            raise
        except Exception as e:
            await session.rollback()
            self._handle_database_error(e, "delete_diagnostic_report")
    
    async def search(self, session: AsyncSession, search_params: DiagnosticReportSearchParams, 
                    documento_id: int = None) -> Dict[str, Any]:
        """
        Buscar reportes diagnósticos con filtros y paginación
        
        Args:
            session: Sesión de base de datos
            search_params: Parámetros de búsqueda
            documento_id: ID del documento (opcional para búsqueda global)
            
        Returns:
            Resultado paginado con reportes encontrados
        """
        try:
            # Construir query base
            query = select(DiagnosticReportORM)
            count_query = select(func.count()).select_from(DiagnosticReportORM)
            
            # Aplicar filtros
            filters = []
            
            # Filtro por documento si se especifica
            if documento_id:
                filters.append(DiagnosticReportORM.documento_id == documento_id)
            
            if search_params.patient:
                # Asumir que search_params.patient contiene el ID del paciente
                filters.append(DiagnosticReportORM.paciente_id == int(search_params.patient))
            
            if search_params.code:
                filters.append(DiagnosticReportORM.codigo_loinc == search_params.code)
            
            if search_params.category:
                filters.append(DiagnosticReportORM.categoria == search_params.category)
            
            if search_params.status:
                filters.append(DiagnosticReportORM.estado == search_params.status)
            
            if search_params.performer:
                filters.append(DiagnosticReportORM.profesional_id == int(search_params.performer))
            
            if search_params.date:
                # Parsear fecha para búsqueda
                if isinstance(search_params.date, str):
                    search_date = datetime.fromisoformat(search_params.date.replace('Z', '+00:00')).date()
                else:
                    search_date = search_params.date
                
                filters.append(func.date(DiagnosticReportORM.fecha_estudio) == search_date)
            
            if search_params.issued:
                # Parsear fecha para búsqueda
                if isinstance(search_params.issued, str):
                    search_date = datetime.fromisoformat(search_params.issued.replace('Z', '+00:00')).date()
                else:
                    search_date = search_params.issued
                
                filters.append(func.date(DiagnosticReportORM.fecha_emision) == search_date)
            
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
                    order_field = DiagnosticReportORM.fecha_estudio
                elif search_params.sort == "issued":
                    order_field = DiagnosticReportORM.fecha_emision
                elif search_params.sort == "status":
                    order_field = DiagnosticReportORM.estado
                elif search_params.sort == "code":
                    order_field = DiagnosticReportORM.codigo_loinc
                else:
                    order_field = DiagnosticReportORM.created_at
                
                if search_params.order == "asc":
                    query = query.order_by(order_field.asc())
                else:
                    query = query.order_by(order_field.desc())
            else:
                query = query.order_by(DiagnosticReportORM.fecha_estudio.desc())
            
            query = query.limit(search_params.size).offset(offset)
            
            # Ejecutar query
            result = await session.execute(query)
            orm_diagnostic_reports = result.scalars().all()
            
            # Convertir a modelos Pydantic
            pydantic_diagnostic_reports = []
            for orm_diagnostic_report in orm_diagnostic_reports:
                pydantic_diagnostic_report = DiagnosticReportMapper.orm_to_pydantic(orm_diagnostic_report)
                pydantic_diagnostic_reports.append(DiagnosticReportResponse(**pydantic_diagnostic_report.dict()))
            
            return self._create_search_response(
                pydantic_diagnostic_reports, total, search_params.page, search_params.size
            )
            
        except Exception as e:
            self._handle_database_error(e, "search_diagnostic_reports")
    
    async def get_by_patient(self, session: AsyncSession, paciente_id: int, 
                           documento_id: int = None) -> List[DiagnosticReportResponse]:
        """
        Obtener todos los reportes diagnósticos de un paciente
        
        Args:
            session: Sesión de base de datos
            paciente_id: ID del paciente
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de reportes diagnósticos del paciente
        """
        try:
            filters = [DiagnosticReportORM.paciente_id == paciente_id]
            if documento_id:
                filters.append(DiagnosticReportORM.documento_id == documento_id)
            
            result = await session.execute(
                select(DiagnosticReportORM)
                .where(and_(*filters))
                .order_by(DiagnosticReportORM.fecha_estudio.desc())
            )
            orm_diagnostic_reports = result.scalars().all()
            
            diagnostic_reports = []
            for orm_diagnostic_report in orm_diagnostic_reports:
                pydantic_diagnostic_report = DiagnosticReportMapper.orm_to_pydantic(orm_diagnostic_report)
                diagnostic_reports.append(DiagnosticReportResponse(**pydantic_diagnostic_report.dict()))
            
            return diagnostic_reports
            
        except Exception as e:
            self._handle_database_error(e, "get_diagnostic_reports_by_patient")
    
    async def get_by_category(self, session: AsyncSession, categoria: str, 
                            documento_id: int = None) -> List[DiagnosticReportResponse]:
        """
        Obtener reportes diagnósticos por categoría
        
        Args:
            session: Sesión de base de datos
            categoria: Categoría a buscar
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de reportes de la categoría especificada
        """
        try:
            filters = [DiagnosticReportORM.categoria == categoria]
            if documento_id:
                filters.append(DiagnosticReportORM.documento_id == documento_id)
            
            result = await session.execute(
                select(DiagnosticReportORM)
                .where(and_(*filters))
                .order_by(DiagnosticReportORM.fecha_estudio.desc())
            )
            orm_diagnostic_reports = result.scalars().all()
            
            diagnostic_reports = []
            for orm_diagnostic_report in orm_diagnostic_reports:
                pydantic_diagnostic_report = DiagnosticReportMapper.orm_to_pydantic(orm_diagnostic_report)
                diagnostic_reports.append(DiagnosticReportResponse(**pydantic_diagnostic_report.dict()))
            
            return diagnostic_reports
            
        except Exception as e:
            self._handle_database_error(e, "get_diagnostic_reports_by_category")
    
    async def get_laboratory_reports(self, session: AsyncSession, paciente_id: int, 
                                   documento_id: int = None) -> List[DiagnosticReportResponse]:
        """
        Obtener reportes de laboratorio de un paciente
        
        Args:
            session: Sesión de base de datos
            paciente_id: ID del paciente
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de reportes de laboratorio
        """
        try:
            filters = [
                DiagnosticReportORM.paciente_id == paciente_id,
                DiagnosticReportORM.categoria == "LAB"
            ]
            if documento_id:
                filters.append(DiagnosticReportORM.documento_id == documento_id)
            
            result = await session.execute(
                select(DiagnosticReportORM)
                .where(and_(*filters))
                .order_by(DiagnosticReportORM.fecha_estudio.desc())
            )
            orm_diagnostic_reports = result.scalars().all()
            
            diagnostic_reports = []
            for orm_diagnostic_report in orm_diagnostic_reports:
                pydantic_diagnostic_report = DiagnosticReportMapper.orm_to_pydantic(orm_diagnostic_report)
                diagnostic_reports.append(DiagnosticReportResponse(**pydantic_diagnostic_report.dict()))
            
            return diagnostic_reports
            
        except Exception as e:
            self._handle_database_error(e, "get_laboratory_reports_by_patient")
    
    async def get_imaging_reports(self, session: AsyncSession, paciente_id: int, 
                                documento_id: int = None) -> List[DiagnosticReportResponse]:
        """
        Obtener reportes de imagenología de un paciente
        
        Args:
            session: Sesión de base de datos
            paciente_id: ID del paciente
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de reportes de imagenología
        """
        try:
            filters = [
                DiagnosticReportORM.paciente_id == paciente_id,
                DiagnosticReportORM.categoria == "RAD"
            ]
            if documento_id:
                filters.append(DiagnosticReportORM.documento_id == documento_id)
            
            result = await session.execute(
                select(DiagnosticReportORM)
                .where(and_(*filters))
                .order_by(DiagnosticReportORM.fecha_estudio.desc())
            )
            orm_diagnostic_reports = result.scalars().all()
            
            diagnostic_reports = []
            for orm_diagnostic_report in orm_diagnostic_reports:
                pydantic_diagnostic_report = DiagnosticReportMapper.orm_to_pydantic(orm_diagnostic_report)
                diagnostic_reports.append(DiagnosticReportResponse(**pydantic_diagnostic_report.dict()))
            
            return diagnostic_reports
            
        except Exception as e:
            self._handle_database_error(e, "get_imaging_reports_by_patient")
    
    async def get_by_professional(self, session: AsyncSession, profesional_id: int, 
                                documento_id: int = None) -> List[DiagnosticReportResponse]:
        """
        Obtener reportes diagnósticos por profesional ejecutor
        
        Args:
            session: Sesión de base de datos
            profesional_id: ID del profesional
            documento_id: ID del documento (opcional)
            
        Returns:
            Lista de reportes del profesional
        """
        try:
            filters = [DiagnosticReportORM.profesional_id == profesional_id]
            if documento_id:
                filters.append(DiagnosticReportORM.documento_id == documento_id)
            
            result = await session.execute(
                select(DiagnosticReportORM)
                .where(and_(*filters))
                .order_by(DiagnosticReportORM.fecha_estudio.desc())
            )
            orm_diagnostic_reports = result.scalars().all()
            
            diagnostic_reports = []
            for orm_diagnostic_report in orm_diagnostic_reports:
                pydantic_diagnostic_report = DiagnosticReportMapper.orm_to_pydantic(orm_diagnostic_report)
                diagnostic_reports.append(DiagnosticReportResponse(**pydantic_diagnostic_report.dict()))
            
            return diagnostic_reports
            
        except Exception as e:
            self._handle_database_error(e, "get_diagnostic_reports_by_professional")


# Instancia global del servicio (singleton)
diagnostic_report_service = DiagnosticReportService()

# Exportaciones del módulo
__all__ = [
    "DiagnosticReportService",
    "diagnostic_report_service"
]