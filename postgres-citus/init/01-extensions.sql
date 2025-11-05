-- 01-extensions.sql
-- Crear las extensiones requeridas por Citus y utilidades adicionales

CREATE EXTENSION IF NOT EXISTS citus;
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- para generar UUIDs si lo deseas

-- Ajustes opcionales: roles y usuarios mínimos
-- (En entorno de producción guarda credenciales en Secrets de K8s)

-- Usuario de aplicación
CREATE ROLE hce_app WITH LOGIN PASSWORD 'hce_password';
CREATE DATABASE hce OWNER hce_app;
\c hce

-- Asegurar que citus está instalado en la BD creada
CREATE EXTENSION IF NOT EXISTS citus;
