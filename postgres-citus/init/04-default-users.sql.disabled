-- =====================================================
-- Insertar usuarios predeterminados para el sistema FHIR
-- Usuarios para demostración con credenciales conocidas
-- =====================================================

-- Función para generar hash de password simple (para demostración)
-- En producción se debe usar bcrypt desde la aplicación
CREATE OR REPLACE FUNCTION simple_hash(password TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Para demostración, usamos un hash simple
    -- En producción debe ser bcrypt desde FastAPI
    RETURN encode(digest(password || 'demo_salt', 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Insertar usuarios predeterminados
INSERT INTO users (
    username, email, hashed_password, full_name, role, 
    is_active, is_verified, created_at, updated_at
) VALUES 
    (
        'admin',
        'admin@hospital.com',
        simple_hash('admin'),
        'Administrador del Sistema',
        'admin',
        true,
        true,
        NOW(),
        NOW()
    ),
    (
        'medic', 
        'medic@hospital.com',
        simple_hash('medic'),
        'Dr. Juan Pérez',
        'practitioner',
        true,
        true,
        NOW(),
        NOW()
    ),
    (
        'patient',
        'patient@hospital.com', 
        simple_hash('patient'),
        'María García',
        'patient',
        true,
        true,
        NOW(),
        NOW()
    ),
    (
        'audit',
        'audit@hospital.com',
        simple_hash('audit'), 
        'Auditor del Sistema',
        'viewer',
        true,
        true,
        NOW(),
        NOW()
    )
ON CONFLICT (username) DO UPDATE SET
    email = EXCLUDED.email,
    full_name = EXCLUDED.full_name,
    role = EXCLUDED.role,
    updated_at = NOW();

-- Crear perfil de médico para el usuario 'medic'
INSERT INTO practitioners (
    user_id, identifier, name_given, name_family,
    specialty, phone, email, active, created_at
) 
SELECT 
    u.id,
    'DOC-' || LPAD(u.id::TEXT, 6, '0'),
    'Dr. Juan',
    'Pérez',
    'Medicina General',
    '+1-555-0123',
    'medic@hospital.com',
    true,
    NOW()
FROM users u 
WHERE u.username = 'medic'
ON CONFLICT (user_id) DO UPDATE SET
    specialty = EXCLUDED.specialty,
    phone = EXCLUDED.phone,
    email = EXCLUDED.email;

-- Crear perfil de paciente para el usuario 'patient'  
INSERT INTO patients (
    user_id, identifier, name_given, name_family,
    birth_date, gender, phone, email, active, created_at
)
SELECT 
    u.id,
    'PAT-' || LPAD(u.id::TEXT, 6, '0'),
    'María',
    'García', 
    '1985-03-15',
    'female',
    '+1-555-0456',
    'patient@hospital.com',
    true,
    NOW()
FROM users u
WHERE u.username = 'patient'
ON CONFLICT (user_id) DO UPDATE SET
    birth_date = EXCLUDED.birth_date,
    gender = EXCLUDED.gender,
    phone = EXCLUDED.phone,
    email = EXCLUDED.email;

-- Crear organización de ejemplo para los médicos
INSERT INTO organizations (
    identifier, name, type, phone, email, 
    address_line, address_city, address_state, address_postal_code,
    active, created_at
) VALUES (
    'ORG-HOSPITAL-001',
    'Hospital General Central',
    'hospital',
    '+1-555-1000',
    'info@hospital.com',
    '123 Medical Center Dr',
    'Ciudad Médica',
    'Estado',
    '12345',
    true,
    NOW()
) ON CONFLICT (identifier) DO UPDATE SET
    name = EXCLUDED.name,
    phone = EXCLUDED.phone,
    email = EXCLUDED.email;

-- Crear algunos encuentros de ejemplo para demostrar el sistema
INSERT INTO encounters (
    patient_id, practitioner_id, organization_id,
    identifier, status, class, type,
    subject_reference, participant_individual,
    period_start, period_end, created_at
)
SELECT 
    p.id,
    pr.id, 
    o.id,
    'ENC-' || LPAD((RANDOM() * 999999)::INT::TEXT, 6, '0'),
    'finished',
    'outpatient',
    'consultation',
    'Patient/' || p.identifier,
    'Practitioner/' || pr.identifier,
    NOW() - INTERVAL '7 days',
    NOW() - INTERVAL '7 days' + INTERVAL '1 hour',
    NOW()
FROM patients p
CROSS JOIN practitioners pr  
CROSS JOIN organizations o
WHERE p.user_id = (SELECT id FROM users WHERE username = 'patient')
  AND pr.user_id = (SELECT id FROM users WHERE username = 'medic')
  AND o.identifier = 'ORG-HOSPITAL-001'
LIMIT 1
ON CONFLICT DO NOTHING;

-- Crear algunas observaciones de ejemplo
INSERT INTO observations (
    patient_id, encounter_id, practitioner_id,
    identifier, status, category, code, code_display,
    subject_reference, value_quantity_value, value_quantity_unit,
    effective_datetime, issued, created_at
)
SELECT 
    p.id,
    e.id,
    pr.id,
    'OBS-' || LPAD((RANDOM() * 999999)::INT::TEXT, 6, '0'),
    'final',
    'vital-signs',
    '8480-6',
    'Systolic blood pressure',
    'Patient/' || p.identifier,
    120,
    'mmHg',
    NOW() - INTERVAL '7 days',
    NOW() - INTERVAL '7 days',
    NOW()
FROM patients p
JOIN encounters e ON e.patient_id = p.id
JOIN practitioners pr ON pr.id = e.practitioner_id
WHERE p.user_id = (SELECT id FROM users WHERE username = 'patient')
LIMIT 1
ON CONFLICT DO NOTHING;

-- Crear registro de auditoría para la creación de usuarios
INSERT INTO audit_logs (
    user_id, action, resource_type, resource_id,
    resource_reference, changes, ip_address, user_agent,
    created_at
)
SELECT 
    u.id,
    'CREATE',
    'User', 
    u.id,
    'User/' || u.username,
    jsonb_build_object(
        'username', u.username,
        'role', u.role,
        'created_by', 'system_initialization'
    ),
    '127.0.0.1',
    'System/1.0 (Initialization Script)',
    NOW()
FROM users u
WHERE u.username IN ('admin', 'medic', 'patient', 'audit')
ON CONFLICT DO NOTHING;

-- Actualizar estadísticas de las tablas
ANALYZE users;
ANALYZE practitioners;  
ANALYZE patients;
ANALYZE organizations;
ANALYZE encounters;
ANALYZE observations;
ANALYZE audit_logs;

-- Mostrar resumen de usuarios creados
SELECT 
    username,
    email,
    full_name,
    role,
    is_active,
    created_at
FROM users 
WHERE username IN ('admin', 'medic', 'patient', 'audit')
ORDER BY 
    CASE role 
        WHEN 'admin' THEN 1
        WHEN 'practitioner' THEN 2  
        WHEN 'patient' THEN 3
        WHEN 'viewer' THEN 4
    END;

-- Mostrar estadísticas del sistema
SELECT 
    'Users' as table_name, COUNT(*) as count 
FROM users
UNION ALL
SELECT 'Practitioners', COUNT(*) FROM practitioners  
UNION ALL
SELECT 'Patients', COUNT(*) FROM patients
UNION ALL  
SELECT 'Organizations', COUNT(*) FROM organizations
UNION ALL
SELECT 'Encounters', COUNT(*) FROM encounters
UNION ALL
SELECT 'Observations', COUNT(*) FROM observations
UNION ALL
SELECT 'Audit Logs', COUNT(*) FROM audit_logs;

-- Limpiar función temporal
DROP FUNCTION IF EXISTS simple_hash(TEXT);

-- Mensaje de confirmación
\echo ''
\echo '✅ USUARIOS PREDETERMINADOS CREADOS EXITOSAMENTE'
\echo '================================================'
\echo 'Credenciales de acceso:'
\echo '  admin/admin     - Administrador del Sistema'
\echo '  medic/medic     - Dr. Juan Pérez (Médico)'  
\echo '  patient/patient - María García (Paciente)'
\echo '  audit/audit     - Auditor del Sistema'
\echo ''
\echo '🌐 Acceso a la aplicación:'
\echo '  API: http://localhost:8000/docs'
\echo '  Web: http://localhost:8000/login'
\echo ''
\echo '⚠️  NOTA: Estas son credenciales de demostración.'
\echo '   En producción cambiar las contraseñas inmediatamente.'
\echo ''