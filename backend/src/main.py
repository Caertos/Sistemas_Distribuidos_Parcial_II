from fastapi import FastAPI, Request, HTTPException  # Importa la clase principal para crear la aplicación FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Importa middleware para manejar CORS (Cross-Origin Resource Sharing)
from src.config import settings  # Importa la configuración de la aplicación
from src.routes.api import router  # Importa el enrutador con los endpoints de la API
from src.middleware.auth import AuthMiddleware
from src.middleware.audit import AuditMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path


app = FastAPI(  # Crea una instancia de la aplicación FastAPI
    title="Sistemas Distribuidos - Parcial II",  # Título de la aplicación
    description="API para el proyecto de Sistemas Distribuidos - Parcial II",  # Descripción de la aplicación
    version="1.0.0",  # Versión de la aplicación
    debug=settings.debug  # Configura el modo debug según la configuración
)


# CORS (ajustar allow_origins en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://tu-frontend.example"],
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
        "/admin",
        "/medic", 
        "/patient"
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

# Montar archivos estáticos del frontend
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Configurar Jinja2 para buscar templates en frontend/templates y frontend/dashboards
templates = Jinja2Templates(directory=[
    str(FRONTEND_DIR / "templates"),
    str(FRONTEND_DIR / "dashboards"),
    str(FRONTEND_DIR)
])


# Rutas del frontend para renderizar dashboards según rol
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirige a login - la autenticación se maneja en el cliente."""
    return RedirectResponse(url="/login")


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


@app.get("/health")
async def health():
    return {"status": "ok"}




