from fastapi import FastAPI, Request, HTTPException, Depends  # Importa la clase principal para crear la aplicación FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Importa middleware para manejar CORS (Cross-Origin Resource Sharing)
from src.config import settings  # Importa la configuración de la aplicación
from src.routes.api import router  # Importa el enrutador con los endpoints de la API
from src.middleware.auth import AuthMiddleware
from src.middleware.audit import AuditMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from fastapi.responses import FileResponse
from src.database import get_db
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging


app = FastAPI(  # Crea una instancia de la aplicación FastAPI
    title="Sistemas Distribuidos - Parcial II",  # Título de la aplicación
    description="API para el proyecto de Sistemas Distribuidos - Parcial II",  # Descripción de la aplicación
    version="1.0.0",  # Versión de la aplicación
    debug=settings.debug  # Configura el modo debug según la configuración
)


# CORS (ajustar allow_origins en producción)
# Configurar CORS - en desarrollo permitir localhost y 127.0.0.1 explícitamente
dev_allowed_origins = ["http://localhost:8000", "http://127.0.0.1:8000"]
# Construir lista de orígenes permitidos. Prioriza la variable `frontend_origins`
# si está definida (se espera una lista separada por comas). Si no, usa los
# orígenes de `dev_allowed_origins` cuando `debug` es True; finalmente usa un
# placeholder en producción si no se configura explícitamente.
if getattr(settings, "frontend_origins", None):
    allow_origins = [o.strip() for o in settings.frontend_origins.split(",") if o.strip()]
elif settings.debug:
    allow_origins = dev_allowed_origins
else:
    allow_origins = ["http://tu-frontend.example"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Autenticación global mediante middleware (todas las rutas requieren auth salvo allow_list)
# Decisión: permitimos que los endpoints de refresh y logout no requieran el access token
# en la cabecera para que clientes con access expirado puedan intercambiar/invalidar
# su refresh token. El endpoint `/api/auth/token` ya estaba allowlisted.
app.add_middleware(
    AuthMiddleware,
    allow_list=[
        "/health",
        "/api/auth/token",
        "/api/auth/refresh",
        "/api/auth/logout",
        "/api/auth/login",
        "/login",
        "/static*",  # permitir archivos estáticos sin auth (prefijo)
        "/",  # permitir raíz (redirige según sesión)
        "/dashboard",  # dashboards del frontend - manejan auth internamente
        "/admission",  # página del módulo Admission (frontend)
        "/admission*",  # permitir /admission/ y subrutas
        "/favicon.ico",
        "/admin",
        "/medic",
        "/patient",
        "/appointments*",  # permitir páginas frontend de citas
        "/profile",        # permitir página de perfil (cliente maneja auth)
        "/medical*",      # permitir historial/medicaciones/alergias frontend
    ],
)

# Middleware que registra accesos de lectura para auditoría
app.add_middleware(
    AuditMiddleware,
    # por defecto audita patient/practitioner/admin
    require_header=settings.require_document_header,
)

# Incluir rutas
app.include_router(router, prefix="/api")

# Configurar archivos estáticos y templates Jinja2
BACKEND_ROOT = Path(__file__).resolve().parent.parent  # backend/
# En el contenedor Docker, frontend está en /app/frontend
FRONTEND_DIR = Path("/app/frontend") if Path("/app/frontend").exists() else BACKEND_ROOT.parent / "frontend"

# Montar archivos estáticos del frontend (apunta a la carpeta `frontend/static`)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")

# Montar recursos estáticos específicos para el módulo Admission
if (FRONTEND_DIR / "admission" / "static").exists():
    app.mount("/admission/static", StaticFiles(directory=str(FRONTEND_DIR / "admission" / "static")), name="admission_static")

if (FRONTEND_DIR / "admission" / "components").exists():
    app.mount("/admission/components", StaticFiles(directory=str(FRONTEND_DIR / "admission" / "components")), name="admission_components")

# Servir admission.css directamente (la plantilla lo referencia como 'admission.css')
@app.get("/admission/admission.css")
async def admission_css():
    css_path = FRONTEND_DIR / "admission" / "admission.css"
    if css_path.exists():
        return FileResponse(str(css_path), media_type="text/css")
    return FileResponse(str(FRONTEND_DIR / "static" / "css" / "admission-dashboard.css"), media_type="text/css")

# Configurar Jinja2 para buscar templates en frontend/templates y frontend/dashboards
templates = Jinja2Templates(directory=[
    str(FRONTEND_DIR / "templates"),
    str(FRONTEND_DIR / "dashboards"),
    str(FRONTEND_DIR)
])


# Rutas del frontend para renderizar dashboards según rol
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Renderiza la página de inicio del frontend. El cliente se encargará
    de redirigir según el token/rol almacenado en `localStorage`."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Renderiza la página de login."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_generic(request: Request):
    """Dashboard genérico (fallback) - autenticación manejada por JS cliente."""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Dashboard",
        "metrics": {"patients": 0, "appointments_today": 0, "alerts": 0}
    })


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Dashboard de administrador - autenticación manejada por JS cliente."""
    return templates.TemplateResponse("admin/templates/admin.html", {
        "request": request,
        "title": "Administración",
        "metrics": {"users": 0, "servers": 0}
    })


@app.get("/medic", response_class=HTMLResponse)
async def medic_dashboard(request: Request):
    """Dashboard de médico/practitioner - autenticación manejada por JS cliente."""
    return templates.TemplateResponse("medic/templates/medic.html", {
        "request": request,
        "title": "Panel Médico",
        "metrics": {"assigned": 0, "appointments_today": 0}
    })


@app.get("/patient", response_class=HTMLResponse)
async def patient_dashboard(request: Request):
    """Dashboard de paciente - autenticación manejada por JS cliente."""
    return templates.TemplateResponse("patient/templates/patient.html", {
        "request": request,
        "title": "Mi Panel",
        "next_appointment": "—",
        "status": "—"
    })



@app.get("/appointments", response_class=HTMLResponse)
async def appointments_page(request: Request):
    """Página de listado de citas (frontend)."""
    return templates.TemplateResponse("appointments.html", {"request": request})


@app.get("/appointments/{appointment_id}", response_class=HTMLResponse)
async def appointment_detail_page(request: Request, appointment_id: int):
    """Página de detalle de una cita (frontend)."""
    return templates.TemplateResponse("appointment_detail.html", {"request": request, "appointment_id": appointment_id})


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Página de perfil del paciente (frontend)."""
    return templates.TemplateResponse("profile.html", {"request": request})


@app.get("/medical", response_class=HTMLResponse)
async def medical_page(request: Request):
    """Página de historial médico (frontend)."""
    return templates.TemplateResponse("medical_history.html", {"request": request})


@app.get("/admission", response_class=HTMLResponse)
@app.get("/admission/", response_class=HTMLResponse)
async def admission_page(request: Request):
    """Página del módulo de Admisión (frontend)."""
    # admitimos un template HTML estático dentro de frontend/admission/admission.html
    return templates.TemplateResponse("admission/admission.html", {"request": request, "title": "Admisión"})


@app.get("/health")
async def health():
    return {"status": "ok"}


# Ruta debug temporal: expone las citas pendientes consultando la tabla `cita` directamente.
# Esto se agrega en `main.py` para evitar posibles problemas con el registro de rutas
# en los subrouters durante la inicialización.
@app.get("/api/debug/admissions/pending")
def api_debug_list_pending_admissions(db: Session = Depends(get_db)):
    logger = logging.getLogger("backend.debug")
    try:
        q = text(
            "SELECT c.cita_id, c.documento_id, c.paciente_id, c.fecha_hora, c.tipo_cita, c.motivo, c.estado, c.estado_admision, p.nombre, p.apellido, p.sexo, p.fecha_nacimiento, p.contacto, EXTRACT(YEAR FROM AGE(p.fecha_nacimiento)) as edad, pr.nombre as profesional_nombre, pr.apellido as profesional_apellido, pr.especialidad FROM cita c INNER JOIN paciente p ON c.documento_id = p.documento_id AND c.paciente_id = p.paciente_id LEFT JOIN profesional pr ON c.profesional_id = pr.profesional_id WHERE c.estado_admision = 'pendiente' OR c.estado_admision IS NULL ORDER BY c.fecha_hora LIMIT 200"
        )
        rows = db.execute(q).mappings().all()
        logger.info("api_debug_list_pending_admissions: rows=%d", len(rows))
        return [dict(r) for r in rows]
    except Exception as e:
        logger.exception("api_debug_list_pending_admissions error")
        return {"error": str(e)}


# Evitar 404 por favicon requests del navegador: redirigir a un favicon público
@app.get("/favicon.ico")
async def favicon():
    # usamos un favicon público para evitar 404 durante desarrollo; si prefieres
    # servir un favicon local, coloca `favicon.ico` en `frontend/` y cambia esto.
    return RedirectResponse(url="https://fastapi.tiangolo.com/img/favicon.png")




