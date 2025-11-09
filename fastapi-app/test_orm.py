"""
Test script para validar modelos ORM SQLAlchemy
Prueba la conectividad y estructura de los modelos
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import DatabaseManager
from app.models.orm import (
    Base, ORMUtils, PatientORM, PractitionerORM, ObservationORM,
    ConditionORM, MedicationRequestORM, DiagnosticReportORM
)


async def test_orm_models():
    """Prueba los modelos ORM y la estructura de base de datos"""
    
    print("🔍 Iniciando prueba de modelos ORM...")
    
    # Inicializar conexión a base de datos
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        # Obtener información de las tablas
        print("\n📊 Información de tablas:")
        table_info = ORMUtils.get_table_info()
        
        for table_name, info in table_info.items():
            print(f"\n  📋 Tabla: {table_name}")
            print(f"     - Modelo: {info['model_class']}")
            print(f"     - Tipo FHIR: {info['fhir_type']}")
            print(f"     - Distribuida: {info['is_distributed']}")
            print(f"     - Referencia: {info['is_reference']}")
            print(f"     - Primary Key: {info['primary_key']}")
            print(f"     - Columnas: {info['column_count']}")
            print(f"     - Índices: {info['index_count']}")
        
        # Validar configuración de Citus
        print("\n🔧 Validando configuración de Citus...")
        issues = ORMUtils.validate_citus_configuration()
        
        if issues:
            print("❌ Problemas encontrados:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✅ Configuración de Citus válida")
        
        # Probar conexión con una consulta simple
        print("\n🔗 Probando conexión con consulta de prueba...")
        
        async with db_manager.get_session() as session:
            # Consulta simple para verificar conectividad
            result = await session.execute("SELECT 1 as test")
            test_value = result.scalar()
            print(f"✅ Conexión exitosa - Resultado de prueba: {test_value}")
            
            # Verificar si las tablas existen
            print("\n📋 Verificando existencia de tablas...")
            for table_name in ["paciente", "profesional", "observacion", "condicion", "medicamento", "resultado_laboratorio"]:
                try:
                    result = await session.execute(f"SELECT COUNT(*) FROM {table_name} LIMIT 1")
                    count = result.scalar()
                    print(f"  ✅ Tabla '{table_name}' existe - Registros: {count}")
                except Exception as e:
                    print(f"  ❌ Error accediendo tabla '{table_name}': {str(e)}")
        
        print("\n🎉 Prueba de modelos ORM completada exitosamente!")
        
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db_manager.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_orm_models())