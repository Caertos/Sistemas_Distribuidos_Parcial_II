from fastapi import APIRouter
from src.routes import auth as auth_module
from src.routes import secure as secure_module
from src.routes import admin as admin_module
from src.routes import patient as patient_module
from src.routes import practitioner as practitioner_module
from src.routes import auditor as auditor_module

router = APIRouter()

# mount subrouters
router.include_router(auth_module.router, prefix="/auth", tags=["auth"])
router.include_router(secure_module.router, prefix="/secure", tags=["secure"])
router.include_router(admin_module.router, prefix="/admin", tags=["admin"])
router.include_router(patient_module.router, prefix="/patient", tags=["patient"])
router.include_router(practitioner_module.router, prefix="/practitioner", tags=["practitioner"])
router.include_router(auditor_module.router, prefix="/admin/auditor", tags=["admin","auditor"])
