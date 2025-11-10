-- 05-auth-tables.sql
-- Tablas de autenticación y usuarios para el sistema FHIR

\c hce

-- Crear extensión para UUID si no existe
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    user_type VARCHAR(20) DEFAULT 'patient',
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    is_superuser BOOLEAN DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    fhir_patient_id VARCHAR(255),
    fhir_practitioner_id VARCHAR(255),
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

-- Tabla de roles
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    fhir_scopes TEXT[],
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de permisos
CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(150) NOT NULL,
    description TEXT,
    category VARCHAR(50) DEFAULT 'general',
    fhir_resource VARCHAR(50),
    fhir_action VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de asociación usuario-rol
CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    granted_by UUID REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

-- Tabla de asociación rol-permiso
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (role_id, permission_id)
);

-- Tabla de API keys
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    usage_count INTEGER DEFAULT 0,
    rate_limit INTEGER,
    allowed_ips TEXT[],
    scopes TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para optimización
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_user_type ON users(user_type);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login);
CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);
CREATE INDEX IF NOT EXISTS idx_permissions_name ON permissions(name);
CREATE INDEX IF NOT EXISTS idx_permissions_category ON permissions(category);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_prefix ON api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON roles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Función para hash de password simple (para demostración)
CREATE OR REPLACE FUNCTION simple_hash(password TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Para demostración, usamos un hash simple
    -- En producción debe ser bcrypt desde FastAPI
    RETURN encode(digest(password || 'demo_salt_fhir', 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Insertar roles predeterminados
INSERT INTO roles (name, display_name, description, fhir_scopes) VALUES 
    ('admin', 'Administrador', 'Acceso completo al sistema', ARRAY['user/*.*', 'system/*.*']),
    ('practitioner', 'Profesional de Salud', 'Acceso a recursos de pacientes y clínicos', ARRAY['user/Patient.*', 'user/Observation.*', 'user/Condition.*', 'user/MedicationRequest.*']),
    ('patient', 'Paciente', 'Acceso limitado a sus propios datos', ARRAY['patient/Patient.read', 'patient/Observation.read', 'patient/Condition.read']),
    ('viewer', 'Auditor/Visualizador', 'Solo lectura de recursos permitidos', ARRAY['user/Patient.read', 'user/Observation.read'])
ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    fhir_scopes = EXCLUDED.fhir_scopes,
    updated_at = NOW();

-- Insertar permisos básicos
INSERT INTO permissions (name, display_name, description, category, fhir_resource, fhir_action) VALUES 
    -- Permisos de pacientes
    ('patient.read', 'Leer Pacientes', 'Ver información de pacientes', 'patient', 'Patient', 'read'),
    ('patient.write', 'Escribir Pacientes', 'Crear/actualizar pacientes', 'patient', 'Patient', 'write'),
    ('patient.delete', 'Eliminar Pacientes', 'Eliminar registros de pacientes', 'patient', 'Patient', 'delete'),
    
    -- Permisos de observaciones
    ('observation.read', 'Leer Observaciones', 'Ver observaciones clínicas', 'clinical', 'Observation', 'read'),
    ('observation.write', 'Escribir Observaciones', 'Crear/actualizar observaciones', 'clinical', 'Observation', 'write'),
    ('observation.delete', 'Eliminar Observaciones', 'Eliminar observaciones', 'clinical', 'Observation', 'delete'),
    
    -- Permisos de condiciones
    ('condition.read', 'Leer Condiciones', 'Ver condiciones médicas', 'clinical', 'Condition', 'read'),
    ('condition.write', 'Escribir Condiciones', 'Crear/actualizar condiciones', 'clinical', 'Condition', 'write'),
    ('condition.delete', 'Eliminar Condiciones', 'Eliminar condiciones', 'clinical', 'Condition', 'delete'),
    
    -- Permisos de medicamentos
    ('medication.read', 'Leer Medicamentos', 'Ver prescripciones', 'clinical', 'MedicationRequest', 'read'),
    ('medication.write', 'Escribir Medicamentos', 'Crear/actualizar prescripciones', 'clinical', 'MedicationRequest', 'write'),
    ('medication.delete', 'Eliminar Medicamentos', 'Eliminar prescripciones', 'clinical', 'MedicationRequest', 'delete'),
    
    -- Permisos administrativos
    ('admin.users', 'Administrar Usuarios', 'Gestionar usuarios del sistema', 'admin', NULL, NULL),
    ('admin.roles', 'Administrar Roles', 'Gestionar roles y permisos', 'admin', NULL, NULL),
    ('admin.system', 'Administrar Sistema', 'Configuración del sistema', 'admin', NULL, NULL),
    ('admin.audit', 'Ver Auditoría', 'Acceso a logs de auditoría', 'admin', NULL, NULL)
ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    updated_at = NOW();

-- Asignar permisos a roles
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r, permissions p 
WHERE r.name = 'admin' -- Admin tiene todos los permisos
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r, permissions p 
WHERE r.name = 'practitioner' 
AND p.name IN ('patient.read', 'patient.write', 'observation.read', 'observation.write', 'condition.read', 'condition.write', 'medication.read', 'medication.write')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r, permissions p 
WHERE r.name = 'patient' 
AND p.name IN ('patient.read', 'observation.read', 'condition.read', 'medication.read')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r, permissions p 
WHERE r.name = 'viewer' 
AND p.name IN ('patient.read', 'observation.read', 'condition.read', 'medication.read', 'admin.audit')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Insertar usuarios de demostración
INSERT INTO users (
    username, email, hashed_password, full_name, user_type, 
    is_active, is_verified, created_at, updated_at
) VALUES 
    (
        'admin',
        'admin@hospital.com',
        simple_hash('admin123'),
        'Administrador del Sistema',
        'admin',
        true,
        true,
        NOW(),
        NOW()
    ),
    (
        'medico', 
        'medico@hospital.com',
        simple_hash('medico123'),
        'Dr. Juan Pérez',
        'practitioner',
        true,
        true,
        NOW(),
        NOW()
    ),
    (
        'paciente',
        'paciente@hospital.com', 
        simple_hash('paciente123'),
        'María García',
        'patient',
        true,
        true,
        NOW(),
        NOW()
    ),
    (
        'auditor',
        'auditor@hospital.com',
        simple_hash('auditor123'), 
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
    user_type = EXCLUDED.user_type,
    updated_at = NOW();

-- Asignar roles a usuarios
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id 
FROM users u, roles r 
WHERE u.username = 'admin' AND r.name = 'admin'
ON CONFLICT (user_id, role_id) DO NOTHING;

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id 
FROM users u, roles r 
WHERE u.username = 'medico' AND r.name = 'practitioner'
ON CONFLICT (user_id, role_id) DO NOTHING;

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id 
FROM users u, roles r 
WHERE u.username = 'paciente' AND r.name = 'patient'
ON CONFLICT (user_id, role_id) DO NOTHING;

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id 
FROM users u, roles r 
WHERE u.username = 'auditor' AND r.name = 'viewer'
ON CONFLICT (user_id, role_id) DO NOTHING;

-- Mostrar resumen de usuarios creados
SELECT 
    u.username,
    u.email,
    u.full_name,
    u.user_type,
    u.is_active,
    r.name as role_name,
    u.created_at
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
WHERE u.username IN ('admin', 'medico', 'paciente', 'auditor')
ORDER BY 
    CASE u.user_type 
        WHEN 'admin' THEN 1
        WHEN 'practitioner' THEN 2  
        WHEN 'patient' THEN 3
        WHEN 'viewer' THEN 4
    END;

-- Limpiar función temporal
DROP FUNCTION IF EXISTS simple_hash(TEXT);

-- Mensaje de confirmación
\echo ''
\echo '✅ TABLAS DE AUTENTICACIÓN Y USUARIOS CREADOS EXITOSAMENTE'
\echo '=========================================================='
\echo 'Credenciales de acceso (username/password):'
\echo '  admin/admin123       - Administrador del Sistema'
\echo '  medico/medico123     - Dr. Juan Pérez (Médico)'  
\echo '  paciente/paciente123 - María García (Paciente)'
\echo '  auditor/auditor123   - Auditor del Sistema'
\echo ''
\echo '🌐 Endpoints de autenticación:'
\echo '  Login: POST http://localhost:8000/auth/login'
\echo '  Login Web: http://localhost/login'
\echo ''
\echo '⚠️  NOTA: Estas son credenciales de demostración.'
\echo '   En producción cambiar las contraseñas inmediatamente.'
\echo ''