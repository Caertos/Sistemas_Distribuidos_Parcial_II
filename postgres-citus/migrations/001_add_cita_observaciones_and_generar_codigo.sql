-- Migration: add observaciones and updated_at to cita, create admission sequence and generar_codigo_admision()
-- Run this against the coordinator database (hce_distribuida)

BEGIN;

-- Add observaciones column if not present
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cita' AND column_name='observaciones') THEN
        ALTER TABLE cita ADD COLUMN observaciones text;
    END IF;
END$$;

-- Add updated_at column if not present
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cita' AND column_name='updated_at') THEN
        ALTER TABLE cita ADD COLUMN updated_at timestamptz;
    END IF;
END$$;

-- Create a sequence for admission codes if it does not exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = 'admission_seq') THEN
        CREATE SEQUENCE admission_seq START 1;
    END IF;
END$$;

-- Create or replace generar_codigo_admision function
CREATE OR REPLACE FUNCTION generar_codigo_admision() RETURNS text AS $$
DECLARE
    seqval bigint;
BEGIN
    seqval := nextval('admission_seq');
    RETURN format('ADM-%s-%s', to_char(now() AT TIME ZONE 'UTC', 'YYYYMMDD'), lpad(seqval::text,4,'0'));
END;
$$ LANGUAGE plpgsql;

COMMIT;

-- End migration
