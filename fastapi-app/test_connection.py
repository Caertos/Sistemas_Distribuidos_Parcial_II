#!/usr/bin/env python3
"""
Test de conexión a la base de datos
Verificar configuración y conexión
"""

import sys
import os
sys.path.append('/media/caertos/DC/ProyectosAcademicos/Sistemas_Distribuidos_Parcial_II/fastapi-app')

from app.config.settings import settings
from app.utils.database import get_connection_test

def test_settings():
    """Test de configuración"""
    print("=== CONFIGURACIÓN ===")
    print(f"DB_HOST: {settings.db_host}")
    print(f"DB_PORT: {settings.db_port}")
    print(f"DB_NAME: {settings.db_name}")
    print(f"DB_USER: {settings.db_user}")
    print(f"DB_PASSWORD: {settings.db_password}")
    print(f"Database URL: {settings.database_url}")
    print()

def test_connection():
    """Test de conexión"""
    print("=== TEST DE CONEXIÓN ===")
    try:
        result = get_connection_test()
        print(f"Resultado: {result}")
        if result["success"]:
            print("✅ Conexión exitosa")
            print(f"Versión: {result['version']}")
            print(f"Base de datos: {result['database']}")
            print(f"Usuario: {result['user']}")
        else:
            print("❌ Error de conexión")
            print(f"Error: {result.get('error')}")
    except Exception as e:
        print(f"❌ Excepción: {e}")

if __name__ == "__main__":
    test_settings()
    test_connection()