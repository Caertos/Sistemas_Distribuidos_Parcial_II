-- 02-schema-fhir.sql
-- Esquema FHIR (Fast Healthcare Interoperability Resources)
-- Diseñado para distribuir por documento_id (agrupando datos de cada paciente)
-- IMPORTANTE: Las PKs deben incluir la columna de distribución en Citus

\c hce

-- Tabla de pacientes (distribuida por documento_id)
-- La PK compuesta incluye documento_id para cumplir con requisitos de Citus
CREATE TABLE IF NOT EXISTS paciente (
  paciente_id BIGINT,
  documento_id BIGINT NOT NULL,
  uuid UUID DEFAULT gen_random_uuid(),
  nombre TEXT,
  apellido TEXT,
  sexo VARCHAR(10),
  fecha_nacimiento DATE,
  contacto TEXT,
  ciudad TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, paciente_id)
);

-- Tabla de profesionales (replicada en todos los nodos)
-- No requiere documento_id porque es tabla de referencia
CREATE TABLE IF NOT EXISTS profesional (
  profesional_id BIGSERIAL PRIMARY KEY,
  nombre TEXT,
  apellido TEXT,
  especialidad TEXT,
  registro_medico TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Tabla de encuentros/consultas (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS encuentro (
  encuentro_id BIGSERIAL,
  paciente_id BIGINT NOT NULL,
  documento_id BIGINT NOT NULL,
  fecha TIMESTAMP WITH TIME ZONE DEFAULT now(),
  motivo TEXT,
  diagnostico TEXT,
  profesional_id BIGINT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, encuentro_id)
);

-- Tabla de observaciones clínicas (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS observacion (
  observacion_id BIGSERIAL,
  paciente_id BIGINT NOT NULL,
  documento_id BIGINT NOT NULL,
  tipo TEXT NOT NULL,
  valor TEXT,
  unidad TEXT,
  fecha TIMESTAMP WITH TIME ZONE DEFAULT now(),
  referencia_encuentro BIGINT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, observacion_id)
);

-- Tabla de condiciones/diagnósticos (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS condicion (
  condicion_id BIGSERIAL,
  paciente_id BIGINT NOT NULL,
  documento_id BIGINT NOT NULL,
  codigo TEXT,
  descripcion TEXT NOT NULL,
  gravedad TEXT,
  fecha_inicio DATE,
  fecha_fin DATE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, condicion_id)
);

-- Convertir tablas a distribuidas/replicadas en Citus
-- NOTA: Las tablas deben existir ANTES de distribuirlas

-- Distribuir por documento_id (co-location para queries eficientes)
SELECT create_distributed_table('paciente', 'documento_id');
SELECT create_distributed_table('encuentro', 'documento_id');
SELECT create_distributed_table('observacion', 'documento_id');
SELECT create_distributed_table('condicion', 'documento_id');

-- Profesional es tabla de referencia (replicada en todos los workers)
SELECT create_reference_table('profesional');

-- Índices para optimizar consultas comunes
CREATE INDEX IF NOT EXISTS idx_paciente_nombre ON paciente(nombre, apellido);
CREATE INDEX IF NOT EXISTS idx_observacion_fecha ON observacion(fecha);
CREATE INDEX IF NOT EXISTS idx_observacion_tipo ON observacion(tipo);
CREATE INDEX IF NOT EXISTS idx_encuentro_fecha ON encuentro(fecha);
CREATE INDEX IF NOT EXISTS idx_condicion_fecha ON condicion(fecha_inicio);
