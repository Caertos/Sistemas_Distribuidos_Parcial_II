from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from src.config import settings


def create_access_token(subject: str, expires_minutes: Optional[int] = None, extras: Optional[Dict[str, Any]] = None) -> str:
    """Crea un JWT con el campo `sub` igual al identificador del sujeto.

    `extras` permite incluir claims adicionales (por ejemplo `role`).
    No permite que `extras` sobrescriba los claims reservados: sub, exp, iat.
    """
    now = datetime.utcnow()
    expire = now + timedelta(minutes=(expires_minutes or settings.jwt_expire_minutes))
    to_encode: Dict[str, Any] = {"sub": str(subject), "iat": now, "exp": expire}
    if extras:
        for k, v in extras.items():
            if k in ("sub", "exp", "iat"):
                # evitar sobrescribir claims estándar
                continue
            to_encode[k] = v
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verifica y decodifica un token JWT. Lanza `JWTError` si es inválido."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        raise
