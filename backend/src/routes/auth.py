from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.auth.utils import verify_password
from src.auth.jwt import create_access_token
from src.auth.refresh import create_refresh_token, verify_refresh_token, revoke_refresh_token
from src.database import get_db
from src.models.user import User

router = APIRouter()


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None
    role: str | None = None  # Añadido para frontend
    username: str | None = None  # Añadido para frontend


class LoginIn(BaseModel):
    username: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


@router.post("/token", response_model=TokenOut)
async def token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Endpoint OAuth2 password flow para obtener JWT y refresh token."""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    extras = {
        "role": user.user_type,
        # usar fhir_patient_id si existe; si no, fhir_practitioner_id; si ninguno, dejar None explícito
        "documento_id": user.fhir_patient_id or user.fhir_practitioner_id or None,
    }
    access_token = create_access_token(subject=user.id, extras=extras)
    # Crear refresh token (persistente)
    refresh = create_refresh_token(db, user.id)
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "refresh_token": refresh,
        "role": user.user_type,
        "username": user.username
    }


@router.post("/refresh", response_model=TokenOut)
def refresh_token(payload: RefreshIn, db: Session = Depends(get_db)):
    """Intercambia un refresh token válido por un nuevo access token y rota el refresh token."""
    rt = verify_refresh_token(db, payload.refresh_token)
    if not rt:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # obtener usuario para claims
    user = db.query(User).filter(User.id == rt.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    # rotación: revocar el refresh actual y emitir uno nuevo
    revoke_refresh_token(db, payload.refresh_token)
    new_refresh = create_refresh_token(db, user.id)
    access = create_access_token(subject=user.id, extras={
        "role": user.user_type,
        "documento_id": user.fhir_patient_id or user.fhir_practitioner_id or None,
    })
    return {"access_token": access, "token_type": "bearer", "refresh_token": new_refresh}


@router.post("/logout")
def logout(payload: RefreshIn, db: Session = Depends(get_db)):
    """Invalidar (revocar) un refresh token — logout por dispositivo."""
    ok = revoke_refresh_token(db, payload.refresh_token)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token not found")
    return {"detail": "logged out"}


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, db: Session = Depends(get_db)):
    """Endpoint JSON para login: recibe username/password en JSON y devuelve access + refresh token.

    Este endpoint es equivalente a `/token` (OAuth2 form) pero acepta JSON para clientes que
    prefieren enviar body JSON en lugar de form-encoded.
    """
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    extras = {
        "role": user.user_type,
        # documento_id: preferir fhir_patient_id si existe, si no fhir_practitioner_id
        "documento_id": user.fhir_patient_id or user.fhir_practitioner_id or None,
        "username": user.username,
    }
    access_token = create_access_token(subject=user.id, extras=extras)
    refresh = create_refresh_token(db, user.id)
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "refresh_token": refresh,
        "role": user.user_type,
        "username": user.username
    }
