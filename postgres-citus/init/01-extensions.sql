-- 01-extensions.sql
-- Crear las extensiones requeridas por Citus y utilidades adicionales

-- Primero creamos las extensiones en la BD principal (hce_distribuida)
CREATE EXTENSION IF NOT EXISTS citus;
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- para generar UUIDs si lo deseas

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

-- Crear la BD 'hce' si no existe (para compatibilidad con esquemas FHIR)
SELECT 'CREATE DATABASE hce OWNER hce_app' 
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'hce')\gexec

\c hce

-- Asegurar que citus está instalado en la BD 'hce'
CREATE EXTENSION IF NOT EXISTS citus;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
