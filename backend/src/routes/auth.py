from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.auth.utils import verify_password
from src.auth.jwt import create_access_token
from src.database import get_db
from src.models.user import User

router = APIRouter()


@router.post("/token")
async def token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Endpoint OAuth2 password flow para obtener JWT. Consulta la tabla `users` en la BD."""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    extras = {"role": user.user_type}
    access_token = create_access_token(subject=user.id, extras=extras)
    return {"access_token": access_token, "token_type": "bearer"}
