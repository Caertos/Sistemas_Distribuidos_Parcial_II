-- 00-create-db.sql
-- Create the target database before other init scripts switch to it
-- This runs first because of lexicographic order in /docker-entrypoint-initdb.d

CREATE DATABASE hce_distribuida WITH OWNER = postgres ENCODING = 'UTF8';

-- Ensure the DB exists and can be connected to (harmless if already present)
\connect hce_distribuida
