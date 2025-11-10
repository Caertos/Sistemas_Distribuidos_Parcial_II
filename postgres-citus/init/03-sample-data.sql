-- 03-sample-data.sql
-- ARCHIVO DEPRECADO - NO SE EJECUTA
--
-- ⚠️  ESTE ARCHIVO HA SIDO DEPRECADO ⚠️
-- 
-- Los datos de ejemplo ahora se crean mediante el script llenar.sh
-- que proporciona un conjunto más completo y coherente de datos FHIR.
--
-- INSTRUCCIONES:
-- 1. Durante la instalación, cuando se pregunte si desea poblar la base de datos
--    con el script llenar.sh, responder "S" (Sí)
-- 2. O ejecutar manualmente: ./llenar.sh
--
-- El script llenar.sh incluye:
-- - 22 usuarios (admins, médicos, pacientes, auditores)
-- - 15 pacientes con historiales médicos completos
-- - Condiciones médicas, medicamentos, encuentros y observaciones
-- - Datos coherentes y relacionados entre tablas

\c hce_distribuida

-- ARCHIVO DEPRECADO - Datos comentados - usar llenar.sh en su lugar
/*
-- Insertar profesionales de ejemplo
INSERT INTO profesional (nombre, apellido, especialidad, registro_medico)
VALUES 
  ('Juan', 'García', 'Medicina General', 'MG-2024-001'),
  ('María', 'López', 'Pediatría', 'PED-2024-002'),
  ('Carlos', 'Rodríguez', 'Cardiología', 'CAR-2024-003'),
  ('Ana', 'Martínez', 'Neurología', 'NEU-2024-004'),
  ('Luis', 'Hernández', 'Traumatología', 'TRA-2024-005')
ON CONFLICT DO NOTHING;

-- Insertar pacientes de ejemplo
INSERT INTO paciente (paciente_id, documento_id, nombre, apellido, sexo, fecha_nacimiento, ciudad)
VALUES 
  (1, 1001234567, 'Pedro', 'González', 'masculino', '1985-03-15', 'Bogotá'),
  (2, 1002345678, 'Laura', 'Ramírez', 'femenino', '1990-07-22', 'Medellín'),
  (3, 1003456789, 'Jorge', 'Torres', 'masculino', '1978-11-30', 'Cali'),
  (4, 1004567890, 'Carmen', 'Díaz', 'femenino', '1995-01-08', 'Barranquilla'),
  (5, 1005678901, 'Roberto', 'Castro', 'masculino', '1982-05-19', 'Cartagena')
ON CONFLICT DO NOTHING;

-- Insertar encuentros de ejemplo
INSERT INTO encuentro (paciente_id, documento_id, fecha, motivo, diagnostico, profesional_id)
VALUES 
  (1, 1001234567, '2025-01-10 09:30:00', 'Control de rutina', 'Paciente sano', 1),
  (2, 1002345678, '2025-01-11 10:00:00', 'Dolor abdominal', 'Gastritis leve', 1),
  (3, 1003456789, '2025-01-12 14:30:00', 'Control cardiológico', 'Hipertensión controlada', 3),
  (4, 1004567890, '2025-01-13 11:00:00', 'Vacunación', 'Vacuna aplicada correctamente', 2),
  (5, 1005678901, '2025-01-14 15:00:00', 'Dolor en rodilla', 'Lesión de menisco', 5)
ON CONFLICT DO NOTHING;

-- Insertar observaciones de ejemplo
INSERT INTO observacion (paciente_id, documento_id, tipo, valor, unidad, fecha)
VALUES 
  (1, 1001234567, 'Presión Arterial', '120/80', 'mmHg', '2025-01-10 09:35:00'),
  (1, 1001234567, 'Peso', '75', 'kg', '2025-01-10 09:36:00'),
  (1, 1001234567, 'Altura', '175', 'cm', '2025-01-10 09:37:00'),
  (2, 1002345678, 'Temperatura', '36.5', '°C', '2025-01-11 10:05:00'),
  (2, 1002345678, 'Presión Arterial', '110/70', 'mmHg', '2025-01-11 10:06:00'),
  (3, 1003456789, 'Presión Arterial', '140/90', 'mmHg', '2025-01-12 14:35:00'),
  (3, 1003456789, 'Frecuencia Cardíaca', '78', 'bpm', '2025-01-12 14:36:00'),
  (4, 1004567890, 'Peso', '22', 'kg', '2025-01-13 11:05:00'),
  (5, 1005678901, 'Dolor', '7', 'escala 1-10', '2025-01-14 15:05:00')
ON CONFLICT DO NOTHING;

-- Insertar condiciones de ejemplo
INSERT INTO condicion (paciente_id, documento_id, codigo, descripcion, gravedad, fecha_inicio)
VALUES 
  (2, 1002345678, 'K29.7', 'Gastritis crónica', 'Leve', '2024-06-01'),
  (3, 1003456789, 'I10', 'Hipertensión arterial esencial', 'Moderada', '2020-03-15'),
  (5, 1005678901, 'S83.2', 'Desgarro de menisco', 'Moderada', '2025-01-14')
ON CONFLICT DO NOTHING;
*/

-- Mensaje de deprecación
\echo ''
\echo '⚠️  ARCHIVO 03-sample-data.sql DEPRECADO'
\echo '════════════════════════════════════════'
\echo ''
\echo '   Este archivo ya NO se usa para poblar datos.'
\echo '   En su lugar, usa el script llenar.sh que es más completo.'
\echo ''
\echo '   INSTRUCCIONES:'
\echo '   • Durante la instalación: Responder "S" cuando pregunte por llenar.sh'
\echo '   • Manual: Ejecutar ./llenar.sh'
\echo ''
\echo '   El script llenar.sh incluye usuarios, pacientes, historiales médicos'
\echo '   completos y datos coherentes para el sistema FHIR.'
\echo ''
