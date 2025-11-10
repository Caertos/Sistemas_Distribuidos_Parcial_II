"""
Database Configuration for PostgreSQL + Citus
Configuración de conexión a clúster distribuido
"""

from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager, asynccontextmanager
from typing import Generator, Optional, List, AsyncGenerator
import logging

from .settings import settings

# Configurar logging
logger = logging.getLogger(__name__)

# Base para modelos SQLAlchemy
Base = declarative_base()

# Metadata para esquemas
metadata = MetaData()

class DatabaseManager:
    """Gestor de conexiones a PostgreSQL + Citus"""
    
    def __init__(self):
        self.coordinator_engine = None
        self.async_coordinator_engine = None
        self.worker_engines = []
        self.SessionLocal = None
        self.AsyncSessionLocal = None
        self._setup_engines()
    
    def _setup_engines(self):
        """Configurar engines para coordinator y workers"""
        try:
            # Engine principal (Coordinator)
            self.coordinator_engine = create_engine(
                settings.citus_coordinator_url,
                poolclass=QueuePool,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_timeout=settings.db_pool_timeout,
                pool_recycle=settings.db_pool_recycle,
                pool_pre_ping=True,  # Verificar conexiones antes de usar
                echo=settings.debug,  # Log SQL queries en debug
            )
            
            # Configurar eventos para optimización de Citus
            @event.listens_for(self.coordinator_engine, "connect")
            def set_citus_settings(dbapi_connection, connection_record):
                """Configurar parámetros específicos de Citus"""
                with dbapi_connection.cursor() as cursor:
                    # Optimizaciones para Citus
                    cursor.execute("SET citus.multi_shard_modify_mode TO 'parallel'")
                    cursor.execute("SET citus.enable_repartition_joins TO on")
                    cursor.execute("SET citus.enable_fast_path_router_planner TO on")
                    cursor.execute("SET work_mem = '256MB'")
                    cursor.execute("SET random_page_cost = 1.1")
            
            # Session factory (síncrono)
            self.SessionLocal = sessionmaker(
                bind=self.coordinator_engine,
                autocommit=False,
                autoflush=False
            )
            
            # Async engine y session para FastAPI async endpoints
            async_url = settings.citus_coordinator_url.replace('postgresql://', 'postgresql+asyncpg://')
            self.async_coordinator_engine = create_async_engine(
                async_url,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_timeout=settings.db_pool_timeout,
                pool_recycle=settings.db_pool_recycle,
                pool_pre_ping=True,
                echo=settings.debug,
            )
            
            # Async session factory
            self.AsyncSessionLocal = async_sessionmaker(
                bind=self.async_coordinator_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False
            )
            
            logger.info(f"Conexión a Citus Coordinator establecida: {settings.citus_coordinator_host}:{settings.citus_coordinator_port}")
            
            # Engines para workers (para consultas específicas si es necesario)
            for worker_url in settings.citus_worker_urls:
                try:
                    worker_engine = create_engine(
                        worker_url,
                        poolclass=QueuePool,
                        pool_size=5,  # Pool más pequeño para workers
                        max_overflow=10,
                        pool_timeout=settings.db_pool_timeout,
                        pool_recycle=settings.db_pool_recycle,
                        pool_pre_ping=True,
                        echo=settings.debug,
                    )
                    self.worker_engines.append(worker_engine)
                    logger.info(f"Conexión a Citus Worker establecida: {worker_url}")
                except Exception as e:
                    logger.warning(f"No se pudo conectar al worker {worker_url}: {e}")
            
        except Exception as e:
            logger.error(f"Error configurando engines de base de datos: {e}")
            raise
    
    def get_session(self) -> Generator[Session, None, None]:
        """Generator para sesiones de base de datos"""
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            logger.error(f"Error en sesión de base de datos: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def get_session_context(self):
        """Context manager para sesiones de base de datos"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(f"Error en transacción: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def health_check(self) -> dict:
        """Verificar estado de conexiones"""
        health_status = {
            "coordinator": False,
            "workers": [],
            "total_workers": len(self.worker_engines),
            "healthy_workers": 0
        }
        
        # Verificar coordinator
        try:
            with self.coordinator_engine.connect() as conn:
                result = conn.execute("SELECT 1 as health").fetchone()
                if result and result[0] == 1:
                    health_status["coordinator"] = True
        except Exception as e:
            logger.error(f"Health check falló para coordinator: {e}")
        
        # Verificar workers
        for i, worker_engine in enumerate(self.worker_engines):
            worker_status = {"index": i, "healthy": False}
            try:
                with worker_engine.connect() as conn:
                    result = conn.execute("SELECT 1 as health").fetchone()
                    if result and result[0] == 1:
                        worker_status["healthy"] = True
                        health_status["healthy_workers"] += 1
            except Exception as e:
                logger.error(f"Health check falló para worker {i}: {e}")
            
            health_status["workers"].append(worker_status)
        
        return health_status
    
    def get_cluster_info(self) -> dict:
        """Obtener información del clúster Citus"""
        cluster_info = {
            "coordinator": None,
            "workers": [],
            "distributed_tables": [],
            "shards": 0
        }
        
        try:
            with self.get_session_context() as session:
                # Información del coordinator
                result = session.execute("""
                    SELECT 
                        version() as version,
                        current_database() as database,
                        current_user as user
                """).fetchone()
                
                if result:
                    cluster_info["coordinator"] = {
                        "version": result[0],
                        "database": result[1],
                        "user": result[2]
                    }
                
                # Información de workers (si Citus está disponible)
                try:
                    workers_result = session.execute("""
                        SELECT nodename, nodeport, groupid, noderack, hasmetadata, isactive, noderole, nodecluster
                        FROM pg_dist_node 
                        WHERE noderole = 'primary'
                    """).fetchall()
                    
                    for worker in workers_result:
                        cluster_info["workers"].append({
                            "host": worker[0],
                            "port": worker[1],
                            "group_id": worker[2],
                            "rack": worker[3],
                            "has_metadata": worker[4],
                            "is_active": worker[5],
                            "role": worker[6],
                            "cluster": worker[7]
                        })
                except Exception:
                    logger.info("Información de workers de Citus no disponible (normal si Citus no está configurado)")
                
                # Tablas distribuidas
                try:
                    tables_result = session.execute("""
                        SELECT schemaname, tablename, colgroupid, repmodel, autoconverted
                        FROM pg_dist_partition
                    """).fetchall()
                    
                    for table in tables_result:
                        cluster_info["distributed_tables"].append({
                            "schema": table[0],
                            "table": table[1],
                            "column_group_id": table[2],
                            "replication_model": table[3],
                            "auto_converted": table[4]
                        })
                except Exception:
                    logger.info("Información de tablas distribuidas no disponible")
                
                # Número de shards
                try:
                    shards_result = session.execute("""
                        SELECT COUNT(*) FROM pg_dist_shard
                    """).fetchone()
                    
                    if shards_result:
                        cluster_info["shards"] = shards_result[0]
                except Exception:
                    logger.info("Información de shards no disponible")
                
        except Exception as e:
            logger.error(f"Error obteniendo información del clúster: {e}")
        
        return cluster_info
    
    def execute_distributed_query(self, query: str, params: dict = None) -> List[dict]:
        """Ejecutar query optimizada para distribución"""
        try:
            with self.get_session_context() as session:
                # Configurar parámetros de Citus para la query
                session.execute("SET citus.multi_shard_modify_mode TO 'parallel'")
                session.execute("SET citus.enable_repartition_joins TO on")
                
                result = session.execute(query, params or {})
                
                # Convertir resultado a lista de diccionarios
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Error ejecutando query distribuida: {e}")
            raise
    
    def close_connections(self):
        """Cerrar todas las conexiones"""
        try:
            if self.coordinator_engine:
                self.coordinator_engine.dispose()
                logger.info("Conexión coordinator cerrada")
            
            for i, worker_engine in enumerate(self.worker_engines):
                worker_engine.dispose()
                logger.info(f"Conexión worker {i} cerrada")
                
        except Exception as e:
            logger.error(f"Error cerrando conexiones: {e}")


# Instancia global del manager
db_manager = DatabaseManager()

# Dependencia para FastAPI
def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI para obtener sesión de base de datos"""
    yield from db_manager.get_session()

# Dependencia async para FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI para obtener sesión async de base de datos"""
    async with db_manager.AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Error en sesión async: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

# Alias para compatibilidad
get_session = get_db