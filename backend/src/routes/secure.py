from fastapi import APIRouter, Request, Depends
from src.auth.deps import get_current_user
from src.auth.roles import require_role

router = APIRouter()


@router.get("/me")
async def me(request: Request, current_user: dict = Depends(get_current_user)):
    """Ruta protegida que devuelve la identidad mínima del usuario (ejemplo)."""
    # request.state.user también está disponible gracias al middleware
    return {"user": request.state.user}


@router.get("/admin-only")
async def admin_only(user: dict = require_role("admin")):
    return {"message": "Hello admin", "user": user}
