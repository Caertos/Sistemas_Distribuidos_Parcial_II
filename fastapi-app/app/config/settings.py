"""
Settings Configuration for FastAPI FHIR API
Configuración centralizada usando Pydantic Settings
"""

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Configuración de la aplicación usando Pydantic Settings"""
    
    # Application Settings
    app_name: str = Field(default="FHIR Clinical Records API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    reload: bool = Field(default=True, env="RELOAD")
    
    # Database Configuration (PostgreSQL + Citus)
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="clinical_records", env="DB_NAME")
    db_user: str = Field(default="postgres", env="DB_USER")
    db_password: str = Field(default="", env="DB_PASSWORD")
    
    # Database Pool Settings
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=3600, env="DB_POOL_RECYCLE")
    
    # Citus Specific Configuration
    citus_coordinator_host: str = Field(default="localhost", env="CITUS_COORDINATOR_HOST")
    citus_coordinator_port: int = Field(default=5432, env="CITUS_COORDINATOR_PORT")
    citus_worker_hosts: str = Field(default="localhost:5433,localhost:5434", env="CITUS_WORKER_HOSTS")
    
    # Security
    secret_key: str = Field(default="your-super-secret-key-here", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    api_key_expire_days: int = Field(default=365, env="API_KEY_EXPIRE_DAYS")
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    password_require_special: bool = Field(default=True, env="PASSWORD_REQUIRE_SPECIAL")
    password_require_numbers: bool = Field(default=True, env="PASSWORD_REQUIRE_NUMBERS")
    password_require_uppercase: bool = Field(default=True, env="PASSWORD_REQUIRE_UPPERCASE")
    
    # Logging Configuration
    log_level: str = Field(default="info", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # API Configuration
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    max_page_size: int = Field(default=100, env="MAX_PAGE_SIZE")
    default_page_size: int = Field(default=20, env="DEFAULT_PAGE_SIZE")
    
    # CORS Configuration
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")
    cors_credentials: bool = Field(default=True, env="CORS_CREDENTIALS")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }
    
    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v
    
    @field_validator("reload", mode="before") 
    @classmethod
    def parse_reload(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v
    
    @field_validator("cors_credentials", mode="before")
    @classmethod
    def parse_cors_credentials(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v
    
    @property
    def database_url(self) -> str:
        """Construir URL de conexión a la base de datos"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def citus_coordinator_url(self) -> str:
        """URL de conexión al coordinador de Citus"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.citus_coordinator_host}:{self.citus_coordinator_port}/{self.db_name}"
    
    @property
    def citus_worker_urls(self) -> List[str]:
        """Lista de URLs de workers de Citus"""
        worker_urls = []
        for worker in self.citus_worker_hosts.split(","):
            worker = worker.strip()
            if ":" in worker:
                host, port = worker.split(":")
                worker_url = f"postgresql://{self.db_user}:{self.db_password}@{host}:{port}/{self.db_name}"
                worker_urls.append(worker_url)
        return worker_urls
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Lista de orígenes CORS permitidos"""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Instancia global de configuración
settings = Settings()