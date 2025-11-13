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

    # JWT
    jwt_secret: str = "Clinica-UAJS"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    class Config:
        # Buscar `.env` relativo al directorio `backend/` donde está este módulo
        from pathlib import Path

        env_file = str(Path(__file__).resolve().parent.parent / ".env")


settings = Settings()
