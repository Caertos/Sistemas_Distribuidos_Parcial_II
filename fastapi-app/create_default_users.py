#!/usr/bin/env python3
"""
Script para crear usuarios predeterminados en el sistema FHIR
Crea usuarios con credenciales conocidas para testing y demostración

Usuarios creados:
- admin/admin (rol: admin)
- medic/medic (rol: practitioner) 
- patient/patient (rol: patient)
- audit/audit (rol: viewer)
"""

import asyncio
import sys
import os
from pathlib import Path

# Agregar el directorio de la aplicación al path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

from app.core.database import get_database
from app.core.security import get_password_hash
from app.models.auth import UserRole
import asyncpg
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Usuarios predeterminados
DEFAULT_USERS = [
    {
        "username": "admin",
        "email": "admin@hospital.com",
        "password": "admin",
        "full_name": "Administrador del Sistema",
        "role": UserRole.ADMIN,
        "is_active": True,
        "is_verified": True,
        "description": "Usuario administrador con acceso completo al sistema"
    },
    {
        "username": "medic",
        "email": "medic@hospital.com", 
        "password": "medic",
        "full_name": "Dr. Juan Pérez",
        "role": UserRole.PRACTITIONER,
        "is_active": True,
        "is_verified": True,
        "description": "Médico con acceso a historias clínicas y gestión de pacientes"
    },
    {
        "username": "patient",
        "email": "patient@hospital.com",
        "password": "patient", 
        "full_name": "María García",
        "role": UserRole.PATIENT,
        "is_active": True,
        "is_verified": True,
        "description": "Paciente con acceso a su propia historia clínica"
    },
    {
        "username": "audit",
        "email": "audit@hospital.com",
        "password": "audit",
        "full_name": "Auditor del Sistema",
        "role": UserRole.VIEWER,
        "is_active": True,
        "is_verified": True,
        "description": "Auditor con acceso de solo lectura y logs del sistema"
    }
]

async def check_database_connection():
    """Verificar conexión a la base de datos"""
    try:
        db = await get_database()
        await db.fetchval("SELECT 1")
        logger.info("✅ Conexión a la base de datos exitosa")
        return db
    except Exception as e:
        logger.error(f"❌ Error conectando a la base de datos: {e}")
        return None

async def user_exists(db: asyncpg.Connection, username: str) -> bool:
    """Verificar si un usuario ya existe"""
    result = await db.fetchval(
        "SELECT id FROM users WHERE username = $1",
        username
    )
    return result is not None

async def create_user(db: asyncpg.Connection, user_data: dict) -> bool:
    """Crear un usuario en la base de datos"""
    try:
        # Hash de la contraseña
        hashed_password = get_password_hash(user_data["password"])
        
        # Insertar usuario
        user_id = await db.fetchval("""
            INSERT INTO users (
                username, email, hashed_password, full_name, 
                role, is_active, is_verified, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, NOW(), NOW()
            ) RETURNING id
        """,
            user_data["username"],
            user_data["email"],
            hashed_password,
            user_data["full_name"],
            user_data["role"].value,
            user_data["is_active"],
            user_data["is_verified"]
        )
        
        logger.info(f"✅ Usuario creado: {user_data['username']} (ID: {user_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando usuario {user_data['username']}: {e}")
        return False

async def create_user_profile(db: asyncpg.Connection, username: str, role: UserRole, full_name: str):
    """Crear perfil adicional según el rol del usuario"""
    try:
        user_id = await db.fetchval("SELECT id FROM users WHERE username = $1", username)
        
        if role == UserRole.PRACTITIONER:
            # Crear perfil de médico en la tabla practitioners
            await db.execute("""
                INSERT INTO practitioners (
                    user_id, identifier, name_given, name_family,
                    specialty, phone, email, active, created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, true, NOW()
                ) ON CONFLICT (user_id) DO NOTHING
            """,
                user_id,
                f"DOC-{user_id:06d}",
                "Dr. Juan",
                "Pérez",
                "Medicina General",
                "+1-555-0123",
                "medic@hospital.com"
            )
            logger.info(f"✅ Perfil de médico creado para {username}")
            
        elif role == UserRole.PATIENT:
            # Crear perfil de paciente en la tabla patients
            await db.execute("""
                INSERT INTO patients (
                    user_id, identifier, name_given, name_family,
                    birth_date, gender, phone, email, active, created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, true, NOW()
                ) ON CONFLICT (user_id) DO NOTHING  
            """,
                user_id,
                f"PAT-{user_id:06d}",
                "María",
                "García",
                "1985-03-15",
                "female",
                "+1-555-0456",
                "patient@hospital.com"
            )
            logger.info(f"✅ Perfil de paciente creado para {username}")
            
    except Exception as e:
        logger.error(f"❌ Error creando perfil para {username}: {e}")

async def update_table_statistics():
    """Actualizar estadísticas de las tablas para optimización"""
    try:
        db = await get_database()
        await db.execute("ANALYZE users")
        await db.execute("ANALYZE practitioners") 
        await db.execute("ANALYZE patients")
        logger.info("✅ Estadísticas de tablas actualizadas")
    except Exception as e:
        logger.error(f"❌ Error actualizando estadísticas: {e}")

async def main():
    """Función principal"""
    logger.info("🚀 Iniciando creación de usuarios predeterminados...")
    
    # Verificar conexión
    db = await check_database_connection()
    if not db:
        logger.error("❌ No se pudo conectar a la base de datos")
        sys.exit(1)
    
    created_count = 0
    skipped_count = 0
    
    # Procesar cada usuario
    for user_data in DEFAULT_USERS:
        username = user_data["username"]
        
        # Verificar si ya existe
        if await user_exists(db, username):
            logger.info(f"⚠️  Usuario '{username}' ya existe, saltando...")
            skipped_count += 1
            continue
        
        # Crear usuario
        if await create_user(db, user_data):
            # Crear perfil adicional según el rol
            await create_user_profile(db, username, user_data["role"], user_data["full_name"])
            created_count += 1
        
    # Actualizar estadísticas
    await update_table_statistics()
    
    # Resumen
    total_users = len(DEFAULT_USERS)
    logger.info("\n" + "="*50)
    logger.info("📊 RESUMEN DE CREACIÓN DE USUARIOS")
    logger.info("="*50)
    logger.info(f"Total usuarios procesados: {total_users}")
    logger.info(f"Usuarios creados: {created_count}")
    logger.info(f"Usuarios existentes (saltados): {skipped_count}")
    
    if created_count > 0:
        logger.info("\n✅ USUARIOS CREADOS EXITOSAMENTE:")
        logger.info("-" * 40)
        for user_data in DEFAULT_USERS:
            if not await user_exists(db, user_data["username"]) or created_count > 0:
                logger.info(f"• {user_data['username']}/{user_data['password']} - {user_data['role'].value}")
                logger.info(f"  📧 {user_data['email']}")
                logger.info(f"  👤 {user_data['full_name']}")
                logger.info(f"  📝 {user_data['description']}")
                logger.info("")
    
    logger.info("🎯 CREDENCIALES DE ACCESO:")
    logger.info("-" * 30)
    logger.info("admin/admin     - Administrador")
    logger.info("medic/medic     - Médico")  
    logger.info("patient/patient - Paciente")
    logger.info("audit/audit     - Auditor")
    logger.info("")
    logger.info("🌐 Acceso a la aplicación:")
    logger.info("http://localhost:8000/docs (API)")
    logger.info("http://localhost:8000/login (Web)")
    logger.info("")
    logger.info("✅ Proceso completado exitosamente!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Error inesperado: {e}")
        sys.exit(1)