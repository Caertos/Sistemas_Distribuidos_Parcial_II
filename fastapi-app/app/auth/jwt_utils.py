"""
JWT Authentication Utilities
Utilidades para manejo de tokens JWT, autenticación y autorización
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from jose import jwt, JWTError
from passlib.context import CryptContext
from passlib.hash import bcrypt
import hashlib
import base64

from app.models.auth import TokenData, UserType, TokenType, FHIRScope


class InvalidTokenError(Exception):
    """Excepción para tokens JWT inválidos"""
    pass


class JWTConfig:
    """Configuración JWT centralizada"""
    
    # Configuración de tokens
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
    ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    
    # Configuración de seguridad
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOCKOUT_DURATION_MINUTES: int = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))
    
    # Configuración FHIR
    FHIR_BASE_URL: str = os.getenv("FHIR_BASE_URL", "http://localhost:8000/fhir")
    ENABLE_FHIR_SCOPES: bool = os.getenv("ENABLE_FHIR_SCOPES", "true").lower() == "true"
    
    @classmethod
    def validate_config(cls) -> List[str]:
        """Valida la configuración JWT"""
        issues = []
        
        if len(cls.SECRET_KEY) < 32:
            issues.append("JWT_SECRET_KEY should be at least 32 characters long")
        
        if cls.ACCESS_TOKEN_EXPIRE_MINUTES < 5:
            issues.append("ACCESS_TOKEN_EXPIRE_MINUTES should be at least 5 minutes")
        
        if cls.REFRESH_TOKEN_EXPIRE_DAYS < 1:
            issues.append("REFRESH_TOKEN_EXPIRE_DAYS should be at least 1 day")
        
        return issues


class PasswordManager:
    """Gestor de contraseñas con hashing seguro"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def hash_password(self, password: str) -> str:
        """Genera hash de contraseña"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica contraseña contra hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Genera token seguro aleatorio"""
        return secrets.token_urlsafe(length)
    
    def hash_token(self, token: str) -> str:
        """Genera hash de token para almacenamiento seguro"""
        return hashlib.sha256(token.encode()).hexdigest()


class JWTManager:
    """Gestor de tokens JWT"""
    
    def __init__(self):
        self.config = JWTConfig()
        self.password_manager = PasswordManager()
    
    def create_access_token(
        self, 
        user_id: str,
        username: str,
        user_type: UserType,
        roles: List[str] = None,
        scopes: List[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Crea token de acceso JWT
        
        Args:
            user_id: ID del usuario
            username: Nombre de usuario
            user_type: Tipo de usuario
            roles: Lista de roles del usuario
            scopes: Lista de scopes/permisos
            expires_delta: Tiempo personalizado de expiración
        
        Returns:
            Token JWT como string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.config.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Datos del token
        token_data = {
            "sub": user_id,  # Subject (estándar JWT)
            "username": username,
            "user_type": user_type.value,
            "roles": roles or [],
            "scopes": scopes or [],
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(16),  # JWT ID único
            "type": TokenType.ACCESS.value
        }
        
        return jwt.encode(token_data, self.config.SECRET_KEY, algorithm=self.config.ALGORITHM)
    
    def create_refresh_token(
        self, 
        user_id: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Crea token de refresh
        
        Args:
            user_id: ID del usuario
            expires_delta: Tiempo personalizado de expiración
        
        Returns:
            Token de refresh como string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.config.REFRESH_TOKEN_EXPIRE_DAYS)
        
        token_data = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(16),
            "type": TokenType.REFRESH.value
        }
        
        return jwt.encode(token_data, self.config.SECRET_KEY, algorithm=self.config.ALGORITHM)
    
    def decode_token(self, token: str) -> TokenData:
        """
        Decodifica y valida token JWT
        
        Args:
            token: Token JWT a decodificar
        
        Returns:
            TokenData con información del token
        
        Raises:
            InvalidTokenError: Si el token es inválido
        """
        try:
            payload = jwt.decode(
                token, 
                self.config.SECRET_KEY, 
                algorithms=[self.config.ALGORITHM]
            )
            
            # Validar campos requeridos
            user_id = payload.get("sub")
            if not user_id:
                raise InvalidTokenError("Token missing user ID")
            
            # Para tokens de acceso, validar campos adicionales
            if payload.get("type") == TokenType.ACCESS.value:
                username = payload.get("username")
                user_type = payload.get("user_type")
                
                if not username or not user_type:
                    raise InvalidTokenError("Access token missing required fields")
                
                return TokenData(
                    user_id=user_id,
                    username=username,
                    user_type=UserType(user_type),
                    roles=payload.get("roles", []),
                    scopes=payload.get("scopes", []),
                    exp=payload.get("exp"),
                    iat=payload.get("iat"),
                    jti=payload.get("jti")
                )
            
            # Para tokens de refresh, solo necesitamos el user_id
            return TokenData(
                user_id=user_id,
                username="",  # No disponible en refresh token
                user_type=UserType.SYSTEM,  # Placeholder
                exp=payload.get("exp"),
                iat=payload.get("iat"),
                jti=payload.get("jti")
            )
            
        except JWTError as e:
            if "expired" in str(e).lower():
                raise InvalidTokenError("Token has expired")
            raise InvalidTokenError(f"Token decode error: {str(e)}")
    
    def is_token_expired(self, token: str) -> bool:
        """
        Verifica si un token ha expirado sin validar la signature
        
        Args:
            token: Token JWT a verificar
        
        Returns:
            True si está expirado, False en caso contrario
        """
        try:
            # Decodificar sin verificar signature
            payload = jwt.decode(
                token, 
                options={"verify_signature": False}
            )
            exp = payload.get("exp")
            if exp:
                return datetime.utcnow().timestamp() > exp
            return True
        except:
            return True
    
    def extract_token_from_header(self, authorization: str) -> Optional[str]:
        """
        Extrae token de header Authorization
        
        Args:
            authorization: Header Authorization completo
        
        Returns:
            Token extraído o None si formato inválido
        """
        if not authorization:
            return None
        
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        return parts[1]


class FHIRScopeManager:
    """Gestor de scopes FHIR según especificación SMART on FHIR"""
    
    # Recursos FHIR soportados
    SUPPORTED_RESOURCES = [
        "Patient", "Practitioner", "Observation", 
        "Condition", "MedicationRequest", "DiagnosticReport"
    ]
    
    # Interacciones FHIR soportadas
    SUPPORTED_INTERACTIONS = [
        "read", "write", "create", "update", "delete", "search", "*"
    ]
    
    # Contextos FHIR soportados
    SUPPORTED_CONTEXTS = ["user", "patient", "system"]
    
    @classmethod
    def parse_scope(cls, scope_string: str) -> List[FHIRScope]:
        """
        Parsea string de scopes FHIR
        
        Args:
            scope_string: String con scopes separados por espacios
        
        Returns:
            Lista de objetos FHIRScope
        """
        scopes = []
        for scope in scope_string.split():
            try:
                parts = scope.split("/")
                if len(parts) != 2:
                    continue
                
                context = parts[0]
                resource_interaction = parts[1]
                
                if "." in resource_interaction:
                    resource_type, interaction = resource_interaction.split(".", 1)
                    if resource_type == "*":
                        resource_type = None
                else:
                    continue
                
                # Validar componentes
                if context not in cls.SUPPORTED_CONTEXTS:
                    continue
                
                if interaction not in cls.SUPPORTED_INTERACTIONS:
                    continue
                
                if resource_type and resource_type not in cls.SUPPORTED_RESOURCES:
                    continue
                
                scopes.append(FHIRScope(
                    resource_type=resource_type,
                    interaction=interaction,
                    context=context
                ))
                
            except Exception:
                # Ignorar scopes mal formados
                continue
        
        return scopes
    
    @classmethod
    def validate_scope_access(
        cls, 
        required_scope: str, 
        user_scopes: List[str],
        user_type: UserType,
        user_roles: List[str] = None
    ) -> bool:
        """
        Valida si el usuario tiene acceso a un scope específico
        
        Args:
            required_scope: Scope requerido (ej: "user/Patient.read")
            user_scopes: Scopes del usuario
            user_type: Tipo de usuario
            user_roles: Roles del usuario
        
        Returns:
            True si tiene acceso, False en caso contrario
        """
        # Administradores tienen acceso total
        if user_roles and "admin" in user_roles:
            return True
        
        # Verificar scopes exactos
        if required_scope in user_scopes:
            return True
        
        # Verificar scopes con wildcard
        required_parts = required_scope.split("/")
        if len(required_parts) != 2:
            return False
        
        context, resource_interaction = required_parts
        
        # Verificar wildcards de contexto
        wildcard_scopes = [
            f"{context}/*.*",  # Acceso total al contexto
            f"system/*.*"      # Acceso de sistema
        ]
        
        for wildcard in wildcard_scopes:
            if wildcard in user_scopes:
                return True
        
        # Verificar wildcards de recurso
        if "." in resource_interaction:
            resource, interaction = resource_interaction.split(".", 1)
            resource_wildcard = f"{context}/{resource}.*"
            if resource_wildcard in user_scopes:
                return True
        
        return False
    
    @classmethod
    def get_default_scopes_for_user_type(cls, user_type: UserType) -> List[str]:
        """
        Obtiene scopes por defecto según tipo de usuario
        
        Args:
            user_type: Tipo de usuario
        
        Returns:
            Lista de scopes por defecto
        """
        if user_type == UserType.ADMIN:
            return ["user/*.*", "system/*.*"]
        
        elif user_type == UserType.PRACTITIONER:
            return [
                "user/Patient.read",
                "user/Patient.write", 
                "user/Observation.*",
                "user/Condition.*",
                "user/MedicationRequest.*",
                "user/DiagnosticReport.*"
            ]
        
        elif user_type == UserType.PATIENT:
            return [
                "user/Patient.read",
                "user/Observation.read",
                "user/Condition.read", 
                "user/MedicationRequest.read",
                "user/DiagnosticReport.read"
            ]
        
        elif user_type == UserType.SYSTEM:
            return ["system/*.*"]
        
        return []


class APIKeyManager:
    """Gestor de API Keys para autenticación de sistemas"""
    
    def __init__(self):
        self.password_manager = PasswordManager()
    
    def generate_api_key(self, prefix: str = "fhir") -> tuple[str, str, str]:
        """
        Genera nueva API key
        
        Args:
            prefix: Prefijo para la key
        
        Returns:
            Tuple con (api_key_completa, hash, prefijo_visible)
        """
        # Generar key aleatoria
        key_part = self.password_manager.generate_secure_token(32)
        
        # Construir API key completa
        api_key = f"{prefix}_{key_part}"
        
        # Generar hash para almacenamiento
        key_hash = self.password_manager.hash_token(api_key)
        
        # Prefijo visible para identificación
        visible_prefix = f"{prefix}_{key_part[:8]}..."
        
        return api_key, key_hash, visible_prefix
    
    def verify_api_key(self, provided_key: str, stored_hash: str) -> bool:
        """
        Verifica API key contra hash almacenado
        
        Args:
            provided_key: API key proporcionada
            stored_hash: Hash almacenado en BD
        
        Returns:
            True si la key es válida
        """
        calculated_hash = self.password_manager.hash_token(provided_key)
        return calculated_hash == stored_hash


# Instancias globales
jwt_manager = JWTManager()
password_manager = PasswordManager()
scope_manager = FHIRScopeManager()
api_key_manager = APIKeyManager()


# Funciones de conveniencia
def create_access_token(user_data: Dict[str, Any]) -> str:
    """Crear token de acceso con datos de usuario"""
    return jwt_manager.create_access_token(
        user_id=user_data["id"],
        username=user_data["username"],
        user_type=UserType(user_data["user_type"]),
        roles=user_data.get("roles", []),
        scopes=user_data.get("scopes", [])
    )


def create_refresh_token(user_id: str) -> str:
    """Crear token de refresh"""
    return jwt_manager.create_refresh_token(user_id)


def verify_token(token: str) -> TokenData:
    """Verificar y decodificar token"""
    return jwt_manager.decode_token(token)


def hash_password(password: str) -> str:
    """Hash de contraseña"""
    return password_manager.hash_password(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verificar contraseña"""
    return password_manager.verify_password(password, hashed)


def validate_fhir_scope(required_scope: str, user_scopes: List[str], user_type: UserType, user_roles: List[str] = None) -> bool:
    """Validar scope FHIR"""
    return scope_manager.validate_scope_access(required_scope, user_scopes, user_type, user_roles)