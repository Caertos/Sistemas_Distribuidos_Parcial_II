from fastapi import APIRouter
from src.routes import auth as auth_module
from src.routes import secure as secure_module

router = APIRouter()

# mount subrouters
router.include_router(auth_module.router, prefix="/auth", tags=["auth"])
router.include_router(secure_module.router, prefix="/secure", tags=["secure"])
