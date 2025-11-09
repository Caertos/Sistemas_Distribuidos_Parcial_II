"""
Authentication Package
Paquete de autenticación y autorización para la API FHIR
"""

from .jwt_utils import (
    JWTConfig,
    JWTManager,
    PasswordManager,
    FHIRScopeManager,
    APIKeyManager,
    InvalidTokenError,
    jwt_manager,
    password_manager,
    scope_manager,
    api_key_manager,
    create_access_token,
    create_refresh_token,
    verify_token,
    hash_password,
    verify_password,
    validate_fhir_scope
)

from .middleware import (
    AuthenticationError,
    AuthorizationError,
    get_current_user,
    get_current_active_user,
    get_current_superuser,
    require_roles,
    require_permissions,
    require_fhir_scope,
    require_resource_access,
    optional_auth,
    AuthMiddleware,
    CurrentUser,
    CurrentActiveUser,
    CurrentSuperUser,
    OptionalAuth,
    AdminRequired,
    PractitionerRequired,
    PatientRequired,
    PatientRead,
    PatientWrite,
    ObservationRead,
    ObservationWrite
)

__all__ = [
    # Clases principales
    "JWTConfig",
    "JWTManager", 
    "PasswordManager",
    "FHIRScopeManager",
    "APIKeyManager",
    
    # Excepciones
    "InvalidTokenError",
    "AuthenticationError",
    "AuthorizationError",
    
    # Instancias globales
    "jwt_manager",
    "password_manager", 
    "scope_manager",
    "api_key_manager",
    
    # Funciones de conveniencia
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "hash_password",
    "verify_password",
    "validate_fhir_scope",
    
    # Middleware y dependencies
    "get_current_user",
    "get_current_active_user",
    "get_current_superuser",
    "require_roles",
    "require_permissions",
    "require_fhir_scope",
    "require_resource_access",
    "optional_auth",
    "AuthMiddleware",
    
    # Aliases comunes
    "CurrentUser",
    "CurrentActiveUser",
    "CurrentSuperUser",
    "OptionalAuth",
    "AdminRequired",
    "PractitionerRequired",
    "PatientRequired",
    "PatientRead",
    "PatientWrite",
    "ObservationRead",
    "ObservationWrite"
]