"""
Base Service Classes - Servicios base para operaciones CRUD de recursos FHIR
Incluye manejo de errores, validaciones y transformaciones
"""

from typing import Optional, List, Dict, Any, Generic, TypeVar, Type, Union
from abc import ABC, abstractmethod
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import BaseModel, ValidationError

from app.models.orm import Base
from app.models.orm.mappers import MapperFactory


# Type variables para genericidad
PydanticModel = TypeVar('PydanticModel', bound=BaseModel)
ORMModel = TypeVar('ORMModel', bound=Base)
CreateModel = TypeVar('CreateModel', bound=BaseModel)
UpdateModel = TypeVar('UpdateModel', bound=BaseModel)
SearchModel = TypeVar('SearchModel', bound=BaseModel)


class ServiceException(Exception):
    """Excepción base para servicios"""
    def __init__(self, message: str, code: str = "SERVICE_ERROR", details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ResourceNotFoundException(ServiceException):
    """Excepción cuando un recurso no se encuentra"""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} with ID {resource_id} not found",
            code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class ValidationException(ServiceException):
    """Excepción de validación"""
    def __init__(self, message: str, validation_errors: List[Dict] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"validation_errors": validation_errors or []}
        )


class DatabaseException(ServiceException):
    """Excepción de base de datos"""
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            details={"original_error": str(original_error) if original_error else None}
        )


class BaseService(Generic[PydanticModel, ORMModel, CreateModel, UpdateModel], ABC):
    """
    Servicio base abstracto para operaciones CRUD de recursos FHIR
    
    Proporciona funcionalidad común para todos los servicios de recursos
    """
    
    def __init__(self, 
                 pydantic_model: Type[PydanticModel],
                 orm_model: Type[ORMModel],
                 create_model: Type[CreateModel],
                 update_model: Type[UpdateModel],
                 resource_name: str):
        self.pydantic_model = pydantic_model
        self.orm_model = orm_model
        self.create_model = create_model
        self.update_model = update_model
        self.resource_name = resource_name
        self.logger = logging.getLogger(f"service.{resource_name.lower()}")
        
        # Obtener mapper para transformaciones
        self.mapper = MapperFactory.get_mapper(resource_name)
    
    @abstractmethod
    async def create(self, session: AsyncSession, resource: CreateModel, 
                    documento_id: int, **kwargs) -> PydanticModel:
        """Crear un nuevo recurso"""
        pass
    
    @abstractmethod
    async def get_by_id(self, session: AsyncSession, resource_id: str, 
                       documento_id: int = None) -> Optional[PydanticModel]:
        """Obtener recurso por ID"""
        pass
    
    @abstractmethod
    async def update(self, session: AsyncSession, resource_id: str, 
                    resource: UpdateModel, documento_id: int = None) -> PydanticModel:
        """Actualizar recurso existente"""
        pass
    
    @abstractmethod
    async def delete(self, session: AsyncSession, resource_id: str, 
                    documento_id: int = None) -> bool:
        """Eliminar recurso"""
        pass
    
    @abstractmethod
    async def search(self, session: AsyncSession, search_params: SearchModel) -> Dict[str, Any]:
        """Buscar recursos con paginación"""
        pass
    
    def _handle_database_error(self, error: Exception, operation: str) -> None:
        """
        Maneja errores de base de datos y los convierte a excepciones de servicio
        
        Args:
            error: Excepción original
            operation: Operación que se estaba realizando
        """
        self.logger.error(f"Database error in {operation}: {str(error)}")
        
        if isinstance(error, IntegrityError):
            raise DatabaseException(
                f"Integrity constraint violation during {operation}",
                error
            )
        elif isinstance(error, SQLAlchemyError):
            raise DatabaseException(
                f"Database error during {operation}: {str(error)}",
                error
            )
        else:
            raise DatabaseException(
                f"Unexpected error during {operation}",
                error
            )
    
    def _handle_validation_error(self, error: ValidationError, operation: str) -> None:
        """
        Maneja errores de validación de Pydantic
        
        Args:
            error: Error de validación de Pydantic
            operation: Operación que se estaba realizando
        """
        self.logger.error(f"Validation error in {operation}: {str(error)}")
        
        validation_errors = []
        for err in error.errors():
            validation_errors.append({
                "field": ".".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
                "type": err["type"]
            })
        
        raise ValidationException(
            f"Validation failed during {operation}",
            validation_errors
        )
    
    async def _get_next_id(self, session: AsyncSession, documento_id: int) -> int:
        """
        Obtiene el siguiente ID disponible para un recurso en un documento
        
        Args:
            session: Sesión de base de datos
            documento_id: ID del documento
            
        Returns:
            Siguiente ID disponible
        """
        try:
            # Obtener el ID máximo actual
            id_field = getattr(self.orm_model, f"{self.resource_name.lower()}_id")
            result = await session.execute(
                select(func.coalesce(func.max(id_field), 0))
                .where(self.orm_model.documento_id == documento_id)
            )
            max_id = result.scalar()
            return max_id + 1
        except Exception as e:
            self.logger.error(f"Error getting next ID: {str(e)}")
            return 1
    
    def _create_search_response(self, resources: List[PydanticModel], 
                               total: int, page: int, size: int) -> Dict[str, Any]:
        """
        Crea respuesta paginada para búsquedas
        
        Args:
            resources: Lista de recursos encontrados
            total: Total de recursos disponibles
            page: Página actual
            size: Tamaño de página
            
        Returns:
            Respuesta paginada estructurada
        """
        total_pages = (total + size - 1) // size
        
        return {
            "resources": resources,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "resource_type": self.resource_name,
            "count": len(resources)
        }
    
    async def count_all(self, session: AsyncSession, documento_id: int = None) -> int:
        """
        Cuenta el total de recursos
        
        Args:
            session: Sesión de base de datos
            documento_id: ID del documento (opcional para filtrar)
            
        Returns:
            Número total de recursos
        """
        try:
            query = select(func.count()).select_from(self.orm_model)
            
            if documento_id is not None:
                query = query.where(self.orm_model.documento_id == documento_id)
            
            result = await session.execute(query)
            return result.scalar()
        except Exception as e:
            self._handle_database_error(e, "count_all")
    
    async def exists(self, session: AsyncSession, resource_id: str, 
                    documento_id: int = None) -> bool:
        """
        Verifica si un recurso existe
        
        Args:
            session: Sesión de base de datos
            resource_id: ID del recurso
            documento_id: ID del documento (opcional)
            
        Returns:
            True si el recurso existe
        """
        try:
            resource = await self.get_by_id(session, resource_id, documento_id)
            return resource is not None
        except ResourceNotFoundException:
            return False
        except Exception as e:
            self._handle_database_error(e, "exists")


class DistributedService(BaseService[PydanticModel, ORMModel, CreateModel, UpdateModel]):
    """
    Servicio base para recursos distribuidos por documento_id
    
    Extiende BaseService con funcionalidad específica para tablas distribuidas
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._validate_distributed_model()
    
    def _validate_distributed_model(self):
        """Valida que el modelo ORM tenga documento_id"""
        if not hasattr(self.orm_model, 'documento_id'):
            raise ValueError(f"Model {self.orm_model.__name__} must have documento_id field for distributed service")
    
    async def get_by_documento_id(self, session: AsyncSession, documento_id: int) -> List[PydanticModel]:
        """
        Obtiene todos los recursos de un documento específico
        
        Args:
            session: Sesión de base de datos
            documento_id: ID del documento
            
        Returns:
            Lista de recursos del documento
        """
        try:
            result = await session.execute(
                select(self.orm_model)
                .where(self.orm_model.documento_id == documento_id)
                .order_by(self.orm_model.created_at.desc())
            )
            orm_resources = result.scalars().all()
            
            # Convertir a modelos Pydantic
            pydantic_resources = []
            for orm_resource in orm_resources:
                if self.mapper:
                    pydantic_resource = self.mapper.orm_to_pydantic(orm_resource)
                    pydantic_resources.append(pydantic_resource)
            
            return pydantic_resources
        except Exception as e:
            self._handle_database_error(e, "get_by_documento_id")
    
    async def count_by_documento_id(self, session: AsyncSession, documento_id: int) -> int:
        """
        Cuenta recursos por documento_id
        
        Args:
            session: Sesión de base de datos
            documento_id: ID del documento
            
        Returns:
            Número de recursos en el documento
        """
        try:
            result = await session.execute(
                select(func.count())
                .select_from(self.orm_model)
                .where(self.orm_model.documento_id == documento_id)
            )
            return result.scalar()
        except Exception as e:
            self._handle_database_error(e, "count_by_documento_id")


class ReferenceService(BaseService[PydanticModel, ORMModel, CreateModel, UpdateModel]):
    """
    Servicio base para recursos de referencia (replicados)
    
    Extiende BaseService con funcionalidad específica para tablas de referencia
    """
    
    async def get_all(self, session: AsyncSession, limit: int = 100, 
                     offset: int = 0) -> List[PydanticModel]:
        """
        Obtiene todos los recursos de referencia con paginación
        
        Args:
            session: Sesión de base de datos
            limit: Límite de resultados
            offset: Offset para paginación
            
        Returns:
            Lista de recursos de referencia
        """
        try:
            result = await session.execute(
                select(self.orm_model)
                .order_by(self.orm_model.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            orm_resources = result.scalars().all()
            
            # Convertir a modelos Pydantic
            pydantic_resources = []
            for orm_resource in orm_resources:
                if self.mapper:
                    pydantic_resource = self.mapper.orm_to_pydantic(orm_resource)
                    pydantic_resources.append(pydantic_resource)
            
            return pydantic_resources
        except Exception as e:
            self._handle_database_error(e, "get_all")


# Utilidades para servicios

class ServiceRegistry:
    """Registro de servicios para inyección de dependencias"""
    
    _services: Dict[str, BaseService] = {}
    
    @classmethod
    def register(cls, resource_type: str, service: BaseService):
        """Registra un servicio"""
        cls._services[resource_type] = service
    
    @classmethod
    def get(cls, resource_type: str) -> Optional[BaseService]:
        """Obtiene un servicio registrado"""
        return cls._services.get(resource_type)
    
    @classmethod
    def get_all_services(cls) -> Dict[str, BaseService]:
        """Obtiene todos los servicios registrados"""
        return cls._services.copy()


# Exportaciones del módulo
__all__ = [
    "ServiceException",
    "ResourceNotFoundException", 
    "ValidationException",
    "DatabaseException",
    "BaseService",
    "DistributedService",
    "ReferenceService",
    "ServiceRegistry"
]