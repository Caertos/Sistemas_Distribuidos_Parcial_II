from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from src.config import settings


def create_access_token(subject: str, expires_minutes: Optional[int] = None, extras: Optional[Dict[str, Any]] = None) -> str:
    """Crea un JWT con el campo `sub` igual al identificador del sujeto.

    `extras` permite incluir claims adicionales (por ejemplo `role`).
    """
    expire = datetime.utcnow() + timedelta(minutes=(expires_minutes or settings.jwt_expire_minutes))
    to_encode: Dict[str, Any] = {"sub": str(subject), "exp": expire}
    if extras:
        to_encode.update(extras)
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verifica y decodifica un token JWT. Lanza `JWTError` si es inválido."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        raise
