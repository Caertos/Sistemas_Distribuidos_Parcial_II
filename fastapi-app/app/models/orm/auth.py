"""
Authentication Models - SQLAlchemy ORM
Modelos para autenticación, usuarios, roles y permisos del sistema FHIR
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timedelta
from typing import Optional, List

from .base import (
    Base, 
    UUIDMixin, 
    AuditMixin, 
    DistributedModel,
    get_table_comment
)


# Tabla de asociación many-to-many para User-Role
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
    Column('granted_at', DateTime(timezone=True), server_default=func.now()),
    Column('granted_by', UUID(as_uuid=True), ForeignKey('users.id')),
    schema='public'
)

# Tabla de asociación many-to-many para Role-Permission
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id'), primary_key=True),
    Column('granted_at', DateTime(timezone=True), server_default=func.now()),
    schema='public'
)


class UserORM(Base, DistributedModel, UUIDMixin, AuditMixin):
    """
    Modelo de Usuario del Sistema FHIR
    Usuarios que pueden acceder a los recursos FHIR con diferentes niveles de autorización
    """
    __tablename__ = 'users'
    __table_args__ = (
        # Índices para búsquedas comunes
        {'schema': 'public'},
        
        # Comentario de tabla
        {"comment": get_table_comment("User", is_distributed=True)}
    )
    
    # Información básica del usuario
    username = Column(
        String(50), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="Nombre de usuario único para login"
    )
    
    email = Column(
        String(255), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="Email único del usuario"
    )
    
    full_name = Column(
        String(200), 
        nullable=False,
        comment="Nombre completo del usuario"
    )
    
    # Credenciales de autenticación
    hashed_password = Column(
        String(255), 
        nullable=False,
        comment="Hash de la contraseña del usuario"
    )
    
    # Estado del usuario
    is_active = Column(
        Boolean, 
        default=True, 
        nullable=False,
        comment="Indica si el usuario está activo"
    )
    
    is_verified = Column(
        Boolean, 
        default=False, 
        nullable=False,
        comment="Indica si el email del usuario está verificado"
    )
    
    is_superuser = Column(
        Boolean, 
        default=False, 
        nullable=False,
        comment="Indica si el usuario es superadministrador"
    )
    
    # Información de sesión
    last_login = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha y hora del último login"
    )
    
    failed_login_attempts = Column(
        Integer, 
        default=0,
        comment="Número de intentos fallidos de login"
    )
    
    locked_until = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha hasta cuando la cuenta está bloqueada"
    )
    
    # Asociación con recursos FHIR
    fhir_patient_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID del recurso Patient FHIR asociado (si aplica)"
    )
    
    fhir_practitioner_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID del recurso Practitioner FHIR asociado (si aplica)"
    )
    
    # Metadatos adicionales
    user_type = Column(
        String(20),
        nullable=False,
        default='patient',
        comment="Tipo de usuario: patient, practitioner, admin, system"
    )
    
    preferences = Column(
        Text,
        nullable=True,
        comment="Preferencias del usuario en formato JSON"
    )
    
    # Relaciones
    roles = relationship(
        "RoleORM", 
        secondary=user_roles, 
        back_populates="users",
        lazy="selectin"
    )
    
    refresh_tokens = relationship(
        "RefreshTokenORM", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}', type='{self.user_type}')>"
    
    @property
    def is_locked(self) -> bool:
        """Verifica si la cuenta está bloqueada"""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    def has_permission(self, permission_name: str) -> bool:
        """Verifica si el usuario tiene un permiso específico"""
        if self.is_superuser:
            return True
        
        for role in self.roles:
            if role.has_permission(permission_name):
                return True
        return False
    
    def has_role(self, role_name: str) -> bool:
        """Verifica si el usuario tiene un rol específico"""
        return any(role.name == role_name for role in self.roles)


class RoleORM(Base, UUIDMixin, AuditMixin):
    """
    Modelo de Roles del Sistema
    Define roles que pueden ser asignados a usuarios (admin, practitioner, patient, etc.)
    """
    __tablename__ = 'roles'
    __table_args__ = (
        {'schema': 'public'},
        {"comment": get_table_comment("Role", is_distributed=False)}
    )
    
    name = Column(
        String(50), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="Nombre único del rol"
    )
    
    display_name = Column(
        String(100), 
        nullable=False,
        comment="Nombre legible del rol para mostrar en UI"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Descripción detallada del rol y sus responsabilidades"
    )
    
    is_active = Column(
        Boolean, 
        default=True, 
        nullable=False,
        comment="Indica si el rol está activo"
    )
    
    is_system = Column(
        Boolean, 
        default=False, 
        nullable=False,
        comment="Indica si es un rol del sistema (no editable)"
    )
    
    # Configuración FHIR específica
    fhir_scopes = Column(
        Text,
        nullable=True,
        comment="Scopes FHIR permitidos para este rol (JSON array)"
    )
    
    resource_permissions = Column(
        Text,
        nullable=True,
        comment="Permisos específicos de recursos FHIR (JSON)"
    )
    
    # Relaciones
    users = relationship(
        "UserORM", 
        secondary=user_roles, 
        back_populates="roles"
    )
    
    permissions = relationship(
        "PermissionORM", 
        secondary=role_permissions, 
        back_populates="roles",
        lazy="selectin"
    )
    
    def __repr__(self):
        return f"<Role(name='{self.name}', display_name='{self.display_name}')>"
    
    def has_permission(self, permission_name: str) -> bool:
        """Verifica si el rol tiene un permiso específico"""
        return any(perm.name == permission_name for perm in self.permissions)


class PermissionORM(Base, UUIDMixin, AuditMixin):
    """
    Modelo de Permisos del Sistema
    Define permisos granulares que pueden ser asignados a roles
    """
    __tablename__ = 'permissions'
    __table_args__ = (
        {'schema': 'public'},
        {"comment": get_table_comment("Permission", is_distributed=False)}
    )
    
    name = Column(
        String(100), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="Nombre único del permiso (ej: fhir:patient:read)"
    )
    
    display_name = Column(
        String(150), 
        nullable=False,
        comment="Nombre legible del permiso"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Descripción detallada del permiso"
    )
    
    category = Column(
        String(50), 
        nullable=False,
        default='general',
        comment="Categoría del permiso (fhir, system, admin, etc.)"
    )
    
    is_active = Column(
        Boolean, 
        default=True, 
        nullable=False,
        comment="Indica si el permiso está activo"
    )
    
    # Configuración FHIR específica
    fhir_resource = Column(
        String(50),
        nullable=True,
        comment="Tipo de recurso FHIR al que aplica (Patient, Observation, etc.)"
    )
    
    fhir_action = Column(
        String(20),
        nullable=True,
        comment="Acción FHIR permitida (read, write, create, update, delete, search)"
    )
    
    # Relaciones
    roles = relationship(
        "RoleORM", 
        secondary=role_permissions, 
        back_populates="permissions"
    )
    
    def __repr__(self):
        return f"<Permission(name='{self.name}', category='{self.category}')>"


class RefreshTokenORM(Base, UUIDMixin):
    """
    Modelo de Refresh Tokens
    Almacena tokens de actualización para renovar access tokens
    """
    __tablename__ = 'refresh_tokens'
    __table_args__ = (
        {'schema': 'public'},
        {"comment": get_table_comment("RefreshToken", is_distributed=True)}
    )
    
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'), 
        nullable=False,
        index=True,
        comment="ID del usuario propietario del token"
    )
    
    token_hash = Column(
        String(255), 
        nullable=False, 
        unique=True,
        index=True,
        comment="Hash del refresh token"
    )
    
    expires_at = Column(
        DateTime(timezone=True), 
        nullable=False,
        index=True,
        comment="Fecha de expiración del token"
    )
    
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False,
        comment="Fecha de creación del token"
    )
    
    is_revoked = Column(
        Boolean, 
        default=False, 
        nullable=False,
        comment="Indica si el token ha sido revocado"
    )
    
    client_info = Column(
        Text,
        nullable=True,
        comment="Información del client/navegador (User-Agent, IP, etc.)"
    )
    
    # Relaciones
    user = relationship("UserORM", back_populates="refresh_tokens")
    
    def __repr__(self):
        return f"<RefreshToken(user_id='{self.user_id}', expires_at='{self.expires_at}')>"
    
    @property
    def is_expired(self) -> bool:
        """Verifica si el token ha expirado"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Verifica si el token es válido (no expirado ni revocado)"""
        return not self.is_expired and not self.is_revoked


class APIKeyORM(Base, UUIDMixin, AuditMixin):
    """
    Modelo de API Keys
    Para autenticación de sistemas y aplicaciones externas
    """
    __tablename__ = 'api_keys'
    __table_args__ = (
        {'schema': 'public'},
        {"comment": get_table_comment("APIKey", is_distributed=True)}
    )
    
    name = Column(
        String(100), 
        nullable=False,
        comment="Nombre descriptivo de la API key"
    )
    
    key_hash = Column(
        String(255), 
        nullable=False, 
        unique=True,
        index=True,
        comment="Hash de la API key"
    )
    
    key_prefix = Column(
        String(20), 
        nullable=False,
        index=True,
        comment="Prefijo visible de la API key (para identificación)"
    )
    
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'), 
        nullable=False,
        comment="ID del usuario propietario de la API key"
    )
    
    is_active = Column(
        Boolean, 
        default=True, 
        nullable=False,
        comment="Indica si la API key está activa"
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha de expiración opcional"
    )
    
    last_used_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha del último uso"
    )
    
    usage_count = Column(
        Integer, 
        default=0,
        comment="Contador de usos de la API key"
    )
    
    # Configuración de permisos
    allowed_ips = Column(
        Text,
        nullable=True,
        comment="IPs permitidas (JSON array)"
    )
    
    rate_limit = Column(
        Integer,
        nullable=True,
        comment="Límite de requests por minuto"
    )
    
    scopes = Column(
        Text,
        nullable=True,
        comment="Scopes permitidos para esta API key (JSON array)"
    )
    
    # Relaciones
    user = relationship("UserORM")
    
    def __repr__(self):
        return f"<APIKey(name='{self.name}', prefix='{self.key_prefix}')>"
    
    @property
    def is_expired(self) -> bool:
        """Verifica si la API key ha expirado"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Verifica si la API key es válida"""
        return self.is_active and not self.is_expired


# Función para crear roles por defecto
def create_default_roles():
    """
    Crea los roles por defecto del sistema FHIR
    """
    default_roles = [
        {
            "name": "admin",
            "display_name": "Administrator",
            "description": "Full system administrator with all permissions",
            "is_system": True,
            "fhir_scopes": '["user/*.*", "system/*.*"]'
        },
        {
            "name": "practitioner",
            "display_name": "Healthcare Practitioner", 
            "description": "Healthcare professional with access to patient data",
            "is_system": True,
            "fhir_scopes": '["user/Patient.read", "user/Patient.write", "user/Observation.*", "user/Condition.*", "user/MedicationRequest.*", "user/DiagnosticReport.*"]'
        },
        {
            "name": "patient",
            "display_name": "Patient",
            "description": "Patient with access to own medical data",
            "is_system": True,
            "fhir_scopes": '["user/Patient.read", "user/Observation.read", "user/Condition.read", "user/MedicationRequest.read", "user/DiagnosticReport.read"]'
        },
        {
            "name": "system",
            "display_name": "System Service",
            "description": "System-to-system integration service",
            "is_system": True,
            "fhir_scopes": '["system/*.*"]'
        },
        {
            "name": "readonly",
            "display_name": "Read Only User",
            "description": "Read-only access to FHIR resources",
            "is_system": True,
            "fhir_scopes": '["user/*.read"]'
        }
    ]
    
    return default_roles


# Función para crear permisos por defecto
def create_default_permissions():
    """
    Crea los permisos por defecto basados en recursos FHIR
    """
    fhir_resources = ["Patient", "Practitioner", "Observation", "Condition", "MedicationRequest", "DiagnosticReport"]
    fhir_actions = ["read", "write", "create", "update", "delete", "search"]
    
    permissions = []
    
    # Permisos FHIR por recurso y acción
    for resource in fhir_resources:
        for action in fhir_actions:
            permissions.append({
                "name": f"fhir:{resource.lower()}:{action}",
                "display_name": f"{action.title()} {resource}",
                "description": f"Permission to {action} {resource} resources",
                "category": "fhir",
                "fhir_resource": resource,
                "fhir_action": action
            })
    
    # Permisos de sistema
    system_permissions = [
        {
            "name": "system:admin",
            "display_name": "System Administration",
            "description": "Full system administration capabilities",
            "category": "system"
        },
        {
            "name": "system:user_management",
            "display_name": "User Management",
            "description": "Manage users, roles, and permissions",
            "category": "system"
        },
        {
            "name": "system:api_keys",
            "display_name": "API Key Management",
            "description": "Manage API keys and system access",
            "category": "system"
        },
        {
            "name": "system:audit",
            "display_name": "Audit Logs",
            "description": "View and manage audit logs",
            "category": "system"
        }
    ]
    
    permissions.extend(system_permissions)
    return permissions