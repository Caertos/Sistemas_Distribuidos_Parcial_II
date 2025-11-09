"""
FastAPI Authentication Middleware and Dependencies
Middleware y dependencias para autenticación JWT en FastAPI
"""

from typing import Optional, List, Callable, Union
from datetime import datetime
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config.database import get_db_session
from app.models.orm.auth import UserORM, APIKeyORM
from app.models.auth import TokenData, UserType, UserWithRoles
from app.auth import (
    jwt_manager, 
    api_key_manager, 
    InvalidTokenError,
    validate_fhir_scope
)


# Esquema de seguridad HTTP Bearer
security = HTTPBearer(auto_error=False)


class AuthenticationError(HTTPException):
    """Excepción personalizada para errores de autenticación"""
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(HTTPException):
    """Excepción personalizada para errores de autorización"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> UserORM:
    """
    Dependency para obtener usuario actual desde token JWT
    
    Args:
        credentials: Credenciales HTTP Bearer
        db: Sesión de base de datos
    
    Returns:
        Usuario autenticado
    
    Raises:
        AuthenticationError: Si token inválido o usuario no encontrado
    """
    if not credentials:
        raise AuthenticationError("Authentication token required")
    
    token = credentials.credentials
    
    try:
        # Decodificar token JWT
        token_data = jwt_manager.decode_token(token)
        
        # Buscar usuario en base de datos
        stmt = select(UserORM).options(
            selectinload(UserORM.roles).selectinload(UserORM.roles.property.mapper.class_.permissions)
        ).where(UserORM.id == token_data.user_id)
        
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthenticationError("User not found")
        
        if not user.is_active:
            raise AuthenticationError("User account is inactive")
        
        if user.is_locked:
            raise AuthenticationError("User account is locked")
        
        return user
        
    except InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise AuthenticationError(f"Authentication failed: {str(e)}")


async def get_current_user_from_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
) -> Optional[UserORM]:
    """
    Dependency opcional para obtener usuario desde API Key
    
    Args:
        request: Request de FastAPI
        db: Sesión de base de datos
    
    Returns:
        Usuario autenticado o None si no hay API key
    """
    # Buscar API key en headers
    api_key = None
    
    # Header X-API-Key
    if "x-api-key" in request.headers:
        api_key = request.headers["x-api-key"]
    # Header Authorization con Bearer
    elif "authorization" in request.headers:
        auth_header = request.headers["authorization"]
        if auth_header.startswith("ApiKey "):
            api_key = auth_header[7:]  # Remover "ApiKey "
    
    if not api_key:
        return None
    
    try:
        # Buscar API key en base de datos
        stmt = select(APIKeyORM).options(
            selectinload(APIKeyORM.user).selectinload(UserORM.roles)
        ).where(APIKeyORM.is_active == True)
        
        result = await db.execute(stmt)
        api_keys = result.scalars().all()
        
        # Verificar contra todas las API keys activas
        for stored_key in api_keys:
            if api_key_manager.verify_api_key(api_key, stored_key.key_hash):
                # Verificar expiración
                if stored_key.is_expired:
                    continue
                
                # Actualizar contador de uso
                stored_key.usage_count += 1
                stored_key.last_used_at = datetime.utcnow()
                await db.commit()
                
                return stored_key.user
        
        return None
        
    except Exception:
        return None


async def get_current_user(
    jwt_user: Optional[UserORM] = Depends(get_current_user_from_token),
    api_user: Optional[UserORM] = Depends(get_current_user_from_api_key)
) -> UserORM:
    """
    Dependency que acepta autenticación JWT o API Key
    
    Args:
        jwt_user: Usuario desde JWT (puede fallar)
        api_user: Usuario desde API Key (opcional)
    
    Returns:
        Usuario autenticado
    
    Raises:
        AuthenticationError: Si no hay autenticación válida
    """
    user = jwt_user or api_user
    
    if not user:
        raise AuthenticationError("Valid authentication required (JWT token or API key)")
    
    return user


async def get_current_active_user(
    current_user: UserORM = Depends(get_current_user)
) -> UserORM:
    """
    Dependency para obtener usuario activo
    
    Args:
        current_user: Usuario actual
    
    Returns:
        Usuario activo
    
    Raises:
        AuthenticationError: Si usuario no está activo
    """
    if not current_user.is_active:
        raise AuthenticationError("User account is inactive")
    
    return current_user


async def get_current_superuser(
    current_user: UserORM = Depends(get_current_active_user)
) -> UserORM:
    """
    Dependency para obtener superusuario
    
    Args:
        current_user: Usuario actual
    
    Returns:
        Superusuario
    
    Raises:
        AuthorizationError: Si no es superusuario
    """
    if not current_user.is_superuser:
        raise AuthorizationError("Superuser access required")
    
    return current_user


def require_roles(allowed_roles: List[str]) -> Callable:
    """
    Decorator/dependency para requerir roles específicos
    
    Args:
        allowed_roles: Lista de roles permitidos
    
    Returns:
        Función dependency
    """
    async def check_roles(
        current_user: UserORM = Depends(get_current_active_user)
    ) -> UserORM:
        user_roles = [role.name for role in current_user.roles]
        
        # Superusuarios pasan todos los checks
        if current_user.is_superuser:
            return current_user
        
        # Verificar si tiene algún rol permitido
        if not any(role in user_roles for role in allowed_roles):
            raise AuthorizationError(
                f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        
        return current_user
    
    return check_roles


def require_permissions(required_permissions: List[str]) -> Callable:
    """
    Decorator/dependency para requerir permisos específicos
    
    Args:
        required_permissions: Lista de permisos requeridos
    
    Returns:
        Función dependency
    """
    async def check_permissions(
        current_user: UserORM = Depends(get_current_active_user)
    ) -> UserORM:
        # Superusuarios pasan todos los checks
        if current_user.is_superuser:
            return current_user
        
        # Verificar cada permiso requerido
        for permission in required_permissions:
            if not current_user.has_permission(permission):
                raise AuthorizationError(
                    f"Permission denied. Required: {permission}"
                )
        
        return current_user
    
    return check_permissions


def require_fhir_scope(required_scope: str) -> Callable:
    """
    Decorator/dependency para requerir scope FHIR específico
    
    Args:
        required_scope: Scope FHIR requerido (ej: "user/Patient.read")
    
    Returns:
        Función dependency
    """
    async def check_fhir_scope(
        current_user: UserORM = Depends(get_current_active_user),
        request: Request = None
    ) -> UserORM:
        # Superusuarios pasan todos los checks
        if current_user.is_superuser:
            return current_user
        
        # Obtener scopes del usuario desde roles
        user_scopes = []
        user_roles = [role.name for role in current_user.roles]
        
        for role in current_user.roles:
            if role.fhir_scopes:
                try:
                    import json
                    role_scopes = json.loads(role.fhir_scopes)
                    user_scopes.extend(role_scopes)
                except:
                    pass
        
        # Validar scope FHIR
        if not validate_fhir_scope(
            required_scope, 
            user_scopes, 
            UserType(current_user.user_type),
            user_roles
        ):
            raise AuthorizationError(
                f"FHIR scope denied. Required: {required_scope}"
            )
        
        return current_user
    
    return check_fhir_scope


def require_resource_access(resource_type: str, action: str = "read") -> Callable:
    """
    Decorator/dependency para requerir acceso a recurso FHIR específico
    
    Args:
        resource_type: Tipo de recurso FHIR (Patient, Observation, etc.)
        action: Acción requerida (read, write, create, update, delete)
    
    Returns:
        Función dependency
    """
    required_scope = f"user/{resource_type}.{action}"
    return require_fhir_scope(required_scope)


def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Optional[UserORM]:
    """
    Dependency para autenticación opcional
    
    Args:
        credentials: Credenciales HTTP Bearer opcionales
        db: Sesión de base de datos
    
    Returns:
        Usuario autenticado o None
    """
    if not credentials:
        return None
    
    try:
        # Intentar obtener usuario desde token
        token_data = jwt_manager.decode_token(credentials.credentials)
        
        # Buscar usuario
        stmt = select(UserORM).where(UserORM.id == token_data.user_id)
        result = db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user and user.is_active and not user.is_locked:
            return user
        
    except:
        pass
    
    return None


class AuthMiddleware:
    """Middleware personalizado para logging de autenticación"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Log intentos de autenticación
            auth_header = request.headers.get("authorization")
            if auth_header:
                # Aquí se puede agregar logging de auditoría
                pass
        
        await self.app(scope, receive, send)


# Aliases para compatibilidad
CurrentUser = Depends(get_current_user)
CurrentActiveUser = Depends(get_current_active_user)
CurrentSuperUser = Depends(get_current_superuser)
OptionalAuth = Depends(optional_auth)

# Shortcuts comunes
AdminRequired = require_roles(["admin"])
PractitionerRequired = require_roles(["practitioner", "admin"])
PatientRequired = require_roles(["patient", "practitioner", "admin"])

# Shortcuts FHIR comunes
PatientRead = require_resource_access("Patient", "read")
PatientWrite = require_resource_access("Patient", "write")
ObservationRead = require_resource_access("Observation", "read")
ObservationWrite = require_resource_access("Observation", "write")