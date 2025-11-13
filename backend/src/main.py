from fastapi import FastAPI  # Importa la clase principal para crear la aplicación FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Importa middleware para manejar CORS (Cross-Origin Resource Sharing)
from src.config import settings  # Importa la configuración de la aplicación
from src.routes.api import router  # Importa el enrutador con los endpoints de la API
from src.middleware.auth import AuthMiddleware


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

# Autenticación global mediante middleware (todas las rutas requieren auth salvo allowlist)
app.add_middleware(AuthMiddleware, allow_list=["/health", "/api/auth/token"])

# Incluir rutas
app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}

