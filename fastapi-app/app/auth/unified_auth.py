"""
Middleware de Autenticación Unificado
Maneja tanto tokens JWT estándar como tokens FHIR personalizados para compatibilidad
"""

import json
import base64
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import HTTPException, Header, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config.database import db_manager, get_db_session
from app.auth.middleware import get_current_user_from_token, security
from app.models.orm.auth import UserORM


async def verify_unified_token(
    request: Request,
    authorization: str = Header(None, alias="Authorization")
) -> Dict[str, Any]:
    """
    Middleware unificado que maneja tanto tokens JWT estándar como tokens FHIR personalizados
    Busca tokens en headers de autorización y cookies
    
    Args:
        request: Request de FastAPI
        authorization: Header de autorización
    
    Returns:
        Datos del token decodificado
    
    Raises:
        HTTPException: Si el token es inválido o falta
    """
    try:
        # Intentar obtener token desde header Authorization
        token_source = authorization
        
        # Si no hay header, buscar en cookies
        if not token_source:
            token_source = request.cookies.get('authToken')
            if token_source:
                token_source = f"Bearer {token_source}"
        
        if not token_source:
            raise HTTPException(status_code=401, detail="Token de autorización requerido")
        
        # Caso 1: Token FHIR personalizado (Bearer FHIR-...)
        if token_source.startswith("Bearer FHIR-"):
            token = token_source.replace("Bearer FHIR-", "")
            token_data = json.loads(base64.b64decode(token).decode())
            
            # Verificar expiración del token personalizado
            if token_data.get("expires") and token_data["expires"] < datetime.now().timestamp():
                raise HTTPException(status_code=401, detail="Token expirado")
            
            return token_data
        
        # Caso 2: Token JWT estándar (Bearer ...)
        elif token_source.startswith("Bearer "):
            # Usar el middleware estándar de FastAPI
            from fastapi.security import HTTPAuthorizationCredentials
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=token_source.replace("Bearer ", "")
            )
            
            # Intentar decodificar con el sistema JWT estándar
            user = await get_current_user_from_token(credentials, await get_db_session().__anext__())
            
            # Convertir usuario ORM a formato de token personalizado para compatibilidad
            return {
                "user_id": user.id,
                "username": user.username,
                "user_type": user.user_type,
                "full_name": user.full_name,
                "email": user.email,
                "fhir_patient_id": user.fhir_patient_id,
                "fhir_practitioner_id": user.fhir_practitioner_id,
                "expires": None  # Los JWT manejan su propia expiración
            }
        
        else:
            raise HTTPException(status_code=401, detail="Formato de token inválido")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Error de autenticación: {str(e)}")


async def verify_patient_token_unified(
    request: Request,
    authorization: str = Header(None, alias="Authorization")
) -> Dict[str, Any]:
    """
    Verificar token específicamente para pacientes (ambos formatos)
    
    Args:
        request: Request de FastAPI
        authorization: Header de autorización
    
    Returns:
        Datos del token si es de paciente
    
    Raises:
        HTTPException: Si no es token de paciente o es inválido
    """
    token_data = await verify_unified_token(request, authorization)
    
    if token_data.get("user_type") != "patient":
        raise HTTPException(status_code=403, detail="Acceso solo para pacientes")
    
    return token_data


async def verify_medic_token_unified(
    request: Request,
    authorization: str = Header(None, alias="Authorization")
) -> Dict[str, Any]:
    """
    Verificar token específicamente para médicos (ambos formatos)
    
    Args:
        request: Request de FastAPI
        authorization: Header de autorización
    
    Returns:
        Datos del token si es de médico
    
    Raises:
        HTTPException: Si no es token de médico o es inválido
    """
    token_data = await verify_unified_token(request, authorization)
    
    if token_data.get("user_type") not in ["practitioner", "medico"]:
        raise HTTPException(status_code=403, detail="Acceso solo para médicos")
    
    return token_data


async def verify_admin_token_unified(authorization: str = Header(None, alias="Authorization")) -> Dict[str, Any]:
    """
    Verificar token específicamente para administradores (ambos formatos)
    
    Args:
        authorization: Header de autorización
    
    Returns:
        Datos del token si es de admin
    
    Raises:
        HTTPException: Si no es token de admin o es inválido
    """
    token_data = await verify_unified_token(authorization)
    
    if token_data.get("user_type") not in ["admin", "administrador"]:
        raise HTTPException(status_code=403, detail="Acceso solo para administradores")
    
    return token_data


async def optional_unified_auth(authorization: str = Header(None, alias="Authorization")) -> Optional[Dict[str, Any]]:
    """
    Autenticación opcional que no falla si no hay token
    
    Args:
        authorization: Header de autorización opcional
    
    Returns:
        Datos del token o None si no hay token válido
    """
    try:
        if not authorization:
            return None
        
        return await verify_unified_token(authorization)
    except:
        return None


# Dependencias para usar en las rutas
PatientTokenRequired = Depends(verify_patient_token_unified)
MedicTokenRequired = Depends(verify_medic_token_unified)
AdminTokenRequired = Depends(verify_admin_token_unified)
UnifiedTokenRequired = Depends(verify_unified_token)
OptionalAuth = Depends(optional_unified_auth)