-- 02-schema-fhir.sql
-- Esquema mínimo inspirado en recursos FHIR (Patient, Observation, Encounter, Practitioner, Condition)
-- Diseñado para distribuir por paciente_id (documento_id)

\c hce

-- Tabla de pacientes (distribuible)
CREATE TABLE IF NOT EXISTS paciente (
  paciente_id BIGINT PRIMARY KEY,
  uuid UUID DEFAULT gen_random_uuid(),
  documento_id BIGINT NOT NULL,
  nombre TEXT,
  apellido TEXT,
  sexo VARCHAR(10),
  fecha_nacimiento DATE,
  contacto TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Tabla de profesionales (replicada: suele ser consultada desde cualquier nodo)
CREATE TABLE IF NOT EXISTS profesional (
  profesional_id BIGSERIAL PRIMARY KEY,
  nombre TEXT,
  apellido TEXT,
  especialidad TEXT
);

-- Tabla de encuentros/encounters (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS encuentro (
  encuentro_id BIGSERIAL PRIMARY KEY,
  paciente_id BIGINT NOT NULL,
  documento_id BIGINT NOT NULL,
  fecha TIMESTAMP WITH TIME ZONE,
  motivo TEXT,
  profesional_id BIGINT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Tabla de observaciones (observations) asociadas a paciente
CREATE TABLE IF NOT EXISTS observacion (
  observacion_id BIGSERIAL PRIMARY KEY,
  paciente_id BIGINT NOT NULL,
  documento_id BIGINT NOT NULL,
  tipo TEXT,
  valor TEXT,
  unidad TEXT,
  fecha TIMESTAMP WITH TIME ZONE,
  referencia_encuentro BIGINT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Tabla de condiciones/diagnósticos
CREATE TABLE IF NOT EXISTS condicion (
  condicion_id BIGSERIAL PRIMARY KEY,
  paciente_id BIGINT NOT NULL,
  documento_id BIGINT NOT NULL,
  codigo TEXT,
  descripcion TEXT,
  fecha_inicio DATE,
  fecha_fin DATE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Convertir tablas a tablas distribuidas/replicadas en Citus
-- Distribuiremos por documento_id para agrupar todo lo relativo a un paciente

SELECT master_create_distributed_table('paciente', 'documento_id');
SELECT master_create_distributed_table('encuentro', 'documento_id');
SELECT master_create_distributed_table('observacion', 'documento_id');
SELECT master_create_distributed_table('condicion', 'documento_id');

-- Profesional será una tabla de referencia (replicada en todos los nodos)
SELECT master_create_reference_table('profesional');

-- Índices útiles
CREATE INDEX IF NOT EXISTS idx_paciente_documento ON paciente(documento_id);
CREATE INDEX IF NOT EXISTS idx_observacion_doc_fecha ON observacion(documento_id, fecha);
