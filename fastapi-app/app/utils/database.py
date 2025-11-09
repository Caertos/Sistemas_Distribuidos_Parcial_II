"""
Database Utilities
Utilidades para manejo de base de datos y Citus
"""

from sqlalchemy import text
from typing import Dict, Any, List, Optional
import logging

from app.config.database import db_manager
from app.config.settings import settings

logger = logging.getLogger(__name__)


class CitusUtils:
    """Utilidades específicas para Citus"""
    
    @staticmethod
    def create_distributed_table(table_name: str, distribution_column: str = "paciente_id"):
        """Crear tabla distribuida en Citus"""
        try:
            with db_manager.get_session_context() as session:
                # Crear tabla distribuida
                query = text(f"SELECT create_distributed_table('{table_name}', '{distribution_column}')")
                result = session.execute(query)
                logger.info(f"Tabla {table_name} distribuida exitosamente por {distribution_column}")
                return result.fetchone()
        except Exception as e:
            logger.error(f"Error creando tabla distribuida {table_name}: {e}")
            raise
    
    @staticmethod
    def create_reference_table(table_name: str):
        """Crear tabla de referencia en Citus (replicada en todos los nodos)"""
        try:
            with db_manager.get_session_context() as session:
                query = text(f"SELECT create_reference_table('{table_name}')")
                result = session.execute(query)
                logger.info(f"Tabla de referencia {table_name} creada exitosamente")
                return result.fetchone()
        except Exception as e:
            logger.error(f"Error creando tabla de referencia {table_name}: {e}")
            raise
    
    @staticmethod
    def get_table_distribution_info(table_name: str) -> Dict[str, Any]:
        """Obtener información de distribución de una tabla"""
        try:
            with db_manager.get_session_context() as session:
                query = text("""
                    SELECT 
                        schemaname,
                        tablename,
                        colgroupid,
                        repmodel,
                        autoconverted
                    FROM pg_dist_partition 
                    WHERE tablename = :table_name
                """)
                result = session.execute(query, {"table_name": table_name}).fetchone()
                
                if result:
                    return {
                        "schema": result[0],
                        "table": result[1],
                        "column_group_id": result[2],
                        "replication_model": result[3],
                        "auto_converted": result[4]
                    }
                return {}
        except Exception as e:
            logger.error(f"Error obteniendo información de distribución para {table_name}: {e}")
            return {}
    
    @staticmethod
    def get_shard_count(table_name: str) -> int:
        """Obtener número de shards de una tabla"""
        try:
            with db_manager.get_session_context() as session:
                query = text("""
                    SELECT COUNT(*) 
                    FROM pg_dist_shard s
                    JOIN pg_dist_partition p ON s.logicalrelid = p.logicalrelid
                    WHERE p.tablename = :table_name
                """)
                result = session.execute(query, {"table_name": table_name}).fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error obteniendo número de shards para {table_name}: {e}")
            return 0
    
    @staticmethod
    def rebalance_shards():
        """Rebalancear shards en el clúster"""
        try:
            with db_manager.get_session_context() as session:
                query = text("SELECT rebalance_table_shards()")
                result = session.execute(query)
                logger.info("Rebalanceo de shards completado")
                return result.fetchall()
        except Exception as e:  
            logger.error(f"Error rebalanceando shards: {e}")
            raise


class DatabaseUtils:
    """Utilidades generales de base de datos"""
    
    @staticmethod
    def test_connection() -> Dict[str, Any]:
        """Probar conexión a la base de datos"""
        try:
            with db_manager.get_session_context() as session:
                result = session.execute(text("SELECT version(), current_database(), current_user")).fetchone()
                return {
                    "success": True,
                    "version": result[0],
                    "database": result[1],
                    "user": result[2]
                }
        except Exception as e:
            logger.error(f"Error probando conexión: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_table_stats(table_name: str) -> Dict[str, Any]:
        """Obtener estadísticas de una tabla"""
        try:
            with db_manager.get_session_context() as session:
                # Estadísticas básicas
                count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                count_result = session.execute(count_query).fetchone()
                
                # Tamaño de la tabla
                size_query = text("""
                    SELECT pg_size_pretty(pg_total_relation_size(:table_name)) as size
                """)
                size_result = session.execute(size_query, {"table_name": table_name}).fetchone()
                
                return {
                    "table_name": table_name,
                    "row_count": count_result[0] if count_result else 0,
                    "size": size_result[0] if size_result else "0 bytes"
                }
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas para {table_name}: {e}")
            return {
                "table_name": table_name,
                "row_count": 0,
                "size": "0 bytes",
                "error": str(e)
            }
    
    @staticmethod
    def execute_health_checks() -> Dict[str, Any]:
        """Ejecutar checks de salud completos"""
        health_status = {
            "database_connection": False,
            "citus_available": False,
            "tables_exist": False,
            "distributed_tables": 0,
            "total_shards": 0,
            "workers_count": 0,
            "details": {}
        }
        
        try:
            # Test básico de conexión
            connection_test = DatabaseUtils.test_connection()
            health_status["database_connection"] = connection_test["success"]
            health_status["details"]["connection"] = connection_test
            
            # Test de Citus
            with db_manager.get_session_context() as session:
                try:
                    # Verificar si Citus está disponible
                    citus_check = session.execute(text("SELECT citus_version()")).fetchone()
                    if citus_check:
                        health_status["citus_available"] = True
                        health_status["details"]["citus_version"] = citus_check[0]
                except Exception:
                    health_status["details"]["citus_version"] = "Not available"
                
                # Verificar tablas principales
                main_tables = ['paciente', 'profesional', 'observacion', 'encuentro', 'condicion']
                existing_tables = []
                
                for table in main_tables:
                    try:
                        check_query = text("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_name = :table_name
                            )
                        """)
                        exists = session.execute(check_query, {"table_name": table}).fetchone()[0]
                        if exists:
                            existing_tables.append(table)
                    except Exception as e:
                        logger.error(f"Error verificando tabla {table}: {e}")
                
                health_status["tables_exist"] = len(existing_tables) > 0
                health_status["details"]["existing_tables"] = existing_tables
                
                # Información del clúster
                cluster_info = db_manager.get_cluster_info()
                health_status["distributed_tables"] = len(cluster_info.get("distributed_tables", []))
                health_status["total_shards"] = cluster_info.get("shards", 0)
                health_status["workers_count"] = len(cluster_info.get("workers", []))
                health_status["details"]["cluster"] = cluster_info
            
        except Exception as e:
            logger.error(f"Error en health checks: {e}")
            health_status["details"]["error"] = str(e)
        
        return health_status


# Funciones de conveniencia
def get_connection_test() -> Dict[str, Any]:
    """Test rápido de conexión"""
    return DatabaseUtils.test_connection()

def get_cluster_health() -> Dict[str, Any]:
    """Estado de salud del clúster"""
    return DatabaseUtils.execute_health_checks()

def setup_distributed_tables():
    """Configurar tablas distribuidas para el esquema FHIR"""
    distributed_tables = [
        ("paciente", "paciente_id"),
        ("observacion", "paciente_id"),
        ("encuentro", "paciente_id"),
        ("condicion", "paciente_id"),
        ("cita", "paciente_id"),
        ("medicamento", "paciente_id"),
        ("procedimiento", "paciente_id"),
        ("resultado_laboratorio", "paciente_id"),
        ("signos_vitales", "paciente_id"),
        ("alergia_intolerancia", "paciente_id"),
        ("inmunizacion", "paciente_id"),
        ("estudio_imagen", "paciente_id"),
        ("plan_cuidado", "paciente_id"),
        ("dispositivo_medico", "paciente_id"),
        ("consentimiento", "paciente_id"),
        ("factura", "paciente_id"),
    ]
    
    reference_tables = [
        "profesional",
        "organizacion",
        "ubicacion",
        "concepto_terminologia",
        "guia_clinica",
        "estudio_investigacion",
        "grupo_pacientes"
    ]
    
    results = {
        "distributed_tables": [],
        "reference_tables": [],
        "errors": []
    }
    
    try:
        # Crear tablas distribuidas
        for table_name, distribution_column in distributed_tables:
            try:
                CitusUtils.create_distributed_table(table_name, distribution_column)
                results["distributed_tables"].append(f"{table_name} (by {distribution_column})")
            except Exception as e:
                error_msg = f"Error distributing {table_name}: {e}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        # Crear tablas de referencia
        for table_name in reference_tables:
            try:
                CitusUtils.create_reference_table(table_name)
                results["reference_tables"].append(table_name)
            except Exception as e:
                error_msg = f"Error creating reference table {table_name}: {e}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
    except Exception as e:
        error_msg = f"Error general en setup de tablas distribuidas: {e}"
        results["errors"].append(error_msg)
        logger.error(error_msg)
    
    return results