-- 02-schema-fhir.sql
-- Esquema FHIR (Fast Healthcare Interoperability Resources)
-- Diseñado para distribuir por documento_id (agrupando datos de cada paciente)
-- IMPORTANTE: Las PKs deben incluir la columna de distribución en Citus

\c hce_distribuida

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

-- ============================================================================
-- RECURSOS ADMINISTRATIVOS Y DE FLUJO DE TRABAJO FHIR
-- ============================================================================

-- Tabla de organizaciones (replicada - tabla de referencia)
CREATE TABLE IF NOT EXISTS organizacion (
  organizacion_id BIGSERIAL PRIMARY KEY,
  nombre TEXT NOT NULL,
  tipo TEXT,
  direccion TEXT,
  telefono TEXT,
  email TEXT,
  sitio_web TEXT,
  activa BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Tabla de ubicaciones (replicada - tabla de referencia)
CREATE TABLE IF NOT EXISTS ubicacion (
  ubicacion_id BIGSERIAL PRIMARY KEY,
  nombre TEXT NOT NULL,
  tipo TEXT,
  direccion TEXT,
  latitud DECIMAL(10,8),
  longitud DECIMAL(11,8),
  organizacion_id BIGINT,
  activa BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Tabla de horarios de atención (replicada)
CREATE TABLE IF NOT EXISTS horario_atencion (
  horario_id BIGSERIAL PRIMARY KEY,
  ubicacion_id BIGINT,
  dia_semana INTEGER, -- 0=domingo, 1=lunes, etc.
  hora_inicio TIME,
  hora_fin TIME,
  disponible BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Tabla de citas/appointments (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS cita (
  cita_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  profesional_id BIGINT,
  fecha_hora TIMESTAMP WITH TIME ZONE,
  duracion_minutos INTEGER DEFAULT 30,
  estado TEXT DEFAULT 'programada', -- programada, confirmada, cancelada, completada
  tipo_cita TEXT,
  motivo TEXT,
  ubicacion_id BIGINT,
  notas TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, cita_id)
);

-- ============================================================================
-- RECURSOS CLÍNICOS ESPECÍFICOS FHIR
-- ============================================================================

-- Tabla de alergias e intolerancias (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS alergia_intolerancia (
  alergia_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  tipo TEXT, -- alergia, intolerancia
  categoria TEXT, -- comida, medicamento, ambiente, biológico
  codigo_sustancia TEXT,
  descripcion_sustancia TEXT NOT NULL,
  severidad TEXT, -- leve, moderada, severa
  manifestacion TEXT,
  fecha_inicio DATE,
  estado TEXT DEFAULT 'activa', -- activa, inactiva, resuelta
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, alergia_id)
);

-- Tabla de medicamentos (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS medicamento (
  medicamento_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  codigo_medicamento TEXT,
  nombre_medicamento TEXT NOT NULL,
  dosis TEXT,
  via_administracion TEXT,
  frecuencia TEXT,
  fecha_inicio DATE,
  fecha_fin DATE,
  prescriptor_id BIGINT,
  estado TEXT DEFAULT 'activo', -- activo, suspendido, completado
  notas TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, medicamento_id)
);

-- Tabla de inmunizaciones/vacunas (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS inmunizacion (
  inmunizacion_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  codigo_vacuna TEXT,
  nombre_vacuna TEXT NOT NULL,
  fecha_administracion DATE,
  dosis INTEGER,
  lote TEXT,
  fabricante TEXT,
  sitio_administracion TEXT,
  profesional_id BIGINT,
  reaccion_adversa TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, inmunizacion_id)
);

-- Tabla de procedimientos (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS procedimiento (
  procedimiento_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  codigo_procedimiento TEXT,
  descripcion TEXT NOT NULL,
  fecha TIMESTAMP WITH TIME ZONE,
  estado TEXT DEFAULT 'completado', -- programado, en-progreso, completado, cancelado
  profesional_id BIGINT,
  ubicacion_id BIGINT,
  encuentro_id BIGINT,
  resultado TEXT,
  complicaciones TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, procedimiento_id)
);

-- Tabla de resultados de laboratorio (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS resultado_laboratorio (
  resultado_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  codigo_examen TEXT,
  nombre_examen TEXT NOT NULL,
  valor_numerico DECIMAL(15,6),
  valor_texto TEXT,
  unidad TEXT,
  rango_referencia TEXT,
  estado TEXT DEFAULT 'final', -- preliminar, final, corregido
  fecha_muestra TIMESTAMP WITH TIME ZONE,
  fecha_resultado TIMESTAMP WITH TIME ZONE,
  profesional_id BIGINT,
  laboratorio TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, resultado_id)
);

-- Tabla de estudios de imagen (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS estudio_imagen (
  estudio_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  tipo_estudio TEXT NOT NULL, -- radiografia, tomografia, resonancia, etc.
  codigo_estudio TEXT,
  fecha TIMESTAMP WITH TIME ZONE,
  estado TEXT DEFAULT 'completado',
  profesional_solicitante_id BIGINT,
  profesional_interprete_id BIGINT,
  hallazgos TEXT,
  impresion_diagnostica TEXT,
  archivo_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, estudio_id)
);

-- ============================================================================
-- RECURSOS DE ATENCIÓN ESPECIALIZADA FHIR
-- ============================================================================

-- Tabla de signos vitales (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS signos_vitales (
  signo_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  encuentro_id BIGINT,
  fecha TIMESTAMP WITH TIME ZONE DEFAULT now(),
  presion_sistolica INTEGER,
  presion_diastolica INTEGER,
  frecuencia_cardiaca INTEGER,
  frecuencia_respiratoria INTEGER,
  temperatura DECIMAL(4,2),
  saturacion_oxigeno INTEGER,
  peso DECIMAL(6,2),
  talla INTEGER, -- en centímetros
  imc DECIMAL(5,2),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, signo_id)
);

-- Tabla de planes de cuidado (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS plan_cuidado (
  plan_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  titulo TEXT NOT NULL,
  descripcion TEXT,
  fecha_inicio DATE,
  fecha_fin DATE,
  estado TEXT DEFAULT 'activo', -- activo, completado, cancelado
  profesional_id BIGINT,
  categoria TEXT, -- tratamiento, prevencion, rehabilitacion
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, plan_id)
);

-- Tabla de objetivos del plan de cuidado (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS objetivo_cuidado (
  objetivo_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  plan_id BIGINT NOT NULL,
  descripcion TEXT NOT NULL,
  fecha_meta DATE,
  estado TEXT DEFAULT 'propuesto', -- propuesto, aceptado, rechazado, alcanzado
  prioridad TEXT, -- alta, media, baja
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, objetivo_id)
);

-- Tabla de episodios de cuidado (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS episodio_cuidado (
  episodio_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  titulo TEXT NOT NULL,
  descripcion TEXT,
  estado TEXT DEFAULT 'activo', -- planificado, activo, pausa, completado, cancelado
  fecha_inicio DATE,
  fecha_fin DATE,
  profesional_responsable_id BIGINT,
  organizacion_id BIGINT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, episodio_id)
);

-- ============================================================================
-- RECURSOS DE ATENCIÓN ESPECIALIZADA ADICIONALES
-- ============================================================================

-- Tabla de dispositivos médicos (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS dispositivo_medico (
  dispositivo_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  codigo_dispositivo TEXT,
  nombre_dispositivo TEXT NOT NULL,
  tipo TEXT,
  fabricante TEXT,
  modelo TEXT,
  numero_serie TEXT,
  fecha_implantacion DATE,
  fecha_retiro DATE,
  estado TEXT DEFAULT 'activo', -- activo, inactivo, retirado
  profesional_id BIGINT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, dispositivo_id)
);

-- Tabla de comunicaciones (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS comunicacion (
  comunicacion_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT,
  remitente_id BIGINT,
  destinatario_id BIGINT,
  fecha TIMESTAMP WITH TIME ZONE DEFAULT now(),
  tipo TEXT, -- email, sms, carta, llamada
  asunto TEXT,
  contenido TEXT,
  estado TEXT DEFAULT 'enviado', -- borrador, enviado, recibido, leido
  prioridad TEXT DEFAULT 'normal', -- baja, normal, alta, urgente
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, comunicacion_id)
);

-- Tabla de consentimientos (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS consentimiento (
  consentimiento_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  tipo TEXT NOT NULL, -- tratamiento, investigacion, intercambio-datos
  descripcion TEXT,
  fecha_consentimiento TIMESTAMP WITH TIME ZONE,
  fecha_expiracion DATE,
  estado TEXT DEFAULT 'activo', -- activo, revocado, expirado
  profesional_id BIGINT,
  documento_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, consentimiento_id)
);

-- Tabla de facturas/cuentas (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS factura (
  factura_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  numero_factura TEXT,
  fecha_emision DATE,
  fecha_vencimiento DATE,
  monto_total DECIMAL(12,2),
  monto_pagado DECIMAL(12,2) DEFAULT 0,
  estado TEXT DEFAULT 'pendiente', -- pendiente, pagada, vencida, cancelada
  organizacion_id BIGINT,
  tipo_servicio TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, factura_id)
);

-- Tabla de detalle de factura (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS detalle_factura (
  detalle_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  factura_id BIGINT NOT NULL,
  codigo_servicio TEXT,
  descripcion TEXT NOT NULL,
  cantidad INTEGER DEFAULT 1,
  precio_unitario DECIMAL(12,2),
  subtotal DECIMAL(12,2),
  fecha_servicio DATE,
  profesional_id BIGINT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, detalle_id)
);

-- ============================================================================
-- RECURSOS DE POBLACIONES Y EPIDEMIOLOGÍA
-- ============================================================================

-- Tabla de grupos de pacientes (replicada - tabla de referencia)
CREATE TABLE IF NOT EXISTS grupo_pacientes (
  grupo_id BIGSERIAL PRIMARY KEY,
  nombre TEXT NOT NULL,
  descripcion TEXT,
  tipo TEXT, -- cohorte, familia, equipo-cuidado
  caracteristicas JSONB,
  activo BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Tabla de membresía de grupos (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS membresia_grupo (
  membresia_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  grupo_id BIGINT NOT NULL,
  fecha_ingreso DATE,
  fecha_salida DATE,
  estado TEXT DEFAULT 'activo', -- activo, inactivo
  rol TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, membresia_id)
);

-- Tabla de medidas de salud pública (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS medida_salud_publica (
  medida_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT,
  tipo_medida TEXT NOT NULL, -- vigilancia, prevencion, control-brote
  codigo_evento TEXT,
  descripcion TEXT,
  fecha_evento DATE,
  fecha_notificacion DATE,
  estado TEXT DEFAULT 'activo',
  autoridad_sanitaria TEXT,
  profesional_id BIGINT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, medida_id)
);

-- ============================================================================
-- RECURSOS DE INVESTIGACIÓN Y ESTUDIOS CLÍNICOS
-- ============================================================================

-- Tabla de estudios de investigación (replicada - tabla de referencia)
CREATE TABLE IF NOT EXISTS estudio_investigacion (
  estudio_id BIGSERIAL PRIMARY KEY,
  titulo TEXT NOT NULL,
  descripcion TEXT,
  protocolo TEXT,
  investigador_principal TEXT,
  fecha_inicio DATE,
  fecha_fin DATE,
  estado TEXT DEFAULT 'activo', -- planificado, activo, suspendido, completado
  fase TEXT, -- I, II, III, IV
  tipo TEXT, -- observacional, intervencionista
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Tabla de participación en estudios (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS participacion_estudio (
  participacion_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  estudio_id BIGINT NOT NULL,
  fecha_ingreso DATE,
  fecha_salida DATE,
  estado TEXT DEFAULT 'activo', -- activo, completado, retirado
  grupo_tratamiento TEXT,
  consentimiento_firmado BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, participacion_id)
);

-- ============================================================================
-- RECURSOS DE CALIDAD Y MÉTRICAS
-- ============================================================================

-- Tabla de medidas de calidad (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS medida_calidad (
  medida_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT,
  tipo_medida TEXT NOT NULL,
  codigo_medida TEXT,
  descripcion TEXT,
  valor_medido DECIMAL(15,6),
  valor_objetivo DECIMAL(15,6),
  fecha_medicion DATE,
  periodo_reporte TEXT,
  estado TEXT DEFAULT 'completo',
  profesional_id BIGINT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, medida_id)
);

-- Tabla de eventos adversos (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS evento_adverso (
  evento_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  descripcion TEXT NOT NULL,
  fecha_evento TIMESTAMP WITH TIME ZONE,
  severidad TEXT, -- leve, moderado, severo, mortal
  causalidad TEXT, -- no-relacionado, posible, probable, definitivo
  estado TEXT DEFAULT 'reportado', -- reportado, en-investigacion, cerrado
  medicamento_sospechoso TEXT,
  profesional_reporta_id BIGINT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, evento_id)
);

-- ============================================================================
-- RECURSOS DE TERMINOLOGÍA Y CODIFICACIÓN
-- ============================================================================

-- Tabla de conceptos de terminología (replicada - tabla de referencia)
CREATE TABLE IF NOT EXISTS concepto_terminologia (
  concepto_id BIGSERIAL PRIMARY KEY,
  sistema_codificacion TEXT NOT NULL, -- SNOMED-CT, ICD-10, LOINC, etc.
  codigo TEXT NOT NULL,
  descripcion TEXT NOT NULL,
  definicion TEXT,
  estado TEXT DEFAULT 'activo', -- activo, inactivo, deprecado
  fecha_creacion DATE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  UNIQUE(sistema_codificacion, codigo)
);

-- Tabla de mapeos entre terminologías (replicada)
CREATE TABLE IF NOT EXISTS mapeo_terminologia (
  mapeo_id BIGSERIAL PRIMARY KEY,
  concepto_origen_id BIGINT NOT NULL,
  concepto_destino_id BIGINT NOT NULL,
  tipo_mapeo TEXT, -- equivalente, mas-amplio, mas-especifico, relacionado
  confianza DECIMAL(3,2), -- 0.00 a 1.00
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- ============================================================================
-- RECURSOS DE FLUJO DE TRABAJO Y TAREAS
-- ============================================================================

-- Tabla de tareas (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS tarea (
  tarea_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT,
  titulo TEXT NOT NULL,
  descripcion TEXT,
  estado TEXT DEFAULT 'solicitada', -- solicitada, aceptada, en-progreso, completada, cancelada
  prioridad TEXT DEFAULT 'normal', -- baja, normal, alta, urgente
  fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT now(),
  fecha_vencimiento TIMESTAMP WITH TIME ZONE,
  asignado_a_id BIGINT,
  creado_por_id BIGINT,
  tipo_tarea TEXT,
  entrada JSONB, -- datos de entrada para la tarea
  salida JSONB, -- resultados de la tarea
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, tarea_id)
);

-- Tabla de recursos adicionales específicos del dominio médico
-- Tabla de historia familiar (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS historia_familiar (
  historia_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  relacion_familiar TEXT NOT NULL, -- padre, madre, hermano, etc.
  condicion TEXT NOT NULL,
  codigo_condicion TEXT,
  edad_diagnostico INTEGER,
  estado_vital TEXT, -- vivo, fallecido, desconocido
  causa_muerte TEXT,
  notas TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, historia_id)
);

-- Tabla de riesgos del paciente (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS riesgo_paciente (
  riesgo_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  tipo_riesgo TEXT NOT NULL,
  codigo_riesgo TEXT,
  descripcion TEXT,
  probabilidad TEXT, -- alta, media, baja
  fecha_identificacion DATE,
  fecha_mitigacion DATE,
  estado TEXT DEFAULT 'activo', -- activo, mitigado, resuelto
  medidas_preventivas TEXT,
  profesional_id BIGINT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, riesgo_id)
);

-- Tabla de cuidados (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS cuidado (
  cuidado_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  tipo_cuidado TEXT NOT NULL,
  descripcion TEXT,
  fecha TIMESTAMP WITH TIME ZONE,
  duracion_minutos INTEGER,
  profesional_id BIGINT,
  ubicacion_id BIGINT,
  estado TEXT DEFAULT 'completado',
  notas TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, cuidado_id)
);

-- Tabla de guías clínicas (replicada - tabla de referencia)
CREATE TABLE IF NOT EXISTS guia_clinica (
  guia_id BIGSERIAL PRIMARY KEY,
  titulo TEXT NOT NULL,
  descripcion TEXT,
  version TEXT,
  fecha_publicacion DATE,
  organizacion_emisora TEXT,
  especialidad TEXT,
  estado TEXT DEFAULT 'activa', -- borrador, activa, retirada
  contenido JSONB, -- contenido estructurado de la guía
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Tabla de adherencia a guías (distribuida por documento_id)
CREATE TABLE IF NOT EXISTS adherencia_guia (
  adherencia_id BIGSERIAL,
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  guia_id BIGINT NOT NULL,
  encuentro_id BIGINT,
  recomendacion TEXT,
  cumplida BOOLEAN,
  justificacion_no_cumplimiento TEXT,
  fecha_evaluacion DATE,
  profesional_id BIGINT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (documento_id, adherencia_id)
);

-- ============================================================================
-- SISTEMA DE ADMISIÓN Y TRIAGE DE PACIENTES
-- ============================================================================

-- Tabla de admisiones con datos de triage
-- Esta tabla registra la admisión de pacientes y sus signos vitales iniciales
CREATE TABLE IF NOT EXISTS admision (
  admission_id TEXT NOT NULL,  -- Código único de admisión (ej: ADM-20241112-0001)
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  cita_id BIGINT,  -- Relación con la cita si existe
  
  -- Información de admisión
  fecha_admision TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  admitido_por TEXT,  -- Username del usuario que realizó la admisión
  motivo_consulta TEXT,
  prioridad TEXT DEFAULT 'normal',  -- urgente, normal, baja
  estado_admision TEXT DEFAULT 'activa',  -- activa, atendida, cancelada
  
  -- Datos de Triage (Signos Vitales)
  presion_arterial_sistolica INTEGER,  -- mmHg
  presion_arterial_diastolica INTEGER,  -- mmHg
  frecuencia_cardiaca INTEGER,  -- latidos por minuto
  frecuencia_respiratoria INTEGER,  -- respiraciones por minuto
  temperatura DECIMAL(4,2),  -- Grados Celsius
  saturacion_oxigeno INTEGER,  -- Porcentaje (0-100)
  peso DECIMAL(5,2),  -- Kilogramos
  altura INTEGER,  -- Centímetros
  
  -- Información adicional de triage
  nivel_dolor INTEGER,  -- Escala 0-10
  nivel_conciencia TEXT,  -- alerta, somnoliento, confuso, inconsciente
  sintomas_principales TEXT,
  alergias_conocidas TEXT,
  medicamentos_actuales TEXT,
  
  -- Notas y observaciones
  notas_enfermeria TEXT,
  observaciones TEXT,
  
  -- Auditoría
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Primary Key compuesta (requerida por Citus)
  PRIMARY KEY (documento_id, admission_id)
);

-- Agregar campos para gestión de admisión en tabla de citas
ALTER TABLE cita ADD COLUMN IF NOT EXISTS admission_id TEXT;
ALTER TABLE cita ADD COLUMN IF NOT EXISTS estado_admision TEXT DEFAULT 'pendiente';
ALTER TABLE cita ADD COLUMN IF NOT EXISTS fecha_admision TIMESTAMP WITH TIME ZONE;
ALTER TABLE cita ADD COLUMN IF NOT EXISTS admitido_por TEXT;

-- Convertir tablas a distribuidas/replicadas en Citus
-- NOTA: Las tablas deben existir ANTES de distribuirlas

-- ============================================================================
-- TABLAS DISTRIBUIDAS POR documento_id (co-location para queries eficientes)
-- ============================================================================
SELECT create_distributed_table('paciente', 'documento_id');
SELECT create_distributed_table('encuentro', 'documento_id');
SELECT create_distributed_table('observacion', 'documento_id');
SELECT create_distributed_table('condicion', 'documento_id');
SELECT create_distributed_table('cita', 'documento_id');
SELECT create_distributed_table('alergia_intolerancia', 'documento_id');
SELECT create_distributed_table('medicamento', 'documento_id');
SELECT create_distributed_table('inmunizacion', 'documento_id');
SELECT create_distributed_table('procedimiento', 'documento_id');
SELECT create_distributed_table('resultado_laboratorio', 'documento_id');
SELECT create_distributed_table('estudio_imagen', 'documento_id');
SELECT create_distributed_table('signos_vitales', 'documento_id');
SELECT create_distributed_table('plan_cuidado', 'documento_id');
SELECT create_distributed_table('objetivo_cuidado', 'documento_id');
SELECT create_distributed_table('episodio_cuidado', 'documento_id');
SELECT create_distributed_table('dispositivo_medico', 'documento_id');
SELECT create_distributed_table('comunicacion', 'documento_id');
SELECT create_distributed_table('consentimiento', 'documento_id');
SELECT create_distributed_table('factura', 'documento_id');
SELECT create_distributed_table('detalle_factura', 'documento_id');
SELECT create_distributed_table('membresia_grupo', 'documento_id');
SELECT create_distributed_table('medida_salud_publica', 'documento_id');
SELECT create_distributed_table('participacion_estudio', 'documento_id');
SELECT create_distributed_table('medida_calidad', 'documento_id');
SELECT create_distributed_table('evento_adverso', 'documento_id');
SELECT create_distributed_table('tarea', 'documento_id');
SELECT create_distributed_table('historia_familiar', 'documento_id');
SELECT create_distributed_table('riesgo_paciente', 'documento_id');
SELECT create_distributed_table('cuidado', 'documento_id');
SELECT create_distributed_table('adherencia_guia', 'documento_id');
SELECT create_distributed_table('admision', 'documento_id');

-- ============================================================================
-- TABLAS DE REFERENCIA (replicadas en todos los workers)
-- ============================================================================
SELECT create_reference_table('profesional');
SELECT create_reference_table('organizacion');
SELECT create_reference_table('ubicacion');
SELECT create_reference_table('horario_atencion');
SELECT create_reference_table('grupo_pacientes');
SELECT create_reference_table('estudio_investigacion');
SELECT create_reference_table('concepto_terminologia');
SELECT create_reference_table('mapeo_terminologia');
SELECT create_reference_table('guia_clinica');

-- ============================================================================
-- ÍNDICES PARA OPTIMIZAR CONSULTAS COMUNES
-- ============================================================================

-- Índices en tablas principales
CREATE INDEX IF NOT EXISTS idx_paciente_nombre ON paciente(nombre, apellido);
CREATE INDEX IF NOT EXISTS idx_observacion_fecha ON observacion(fecha);
CREATE INDEX IF NOT EXISTS idx_observacion_tipo ON observacion(tipo);
CREATE INDEX IF NOT EXISTS idx_encuentro_fecha ON encuentro(fecha);
CREATE INDEX IF NOT EXISTS idx_condicion_fecha ON condicion(fecha_inicio);

-- Índices para citas y programación
CREATE INDEX IF NOT EXISTS idx_cita_fecha ON cita(fecha_hora);
CREATE INDEX IF NOT EXISTS idx_cita_estado ON cita(estado);
CREATE INDEX IF NOT EXISTS idx_cita_profesional ON cita(profesional_id);
CREATE INDEX IF NOT EXISTS idx_cita_admission ON cita(documento_id, admission_id);
CREATE INDEX IF NOT EXISTS idx_cita_estado_admision ON cita(estado_admision);
CREATE INDEX IF NOT EXISTS idx_cita_pendientes ON cita(estado_admision, fecha_hora) WHERE estado_admision = 'pendiente';

-- Índices para admisiones
CREATE INDEX IF NOT EXISTS idx_admision_fecha ON admision(fecha_admision);
CREATE INDEX IF NOT EXISTS idx_admision_paciente ON admision(documento_id, paciente_id);
CREATE INDEX IF NOT EXISTS idx_admision_cita ON admision(documento_id, cita_id);
CREATE INDEX IF NOT EXISTS idx_admision_estado ON admision(estado_admision);
CREATE INDEX IF NOT EXISTS idx_admision_prioridad ON admision(prioridad);
CREATE INDEX IF NOT EXISTS idx_admision_admitido_por ON admision(admitido_por);
CREATE INDEX IF NOT EXISTS idx_admision_codigo ON admision(admission_id);

-- Índices para medicamentos y alergias
CREATE INDEX IF NOT EXISTS idx_medicamento_fecha ON medicamento(fecha_inicio);
CREATE INDEX IF NOT EXISTS idx_medicamento_estado ON medicamento(estado);
CREATE INDEX IF NOT EXISTS idx_alergia_tipo ON alergia_intolerancia(tipo);
CREATE INDEX IF NOT EXISTS idx_alergia_categoria ON alergia_intolerancia(categoria);

-- Índices para procedimientos y resultados
CREATE INDEX IF NOT EXISTS idx_procedimiento_fecha ON procedimiento(fecha);
CREATE INDEX IF NOT EXISTS idx_procedimiento_codigo ON procedimiento(codigo_procedimiento);
CREATE INDEX IF NOT EXISTS idx_resultado_lab_fecha ON resultado_laboratorio(fecha_resultado);
CREATE INDEX IF NOT EXISTS idx_resultado_lab_examen ON resultado_laboratorio(codigo_examen);

-- Índices para estudios de imagen
CREATE INDEX IF NOT EXISTS idx_estudio_imagen_fecha ON estudio_imagen(fecha);
CREATE INDEX IF NOT EXISTS idx_estudio_imagen_tipo ON estudio_imagen(tipo_estudio);

-- Índices para signos vitales
CREATE INDEX IF NOT EXISTS idx_signos_vitales_fecha ON signos_vitales(fecha);
CREATE INDEX IF NOT EXISTS idx_signos_vitales_encuentro ON signos_vitales(encuentro_id);

-- Índices para planes de cuidado
CREATE INDEX IF NOT EXISTS idx_plan_cuidado_fecha ON plan_cuidado(fecha_inicio);
CREATE INDEX IF NOT EXISTS idx_plan_cuidado_estado ON plan_cuidado(estado);

-- Índices para comunicaciones y tareas
CREATE INDEX IF NOT EXISTS idx_comunicacion_fecha ON comunicacion(fecha);
CREATE INDEX IF NOT EXISTS idx_comunicacion_tipo ON comunicacion(tipo);
CREATE INDEX IF NOT EXISTS idx_tarea_estado ON tarea(estado);
CREATE INDEX IF NOT EXISTS idx_tarea_prioridad ON tarea(prioridad);
CREATE INDEX IF NOT EXISTS idx_tarea_asignado ON tarea(asignado_a_id);

-- Índices para facturación
CREATE INDEX IF NOT EXISTS idx_factura_fecha ON factura(fecha_emision);
CREATE INDEX IF NOT EXISTS idx_factura_estado ON factura(estado);
CREATE INDEX IF NOT EXISTS idx_factura_paciente ON factura(paciente_id);

-- Índices para estudios de investigación
CREATE INDEX IF NOT EXISTS idx_participacion_estudio ON participacion_estudio(estudio_id);
CREATE INDEX IF NOT EXISTS idx_participacion_fecha ON participacion_estudio(fecha_ingreso);

-- Índices para eventos adversos
CREATE INDEX IF NOT EXISTS idx_evento_adverso_fecha ON evento_adverso(fecha_evento);
CREATE INDEX IF NOT EXISTS idx_evento_adverso_severidad ON evento_adverso(severidad);

-- Índices para terminologías
CREATE INDEX IF NOT EXISTS idx_concepto_sistema ON concepto_terminologia(sistema_codificacion);
CREATE INDEX IF NOT EXISTS idx_concepto_codigo ON concepto_terminologia(codigo);

-- Índices para tablas de referencia
CREATE INDEX IF NOT EXISTS idx_organizacion_nombre ON organizacion(nombre);
CREATE INDEX IF NOT EXISTS idx_ubicacion_organizacion ON ubicacion(organizacion_id);
CREATE INDEX IF NOT EXISTS idx_profesional_especialidad ON profesional(especialidad);

-- Índices compuestos para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_paciente_documento_fecha ON paciente(documento_id, created_at);
CREATE INDEX IF NOT EXISTS idx_encuentro_paciente_fecha ON encuentro(paciente_id, fecha);
CREATE INDEX IF NOT EXISTS idx_medicamento_paciente_activo ON medicamento(paciente_id, estado) WHERE estado = 'activo';
CREATE INDEX IF NOT EXISTS idx_cita_profesional_fecha ON cita(profesional_id, fecha_hora);

-- Índices para búsquedas de texto (usando extensiones de PostgreSQL)
-- CREATE INDEX IF NOT EXISTS idx_paciente_texto ON paciente USING gin(to_tsvector('spanish', nombre || ' ' || apellido));
-- CREATE INDEX IF NOT EXISTS idx_medicamento_texto ON medicamento USING gin(to_tsvector('spanish', nombre_medicamento));
-- CREATE INDEX IF NOT EXISTS idx_procedimiento_texto ON procedimiento USING gin(to_tsvector('spanish', descripcion));

-- ============================================================================
-- RELACIONES Y FOREIGN KEYS
-- ============================================================================
-- NOTA: En Citus, las foreign keys entre tablas distribuidas solo son posibles
-- si ambas tablas están distribuidas por la misma columna y co-localizadas.
-- Las referencias a tablas de referencia son siempre permitidas.

-- ============================================================================
-- RELACIONES DESDE TABLAS DISTRIBUIDAS A TABLAS DE REFERENCIA
-- ============================================================================

-- Relaciones con profesional (tabla de referencia)
ALTER TABLE encuentro ADD CONSTRAINT fk_encuentro_profesional 
  FOREIGN KEY (profesional_id) REFERENCES profesional(profesional_id);

ALTER TABLE medicamento ADD CONSTRAINT fk_medicamento_prescriptor 
  FOREIGN KEY (prescriptor_id) REFERENCES profesional(profesional_id);

ALTER TABLE inmunizacion ADD CONSTRAINT fk_inmunizacion_profesional 
  FOREIGN KEY (profesional_id) REFERENCES profesional(profesional_id);

ALTER TABLE procedimiento ADD CONSTRAINT fk_procedimiento_profesional 
  FOREIGN KEY (profesional_id) REFERENCES profesional(profesional_id);

ALTER TABLE resultado_laboratorio ADD CONSTRAINT fk_resultado_profesional 
  FOREIGN KEY (profesional_id) REFERENCES profesional(profesional_id);

ALTER TABLE estudio_imagen ADD CONSTRAINT fk_estudio_solicitante 
  FOREIGN KEY (profesional_solicitante_id) REFERENCES profesional(profesional_id);

ALTER TABLE estudio_imagen ADD CONSTRAINT fk_estudio_interprete 
  FOREIGN KEY (profesional_interprete_id) REFERENCES profesional(profesional_id);

ALTER TABLE plan_cuidado ADD CONSTRAINT fk_plan_profesional 
  FOREIGN KEY (profesional_id) REFERENCES profesional(profesional_id);

ALTER TABLE episodio_cuidado ADD CONSTRAINT fk_episodio_profesional 
  FOREIGN KEY (profesional_responsable_id) REFERENCES profesional(profesional_id);

ALTER TABLE dispositivo_medico ADD CONSTRAINT fk_dispositivo_profesional 
  FOREIGN KEY (profesional_id) REFERENCES profesional(profesional_id);

ALTER TABLE consentimiento ADD CONSTRAINT fk_consentimiento_profesional 
  FOREIGN KEY (profesional_id) REFERENCES profesional(profesional_id);

ALTER TABLE medida_salud_publica ADD CONSTRAINT fk_medida_profesional 
  FOREIGN KEY (profesional_id) REFERENCES profesional(profesional_id);

ALTER TABLE medida_calidad ADD CONSTRAINT fk_medida_profesional 
  FOREIGN KEY (profesional_id) REFERENCES profesional(profesional_id);

ALTER TABLE evento_adverso ADD CONSTRAINT fk_evento_profesional 
  FOREIGN KEY (profesional_reporta_id) REFERENCES profesional(profesional_id);

ALTER TABLE riesgo_paciente ADD CONSTRAINT fk_riesgo_profesional 
  FOREIGN KEY (profesional_id) REFERENCES profesional(profesional_id);

ALTER TABLE cuidado ADD CONSTRAINT fk_cuidado_profesional 
  FOREIGN KEY (profesional_id) REFERENCES profesional(profesional_id);

ALTER TABLE adherencia_guia ADD CONSTRAINT fk_adherencia_profesional 
  FOREIGN KEY (profesional_id) REFERENCES profesional(profesional_id);

-- Relaciones con organizacion (tabla de referencia)
ALTER TABLE ubicacion ADD CONSTRAINT fk_ubicacion_organizacion 
  FOREIGN KEY (organizacion_id) REFERENCES organizacion(organizacion_id);

ALTER TABLE cita ADD CONSTRAINT fk_cita_profesional 
  FOREIGN KEY (profesional_id) REFERENCES profesional(profesional_id);

ALTER TABLE episodio_cuidado ADD CONSTRAINT fk_episodio_organizacion 
  FOREIGN KEY (organizacion_id) REFERENCES organizacion(organizacion_id);

ALTER TABLE factura ADD CONSTRAINT fk_factura_organizacion 
  FOREIGN KEY (organizacion_id) REFERENCES organizacion(organizacion_id);

-- Relaciones con ubicacion (tabla de referencia)
ALTER TABLE horario_atencion ADD CONSTRAINT fk_horario_ubicacion 
  FOREIGN KEY (ubicacion_id) REFERENCES ubicacion(ubicacion_id);

ALTER TABLE cita ADD CONSTRAINT fk_cita_ubicacion 
  FOREIGN KEY (ubicacion_id) REFERENCES ubicacion(ubicacion_id);

ALTER TABLE procedimiento ADD CONSTRAINT fk_procedimiento_ubicacion 
  FOREIGN KEY (ubicacion_id) REFERENCES ubicacion(ubicacion_id);

ALTER TABLE cuidado ADD CONSTRAINT fk_cuidado_ubicacion 
  FOREIGN KEY (ubicacion_id) REFERENCES ubicacion(ubicacion_id);

-- Relaciones con estudio_investigacion (tabla de referencia)
ALTER TABLE participacion_estudio ADD CONSTRAINT fk_participacion_estudio 
  FOREIGN KEY (estudio_id) REFERENCES estudio_investigacion(estudio_id);

-- Relaciones con grupo_pacientes (tabla de referencia)
ALTER TABLE membresia_grupo ADD CONSTRAINT fk_membresia_grupo 
  FOREIGN KEY (grupo_id) REFERENCES grupo_pacientes(grupo_id);

-- Relaciones con guia_clinica (tabla de referencia)
ALTER TABLE adherencia_guia ADD CONSTRAINT fk_adherencia_guia 
  FOREIGN KEY (guia_id) REFERENCES guia_clinica(guia_id);

-- Relaciones con concepto_terminologia (tabla de referencia)
ALTER TABLE mapeo_terminologia ADD CONSTRAINT fk_mapeo_origen 
  FOREIGN KEY (concepto_origen_id) REFERENCES concepto_terminologia(concepto_id);

ALTER TABLE mapeo_terminologia ADD CONSTRAINT fk_mapeo_destino 
  FOREIGN KEY (concepto_destino_id) REFERENCES concepto_terminologia(concepto_id);

-- ============================================================================
-- RELACIONES ENTRE TABLAS DISTRIBUIDAS (CO-LOCALIZADAS POR documento_id)
-- ============================================================================
-- NOTA: Estas relaciones son posibles porque ambas tablas están distribuidas
-- por documento_id y están co-localizadas en los mismos shards.

-- Relaciones con paciente
ALTER TABLE encuentro ADD CONSTRAINT fk_encuentro_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE observacion ADD CONSTRAINT fk_observacion_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE condicion ADD CONSTRAINT fk_condicion_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE cita ADD CONSTRAINT fk_cita_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE alergia_intolerancia ADD CONSTRAINT fk_alergia_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE medicamento ADD CONSTRAINT fk_medicamento_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE inmunizacion ADD CONSTRAINT fk_inmunizacion_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE procedimiento ADD CONSTRAINT fk_procedimiento_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE resultado_laboratorio ADD CONSTRAINT fk_resultado_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE estudio_imagen ADD CONSTRAINT fk_estudio_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE signos_vitales ADD CONSTRAINT fk_signos_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE plan_cuidado ADD CONSTRAINT fk_plan_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE episodio_cuidado ADD CONSTRAINT fk_episodio_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE dispositivo_medico ADD CONSTRAINT fk_dispositivo_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE consentimiento ADD CONSTRAINT fk_consentimiento_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE factura ADD CONSTRAINT fk_factura_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE membresia_grupo ADD CONSTRAINT fk_membresia_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE participacion_estudio ADD CONSTRAINT fk_participacion_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE evento_adverso ADD CONSTRAINT fk_evento_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE historia_familiar ADD CONSTRAINT fk_historia_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE riesgo_paciente ADD CONSTRAINT fk_riesgo_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE cuidado ADD CONSTRAINT fk_cuidado_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE adherencia_guia ADD CONSTRAINT fk_adherencia_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

-- Relaciones con encuentro
ALTER TABLE observacion ADD CONSTRAINT fk_observacion_encuentro 
  FOREIGN KEY (documento_id, referencia_encuentro) REFERENCES encuentro(documento_id, encuentro_id);

ALTER TABLE signos_vitales ADD CONSTRAINT fk_signos_encuentro 
  FOREIGN KEY (documento_id, encuentro_id) REFERENCES encuentro(documento_id, encuentro_id);

ALTER TABLE procedimiento ADD CONSTRAINT fk_procedimiento_encuentro 
  FOREIGN KEY (documento_id, encuentro_id) REFERENCES encuentro(documento_id, encuentro_id);

ALTER TABLE adherencia_guia ADD CONSTRAINT fk_adherencia_encuentro 
  FOREIGN KEY (documento_id, encuentro_id) REFERENCES encuentro(documento_id, encuentro_id);

-- Relaciones internas en plan de cuidado
ALTER TABLE objetivo_cuidado ADD CONSTRAINT fk_objetivo_plan 
  FOREIGN KEY (documento_id, plan_id) REFERENCES plan_cuidado(documento_id, plan_id);

-- Relaciones en facturación
ALTER TABLE detalle_factura ADD CONSTRAINT fk_detalle_factura 
  FOREIGN KEY (documento_id, factura_id) REFERENCES factura(documento_id, factura_id);

ALTER TABLE detalle_factura ADD CONSTRAINT fk_detalle_profesional 
  FOREIGN KEY (profesional_id) REFERENCES profesional(profesional_id);

-- Relaciones con comunicacion (auto-referencia para profesionales)
-- NOTA: Las comunicaciones pueden ser entre pacientes y profesionales o entre profesionales
-- Se manejan con IDs genéricos que pueden referenciar diferentes tipos de entidades

-- Relaciones con tarea (referencias flexibles)
-- Las tareas pueden ser asignadas a profesionales y pueden referenciar pacientes
ALTER TABLE tarea ADD CONSTRAINT fk_tarea_asignado 
  FOREIGN KEY (asignado_a_id) REFERENCES profesional(profesional_id);

ALTER TABLE tarea ADD CONSTRAINT fk_tarea_creador 
  FOREIGN KEY (creado_por_id) REFERENCES profesional(profesional_id);

-- Si la tarea está relacionada con un paciente específico
ALTER TABLE tarea ADD CONSTRAINT fk_tarea_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

-- Relaciones para medidas que pueden o no estar asociadas a un paciente específico
ALTER TABLE medida_calidad ADD CONSTRAINT fk_medida_calidad_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

ALTER TABLE medida_salud_publica ADD CONSTRAINT fk_medida_salud_paciente 
  FOREIGN KEY (documento_id, paciente_id) REFERENCES paciente(documento_id, paciente_id);

-- ============================================================================
-- COMENTARIOS SOBRE LIMITACIONES DE CITUS CON FOREIGN KEYS
-- ============================================================================
/*
LIMITACIONES IMPORTANTES EN CITUS:

1. Las foreign keys entre tablas distribuidas solo funcionan si:
   - Ambas tablas están distribuidas por la misma columna
   - Las tablas están co-localizadas
   - La foreign key incluye la columna de distribución

2. Las foreign keys desde tablas distribuidas a tablas de referencia siempre funcionan

3. Las foreign keys desde tablas de referencia a tablas distribuidas NO están permitidas

4. Para relaciones que no pueden implementarse con foreign keys en Citus:
   - Implementar validación a nivel de aplicación
   - Usar triggers para mantener integridad referencial
   - Considerar desnormalización controlada

5. Algunas relaciones opcionales pueden manejarse sin foreign keys estrictas:
   - comunicacion.remitente_id y destinatario_id (pueden ser pacientes o profesionales)
   - Ciertas referencias cruzadas entre diferentes entidades
*/

-- ============================================================================
-- CONSTRAINTS ADICIONALES PARA INTEGRIDAD DE DATOS
-- ============================================================================

-- Constraints de check para validar valores
ALTER TABLE paciente ADD CONSTRAINT chk_paciente_sexo 
  CHECK (sexo IN ('masculino', 'femenino', 'otro', 'desconocido'));

ALTER TABLE paciente ADD CONSTRAINT chk_paciente_fecha_nacimiento 
  CHECK (fecha_nacimiento <= CURRENT_DATE);

ALTER TABLE signos_vitales ADD CONSTRAINT chk_signos_presion 
  CHECK (presion_sistolica > 0 AND presion_diastolica > 0 AND presion_sistolica > presion_diastolica);

ALTER TABLE signos_vitales ADD CONSTRAINT chk_signos_frecuencias 
  CHECK (frecuencia_cardiaca > 0 AND frecuencia_respiratoria > 0);

ALTER TABLE signos_vitales ADD CONSTRAINT chk_signos_temperatura 
  CHECK (temperatura > 30.0 AND temperatura < 45.0);

ALTER TABLE signos_vitales ADD CONSTRAINT chk_signos_saturacion 
  CHECK (saturacion_oxigeno >= 0 AND saturacion_oxigeno <= 100);

ALTER TABLE signos_vitales ADD CONSTRAINT chk_signos_peso_talla 
  CHECK (peso > 0 AND talla > 0);

ALTER TABLE cita ADD CONSTRAINT chk_cita_estado 
  CHECK (estado IN ('programada', 'confirmada', 'en-curso', 'completada', 'cancelada', 'no-asistio'));

ALTER TABLE cita ADD CONSTRAINT chk_cita_duracion 
  CHECK (duracion_minutos > 0 AND duracion_minutos <= 480); -- máximo 8 horas

ALTER TABLE cita ADD CONSTRAINT chk_cita_estado_admision 
  CHECK (estado_admision IN ('pendiente', 'admitida', 'cancelada'));

-- Constraints para tabla de admisiones
ALTER TABLE admision ADD CONSTRAINT chk_admision_prioridad 
  CHECK (prioridad IN ('urgente', 'normal', 'baja'));

ALTER TABLE admision ADD CONSTRAINT chk_admision_estado 
  CHECK (estado_admision IN ('activa', 'atendida', 'cancelada'));

ALTER TABLE admision ADD CONSTRAINT chk_admision_nivel_dolor 
  CHECK (nivel_dolor >= 0 AND nivel_dolor <= 10);

ALTER TABLE admision ADD CONSTRAINT chk_admision_saturacion 
  CHECK (saturacion_oxigeno >= 0 AND saturacion_oxigeno <= 100);

ALTER TABLE admision ADD CONSTRAINT chk_admision_temperatura 
  CHECK (temperatura > 30 AND temperatura < 45);

ALTER TABLE admision ADD CONSTRAINT chk_admision_presion 
  CHECK ((presion_arterial_sistolica IS NULL AND presion_arterial_diastolica IS NULL) OR 
         (presion_arterial_sistolica > presion_arterial_diastolica));

ALTER TABLE admision ADD CONSTRAINT chk_admision_nivel_conciencia 
  CHECK (nivel_conciencia IN ('alerta', 'somnoliento', 'confuso', 'inconsciente'));

ALTER TABLE medicamento ADD CONSTRAINT chk_medicamento_estado 
  CHECK (estado IN ('activo', 'suspendido', 'completado', 'cancelado'));

ALTER TABLE medicamento ADD CONSTRAINT chk_medicamento_fechas 
  CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio);

ALTER TABLE alergia_intolerancia ADD CONSTRAINT chk_alergia_tipo 
  CHECK (tipo IN ('alergia', 'intolerancia'));

ALTER TABLE alergia_intolerancia ADD CONSTRAINT chk_alergia_categoria 
  CHECK (categoria IN ('comida', 'medicamento', 'ambiente', 'biologico', 'otro'));

ALTER TABLE alergia_intolerancia ADD CONSTRAINT chk_alergia_severidad 
  CHECK (severidad IN ('leve', 'moderada', 'severa', 'mortal'));

ALTER TABLE alergia_intolerancia ADD CONSTRAINT chk_alergia_estado 
  CHECK (estado IN ('activa', 'inactiva', 'resuelta'));

ALTER TABLE procedimiento ADD CONSTRAINT chk_procedimiento_estado 
  CHECK (estado IN ('programado', 'en-progreso', 'completado', 'cancelado', 'suspendido'));

ALTER TABLE resultado_laboratorio ADD CONSTRAINT chk_resultado_estado 
  CHECK (estado IN ('registrado', 'preliminar', 'final', 'corregido', 'cancelado'));

ALTER TABLE estudio_imagen ADD CONSTRAINT chk_estudio_estado 
  CHECK (estado IN ('programado', 'en-progreso', 'completado', 'cancelado'));

ALTER TABLE plan_cuidado ADD CONSTRAINT chk_plan_estado 
  CHECK (estado IN ('borrador', 'activo', 'suspendido', 'completado', 'cancelado'));

ALTER TABLE plan_cuidado ADD CONSTRAINT chk_plan_categoria 
  CHECK (categoria IN ('tratamiento', 'prevencion', 'rehabilitacion', 'paliativo', 'educativo'));

ALTER TABLE plan_cuidado ADD CONSTRAINT chk_plan_fechas 
  CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio);

ALTER TABLE objetivo_cuidado ADD CONSTRAINT chk_objetivo_estado 
  CHECK (estado IN ('propuesto', 'aceptado', 'rechazado', 'en-progreso', 'alcanzado', 'no-alcanzado'));

ALTER TABLE objetivo_cuidado ADD CONSTRAINT chk_objetivo_prioridad 
  CHECK (prioridad IN ('baja', 'media', 'alta', 'critica'));

ALTER TABLE episodio_cuidado ADD CONSTRAINT chk_episodio_estado 
  CHECK (estado IN ('planificado', 'activo', 'pausa', 'completado', 'cancelado'));

ALTER TABLE episodio_cuidado ADD CONSTRAINT chk_episodio_fechas 
  CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio);

ALTER TABLE dispositivo_medico ADD CONSTRAINT chk_dispositivo_estado 
  CHECK (estado IN ('activo', 'inactivo', 'retirado', 'defectuoso'));

ALTER TABLE dispositivo_medico ADD CONSTRAINT chk_dispositivo_fechas 
  CHECK (fecha_retiro IS NULL OR fecha_retiro >= fecha_implantacion);

ALTER TABLE comunicacion ADD CONSTRAINT chk_comunicacion_tipo 
  CHECK (tipo IN ('email', 'sms', 'carta', 'llamada', 'fax', 'mensaje-app', 'video-llamada'));

ALTER TABLE comunicacion ADD CONSTRAINT chk_comunicacion_estado 
  CHECK (estado IN ('borrador', 'enviado', 'entregado', 'recibido', 'leido', 'respondido', 'error'));

ALTER TABLE comunicacion ADD CONSTRAINT chk_comunicacion_prioridad 
  CHECK (prioridad IN ('baja', 'normal', 'alta', 'urgente', 'critica'));

ALTER TABLE consentimiento ADD CONSTRAINT chk_consentimiento_tipo 
  CHECK (tipo IN ('tratamiento', 'procedimiento', 'investigacion', 'intercambio-datos', 'publicacion', 'autopsia'));

ALTER TABLE consentimiento ADD CONSTRAINT chk_consentimiento_estado 
  CHECK (estado IN ('borrador', 'activo', 'revocado', 'expirado', 'reemplazado'));

ALTER TABLE factura ADD CONSTRAINT chk_factura_estado 
  CHECK (estado IN ('borrador', 'pendiente', 'pagada', 'parcial', 'vencida', 'cancelada', 'anulada'));

ALTER TABLE factura ADD CONSTRAINT chk_factura_montos 
  CHECK (monto_total >= 0 AND monto_pagado >= 0 AND monto_pagado <= monto_total);

ALTER TABLE factura ADD CONSTRAINT chk_factura_fechas 
  CHECK (fecha_vencimiento >= fecha_emision);

ALTER TABLE detalle_factura ADD CONSTRAINT chk_detalle_cantidad 
  CHECK (cantidad > 0);

ALTER TABLE detalle_factura ADD CONSTRAINT chk_detalle_precios 
  CHECK (precio_unitario >= 0 AND subtotal >= 0);

ALTER TABLE grupo_pacientes ADD CONSTRAINT chk_grupo_tipo 
  CHECK (tipo IN ('cohorte', 'familia', 'equipo-cuidado', 'comunidad', 'estudio', 'programa'));

ALTER TABLE membresia_grupo ADD CONSTRAINT chk_membresia_estado 
  CHECK (estado IN ('activo', 'inactivo', 'suspendido', 'egresado'));

ALTER TABLE membresia_grupo ADD CONSTRAINT chk_membresia_fechas 
  CHECK (fecha_salida IS NULL OR fecha_salida >= fecha_ingreso);

ALTER TABLE medida_salud_publica ADD CONSTRAINT chk_medida_tipo 
  CHECK (tipo_medida IN ('vigilancia', 'prevencion', 'control-brote', 'investigacion-epidemiologica', 'inmunizacion'));

ALTER TABLE participacion_estudio ADD CONSTRAINT chk_participacion_estado 
  CHECK (estado IN ('elegible', 'inscrito', 'activo', 'completado', 'retirado', 'excluido'));

ALTER TABLE participacion_estudio ADD CONSTRAINT chk_participacion_fechas 
  CHECK (fecha_salida IS NULL OR fecha_salida >= fecha_ingreso);

ALTER TABLE evento_adverso ADD CONSTRAINT chk_evento_severidad 
  CHECK (severidad IN ('leve', 'moderado', 'severo', 'mortal'));

ALTER TABLE evento_adverso ADD CONSTRAINT chk_evento_causalidad 
  CHECK (causalidad IN ('no-relacionado', 'dudoso', 'posible', 'probable', 'definitivo'));

ALTER TABLE evento_adverso ADD CONSTRAINT chk_evento_estado 
  CHECK (estado IN ('reportado', 'en-investigacion', 'evaluado', 'cerrado'));

ALTER TABLE concepto_terminologia ADD CONSTRAINT chk_concepto_estado 
  CHECK (estado IN ('activo', 'inactivo', 'deprecado', 'experimental'));

ALTER TABLE mapeo_terminologia ADD CONSTRAINT chk_mapeo_tipo 
  CHECK (tipo_mapeo IN ('equivalente', 'mas-amplio', 'mas-especifico', 'relacionado', 'aproximado'));

ALTER TABLE mapeo_terminologia ADD CONSTRAINT chk_mapeo_confianza 
  CHECK (confianza >= 0.0 AND confianza <= 1.0);

ALTER TABLE tarea ADD CONSTRAINT chk_tarea_estado 
  CHECK (estado IN ('solicitada', 'asignada', 'aceptada', 'en-progreso', 'completada', 'cancelada', 'suspendida'));

ALTER TABLE tarea ADD CONSTRAINT chk_tarea_prioridad 
  CHECK (prioridad IN ('baja', 'normal', 'alta', 'urgente', 'critica'));

ALTER TABLE historia_familiar ADD CONSTRAINT chk_historia_estado_vital 
  CHECK (estado_vital IN ('vivo', 'fallecido', 'desconocido'));

ALTER TABLE historia_familiar ADD CONSTRAINT chk_historia_edad 
  CHECK (edad_diagnostico IS NULL OR edad_diagnostico >= 0);

ALTER TABLE riesgo_paciente ADD CONSTRAINT chk_riesgo_probabilidad 
  CHECK (probabilidad IN ('muy-baja', 'baja', 'media', 'alta', 'muy-alta'));

ALTER TABLE riesgo_paciente ADD CONSTRAINT chk_riesgo_estado 
  CHECK (estado IN ('identificado', 'activo', 'mitigado', 'resuelto', 'no-aplicable'));

ALTER TABLE riesgo_paciente ADD CONSTRAINT chk_riesgo_fechas 
  CHECK (fecha_mitigacion IS NULL OR fecha_mitigacion >= fecha_identificacion);

ALTER TABLE cuidado ADD CONSTRAINT chk_cuidado_estado 
  CHECK (estado IN ('programado', 'en-progreso', 'completado', 'cancelado'));

ALTER TABLE cuidado ADD CONSTRAINT chk_cuidado_duracion 
  CHECK (duracion_minutos IS NULL OR duracion_minutos > 0);

ALTER TABLE guia_clinica ADD CONSTRAINT chk_guia_estado 
  CHECK (estado IN ('borrador', 'en-revision', 'activa', 'actualizada', 'retirada', 'obsoleta'));

-- Constraints para fechas lógicas
ALTER TABLE condicion ADD CONSTRAINT chk_condicion_fechas 
  CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio);

ALTER TABLE horario_atencion ADD CONSTRAINT chk_horario_horas 
  CHECK (hora_fin > hora_inicio);

ALTER TABLE horario_atencion ADD CONSTRAINT chk_horario_dia 
  CHECK (dia_semana >= 0 AND dia_semana <= 6);

-- Constraints únicos adicionales
ALTER TABLE organizacion ADD CONSTRAINT uk_organizacion_nombre UNIQUE (nombre);
ALTER TABLE concepto_terminologia ADD CONSTRAINT uk_terminologia_sistema_codigo UNIQUE (sistema_codificacion, codigo);
ALTER TABLE guia_clinica ADD CONSTRAINT uk_guia_titulo_version UNIQUE (titulo, version);

-- ============================================================================
-- FUNCIONES AUXILIARES PARA ADMISIONES Y TRIAGE
-- ============================================================================

-- Función para generar código de admisión único
CREATE OR REPLACE FUNCTION generar_codigo_admision()
RETURNS TEXT AS $$
DECLARE
    nuevo_codigo TEXT;
    existe BOOLEAN;
    contador INTEGER := 1;
    fecha_actual TEXT;
BEGIN
    -- Obtener fecha actual en formato YYYYMMDD
    fecha_actual := TO_CHAR(NOW(), 'YYYYMMDD');
    
    LOOP
        -- Generar código: ADM-YYYYMMDD-####
        nuevo_codigo := 'ADM-' || fecha_actual || '-' || LPAD(contador::TEXT, 4, '0');
        
        -- Verificar si existe
        SELECT EXISTS(SELECT 1 FROM admision WHERE admission_id = nuevo_codigo) INTO existe;
        
        -- Si no existe, retornar el código
        IF NOT existe THEN
            RETURN nuevo_codigo;
        END IF;
        
        -- Incrementar contador
        contador := contador + 1;
        
        -- Prevenir bucle infinito (máximo 9999 admisiones por día)
        IF contador > 9999 THEN
            RAISE EXCEPTION 'No se pueden generar más códigos de admisión para hoy';
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Función para calcular IMC (Índice de Masa Corporal)
CREATE OR REPLACE FUNCTION calcular_imc(peso_kg DECIMAL, altura_cm INTEGER)
RETURNS DECIMAL AS $$
BEGIN
    IF peso_kg IS NULL OR altura_cm IS NULL OR altura_cm = 0 THEN
        RETURN NULL;
    END IF;
    
    -- IMC = peso (kg) / (altura (m))^2
    RETURN ROUND(peso_kg / POWER(altura_cm / 100.0, 2), 2);
END;
$$ LANGUAGE plpgsql;

-- Función para calcular presión arterial media (PAM)
CREATE OR REPLACE FUNCTION calcular_pam(sistolica INTEGER, diastolica INTEGER)
RETURNS INTEGER AS $$
BEGIN
    IF sistolica IS NULL OR diastolica IS NULL THEN
        RETURN NULL;
    END IF;
    
    -- PAM = ((2 × diastólica) + sistólica) / 3
    RETURN ((2 * diastolica) + sistolica) / 3;
END;
$$ LANGUAGE plpgsql;

-- Trigger para actualizar updated_at en admisiones
CREATE OR REPLACE FUNCTION update_admision_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- NOTA: Triggers no están soportados en tablas distribuidas de Citus
-- El campo updated_at se actualiza manualmente en el código de la aplicación
-- CREATE TRIGGER trigger_admision_updated_at
-- BEFORE UPDATE ON admision
-- FOR EACH ROW
-- EXECUTE FUNCTION update_admision_timestamp();

-- ============================================================================
-- VISTAS ÚTILES PARA ADMISIONES
-- ============================================================================

-- Vista de admisiones con información del paciente
CREATE OR REPLACE VIEW vista_admisiones_completas AS
SELECT 
    a.admission_id,
    a.documento_id,
    a.paciente_id,
    a.cita_id,
    a.fecha_admision,
    a.admitido_por,
    a.motivo_consulta,
    a.prioridad,
    a.estado_admision,
    a.presion_arterial_sistolica,
    a.presion_arterial_diastolica,
    a.frecuencia_cardiaca,
    a.frecuencia_respiratoria,
    a.temperatura,
    a.saturacion_oxigeno,
    a.peso,
    a.altura,
    calcular_imc(a.peso, a.altura) as imc,
    calcular_pam(a.presion_arterial_sistolica, a.presion_arterial_diastolica) as presion_arterial_media,
    a.nivel_dolor,
    a.nivel_conciencia,
    a.sintomas_principales,
    a.notas_enfermeria,
    p.nombre,
    p.apellido,
    p.sexo,
    p.fecha_nacimiento,
    EXTRACT(YEAR FROM AGE(p.fecha_nacimiento)) as edad,
    c.fecha_hora as fecha_hora_cita,
    c.profesional_id,
    c.tipo_cita
FROM admision a
INNER JOIN paciente p ON a.documento_id = p.documento_id AND a.paciente_id = p.paciente_id
LEFT JOIN cita c ON a.documento_id = c.documento_id AND a.cita_id = c.cita_id;

-- Vista de citas pendientes de admisión
CREATE OR REPLACE VIEW vista_citas_pendientes_admision AS
SELECT 
    c.cita_id,
    c.documento_id,
    c.paciente_id,
    c.fecha_hora,
    c.tipo_cita,
    c.motivo,
    c.estado,
    c.estado_admision,
    p.nombre,
    p.apellido,
    p.sexo,
    p.fecha_nacimiento,
    p.contacto,
    EXTRACT(YEAR FROM AGE(p.fecha_nacimiento)) as edad,
    pr.nombre as profesional_nombre,
    pr.apellido as profesional_apellido,
    pr.especialidad
FROM cita c
INNER JOIN paciente p ON c.documento_id = p.documento_id AND c.paciente_id = p.paciente_id
LEFT JOIN profesional pr ON c.profesional_id = pr.profesional_id
WHERE c.estado_admision = 'pendiente' OR c.estado_admision IS NULL
ORDER BY c.fecha_hora;

-- ============================================================================
-- COMENTARIOS FINALES SOBRE EL DISEÑO
-- ============================================================================
/*
RESUMEN DEL ESQUEMA FHIR EXTENDIDO:

1. DISTRIBUCIÓN CITUS:
   - 31 tablas distribuidas por documento_id para co-localización de datos del paciente
   - 9 tablas de referencia replicadas en todos los nodos
   - Optimizado para consultas centradas en el paciente

2. INTEGRIDAD REFERENCIAL:
   - 50+ foreign keys implementadas respetando las limitaciones de Citus
   - 50+ constraints de validación para integridad de datos
   - Constraints únicos para prevenir duplicados

3. PERFORMANCE:
   - 30+ índices optimizados para consultas comunes
   - Índices compuestos para consultas frecuentes
   - Preparado para índices de texto completo

4. SISTEMA DE ADMISIÓN Y TRIAGE:
   - Tabla 'admision' con signos vitales y datos de triage
   - Gestión de citas pendientes y admitidas
   - Funciones SQL para cálculo de IMC y PAM
   - Generación automática de códigos de admisión
   - Vistas especializadas para flujo de trabajo de enfermería

5. EXTENSIBILIDAD:
   - Campos JSONB para datos variables
   - Estructura flexible para diferentes tipos de recursos FHIR
   - Compatible con estándares FHIR R4

6. AUDITORÍA Y TRAZABILIDAD:
   - Timestamps de creación en todas las tablas
   - Estados bien definidos para flujos de trabajo
   - Campos de metadatos para seguimiento

TOTAL DE RECURSOS IMPLEMENTADOS: ~53 tipos de datos FHIR + Sistema de Admisión
*/
