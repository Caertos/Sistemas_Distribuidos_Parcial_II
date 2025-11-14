-- 01-extensions.sql
-- Crear las extensiones requeridas por Citus y utilidades adicionales

-- Primero creamos las extensiones en la BD principal (hce_distribuida)
CREATE EXTENSION IF NOT EXISTS citus;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Ajustes opcionales: roles y usuarios mínimos
-- (En entorno de producción guarda credenciales en Secrets de K8s)

-- Usuario de aplicación (si no existe)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'hce_app') THEN
    CREATE ROLE hce_app WITH LOGIN PASSWORD 'hce_password';
  END IF;
END
$$;

-- Usar la BD principal 'hce_distribuida' para compatibilidad
-- Las extensiones ya están instaladas arriba
