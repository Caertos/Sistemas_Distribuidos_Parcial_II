"""
Simplified Authentication Service
Servicio de autenticación simplificado para login/logout
"""

import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import secrets
import base64
import json

from app.models.orm.auth_simple import UserORM
from app.config.settings import settings

class AuthService:
    """Servicio de autenticación simplificado"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verificar contraseña usando el mismo hash que se usó para crear los usuarios"""
        # Usar el mismo método de hash que se usó en el script SQL
        computed_hash = hashlib.sha256((plain_password + 'demo_salt_fhir').encode()).hexdigest()
        return computed_hash == hashed_password
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Crear token simplificado (no JWT real por ahora)"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire.isoformat(), 
            "iat": datetime.utcnow().isoformat()
        })
        
        # Token simplificado (base64 del JSON por ahora)
        token_data = json.dumps(to_encode, default=str)
        encoded_token = base64.b64encode(token_data.encode()).decode()
        return encoded_token
    
    @staticmethod
    async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[UserORM]:
        """Autenticar usuario por username/email y password"""
        try:
            # Buscar usuario por username o email
            stmt = select(UserORM).where(
                (UserORM.username == username) | (UserORM.email == username)
            ).where(UserORM.is_active == True)
            
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Verificar contraseña
            if not AuthService.verify_password(password, user.hashed_password):
                return None
                
            # Actualizar último login (sin commit aquí, se maneja en el endpoint)
            user.last_login = datetime.utcnow()
            user.login_attempts = 0
            db.add(user)  # Marcar para actualización
            
            return user
            
        except Exception as e:
            print(f"Error en autenticación: {e}")
            return None
    
    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[UserORM]:
        """Obtener usuario por username"""
        try:
            stmt = select(UserORM).where(UserORM.username == username)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"Error obteniendo usuario: {e}")
            return None
    
    @staticmethod
    def create_login_response(user: UserORM) -> Dict[str, Any]:
        """Crear respuesta de login exitoso"""
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = AuthService.create_access_token(
            data={
                "sub": str(user.id),
                "username": user.username,
                "user_type": user.user_type,
                "email": user.email
            },
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "user_type": user.user_type,
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
        }