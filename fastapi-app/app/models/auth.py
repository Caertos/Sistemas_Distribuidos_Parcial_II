"""
Authentication Pydantic Models
Modelos Pydantic para validación de datos de autenticación y autorización
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from .base import ResourceBase


class UserType(str, Enum):
    """Tipos de usuario en el sistema FHIR"""
    PATIENT = "patient"
    PRACTITIONER = "practitioner"
    ADMIN = "admin"
    SYSTEM = "system"


class TokenType(str, Enum):
    """Tipos de tokens JWT"""
    ACCESS = "access"
    REFRESH = "refresh"


# Modelos de Request (Input)

class UserRegister(BaseModel):
    """Modelo para registro de nuevos usuarios"""
    username: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario único")
    email: EmailStr = Field(..., description="Email del usuario")
    full_name: str = Field(..., min_length=2, max_length=200, description="Nombre completo")
    password: str = Field(..., min_length=8, max_length=100, description="Contraseña")
    user_type: UserType = Field(UserType.PATIENT, description="Tipo de usuario")
    fhir_patient_id: Optional[str] = Field(None, description="ID del recurso Patient FHIR asociado")
    fhir_practitioner_id: Optional[str] = Field(None, description="ID del recurso Practitioner FHIR asociado")
    
    @validator('password')
    def validate_password(cls, v):
        """Validar fortaleza de contraseña"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('user_type')
    def validate_user_type_associations(cls, v, values):
        """Validar asociaciones FHIR según tipo de usuario"""
        if v == UserType.PATIENT and not values.get('fhir_patient_id'):
            # Nota: fhir_patient_id puede ser asignado después del registro
            pass
        elif v == UserType.PRACTITIONER and not values.get('fhir_practitioner_id'):
            # Nota: fhir_practitioner_id puede ser asignado después del registro
            pass
        return v


class UserLogin(BaseModel):
    """Modelo para login de usuarios"""
    username: str = Field(..., description="Nombre de usuario o email")
    password: str = Field(..., description="Contraseña")
    remember_me: bool = Field(False, description="Mantener sesión activa por más tiempo")


class UserUpdate(BaseModel):
    """Modelo para actualización de información de usuario"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    fhir_patient_id: Optional[str] = None
    fhir_practitioner_id: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class PasswordChange(BaseModel):
    """Modelo para cambio de contraseña"""
    current_password: str = Field(..., description="Contraseña actual")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")
    confirm_password: str = Field(..., description="Confirmación de nueva contraseña")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class RoleAssignment(BaseModel):
    """Modelo para asignación de roles"""
    user_id: str = Field(..., description="ID del usuario")
    role_names: List[str] = Field(..., description="Lista de nombres de roles a asignar")


# Modelos de Response (Output)

class UserProfile(BaseModel):
    """Perfil básico de usuario"""
    id: str
    username: str
    email: str
    full_name: str
    user_type: UserType
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    fhir_patient_id: Optional[str]
    fhir_practitioner_id: Optional[str]
    
    class Config:
        from_attributes = True


class UserWithRoles(UserProfile):
    """Usuario con información de roles"""
    roles: List['RoleInfo'] = []
    permissions: List[str] = []
    
    class Config:
        from_attributes = True


class RoleInfo(BaseModel):
    """Información básica de rol"""
    id: str
    name: str
    display_name: str
    description: Optional[str]
    is_active: bool
    fhir_scopes: Optional[List[str]] = None
    
    class Config:
        from_attributes = True


class RoleDetail(RoleInfo):
    """Información detallada de rol"""
    permissions: List['PermissionInfo'] = []
    user_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class PermissionInfo(BaseModel):
    """Información de permiso"""
    id: str
    name: str
    display_name: str
    description: Optional[str]
    category: str
    fhir_resource: Optional[str]
    fhir_action: Optional[str]
    
    class Config:
        from_attributes = True


class TokenPair(BaseModel):
    """Par de tokens de acceso y refresh"""
    access_token: str = Field(..., description="Token de acceso JWT")
    refresh_token: str = Field(..., description="Token de actualización")
    token_type: str = Field("bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Tiempo de expiración en segundos")


class AccessToken(BaseModel):
    """Token de acceso JWT"""
    access_token: str = Field(..., description="Token de acceso JWT")
    token_type: str = Field("bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Tiempo de expiración en segundos")


class TokenData(BaseModel):
    """Datos contenidos en el token JWT"""
    user_id: str
    username: str
    user_type: UserType
    roles: List[str] = []
    scopes: List[str] = []
    exp: int
    iat: int
    jti: str


class APIKeyCreate(BaseModel):
    """Modelo para creación de API Key"""
    name: str = Field(..., min_length=3, max_length=100, description="Nombre descriptivo")
    expires_at: Optional[datetime] = Field(None, description="Fecha de expiración opcional")
    scopes: Optional[List[str]] = Field(None, description="Scopes permitidos")
    allowed_ips: Optional[List[str]] = Field(None, description="IPs permitidas")
    rate_limit: Optional[int] = Field(None, ge=1, description="Límite de requests por minuto")


class APIKeyInfo(BaseModel):
    """Información de API Key (sin mostrar la key completa)"""
    id: str
    name: str
    key_prefix: str
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    usage_count: int
    rate_limit: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class APIKeyCreated(BaseModel):
    """API Key recién creada (incluye la key completa, solo se muestra una vez)"""
    id: str
    name: str
    api_key: str = Field(..., description="API Key completa - GUARDAR DE FORMA SEGURA")
    key_prefix: str
    expires_at: Optional[datetime]
    scopes: Optional[List[str]]


# Modelos para autenticación FHIR

class FHIRScope(BaseModel):
    """Scope FHIR según especificación SMART on FHIR"""
    resource_type: Optional[str] = Field(None, description="Tipo de recurso (Patient, Observation, etc.)")
    interaction: str = Field(..., description="Tipo de interacción (read, write, *, etc.)")
    context: str = Field(..., description="Contexto (user, patient, system)")
    
    def __str__(self):
        if self.resource_type:
            return f"{self.context}/{self.resource_type}.{self.interaction}"
        else:
            return f"{self.context}/*.{self.interaction}"


class FHIRTokenResponse(TokenPair):
    """Respuesta de token según especificación SMART on FHIR"""
    scope: str = Field(..., description="Scopes otorgados separados por espacios")
    patient: Optional[str] = Field(None, description="ID del paciente en contexto")
    encounter: Optional[str] = Field(None, description="ID del encuentro en contexto")
    
    @validator('scope')
    def validate_fhir_scopes(cls, v):
        """Validar que los scopes sigan el formato FHIR"""
        scopes = v.split()
        for scope in scopes:
            if not any(scope.startswith(prefix) for prefix in ['user/', 'patient/', 'system/']):
                raise ValueError(f'Invalid FHIR scope format: {scope}')
        return v


# Modelos de administración

class UserSearch(BaseModel):
    """Parámetros de búsqueda de usuarios"""
    username: Optional[str] = None
    email: Optional[str] = None
    user_type: Optional[UserType] = None
    is_active: Optional[bool] = None
    role_name: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)


class UserList(BaseModel):
    """Lista paginada de usuarios"""
    users: List[UserProfile]
    total: int
    page: int
    size: int
    pages: int


class RoleCreate(BaseModel):
    """Modelo para creación de roles"""
    name: str = Field(..., min_length=2, max_length=50, description="Nombre único del rol")
    display_name: str = Field(..., min_length=2, max_length=100, description="Nombre para mostrar")
    description: Optional[str] = Field(None, max_length=500)
    fhir_scopes: Optional[List[str]] = Field(None, description="Scopes FHIR permitidos")
    permission_names: Optional[List[str]] = Field(None, description="Nombres de permisos a asignar")


class PermissionCreate(BaseModel):
    """Modelo para creación de permisos"""
    name: str = Field(..., min_length=3, max_length=100, description="Nombre único del permiso")
    display_name: str = Field(..., min_length=3, max_length=150, description="Nombre para mostrar")
    description: Optional[str] = Field(None, max_length=500)
    category: str = Field("general", description="Categoría del permiso")
    fhir_resource: Optional[str] = Field(None, description="Recurso FHIR asociado")
    fhir_action: Optional[str] = Field(None, description="Acción FHIR asociada")


# Modelos de eventos de auditoría

class AuthEvent(BaseModel):
    """Evento de autenticación para auditoría"""
    user_id: Optional[str]
    username: Optional[str]
    event_type: str = Field(..., description="Tipo de evento: login, logout, failed_login, etc.")
    ip_address: Optional[str]
    user_agent: Optional[str]
    success: bool
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Modelos de configuración

class AuthConfig(BaseModel):
    """Configuración de autenticación"""
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    password_reset_expire_minutes: int = 60
    enable_email_verification: bool = True
    enable_two_factor: bool = False


# Hacer las referencias hacia adelante funcionales
UserWithRoles.model_rebuild()
RoleDetail.model_rebuild()