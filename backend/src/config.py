try:
    from pydantic_settings import BaseSettings
except Exception:
    # Fallback: pydantic v1
    from pydantic import BaseSettings


class Settings(BaseSettings):
    # Configuración general
    database_url: str = "postgresql://postgres:postgres@localhost:5432/hce_distribuida"
    secret_key: str = "Clinica-UAJS"
    debug: bool = True

    # Orígenes permitidos por CORS para el frontend.
    # Es una cadena con orígenes separados por comas, por ejemplo:
    # "http://localhost:8000,http://127.0.0.1:8000"
    frontend_origins: str | None = None
    # JWT
    jwt_secret: str = "Clinica-UAJS"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    # Si true, requerir header `X-Documento-Id` en peticiones a rutas auditadas
    require_document_header: bool = False

    class Config:
        # Buscar `.env` relativo al directorio `backend/` donde está este módulo
        from pathlib import Path

        env_file = str(Path(__file__).resolve().parent.parent / ".env")


settings = Settings()
