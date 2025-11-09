-- =============================================================================
-- Migration 004: Create Authentication Tables
-- Sistema de autenticación y autorización
-- =============================================================================

-- Crear tabla de roles
CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Crear tabla de permisos
CREATE TABLE IF NOT EXISTS user_permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    resource_type VARCHAR(50),
    action VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Crear tabla de usuarios
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    email_verified BOOLEAN DEFAULT false,
    phone VARCHAR(20),
    preferred_language VARCHAR(10) DEFAULT 'es',
    timezone VARCHAR(50) DEFAULT 'UTC',
    last_login TIMESTAMP WITH TIME ZONE,
    password_changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Crear tabla de relación usuario-roles (muchos a muchos)
CREATE TABLE IF NOT EXISTS user_role_assignments (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES user_roles(id) ON DELETE CASCADE,
    assigned_by UUID REFERENCES users(id),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(user_id, role_id)
);

-- Crear tabla de relación role-permisos (muchos a muchos)
CREATE TABLE IF NOT EXISTS role_permission_assignments (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES user_roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES user_permissions(id) ON DELETE CASCADE,
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(role_id, permission_id)
);

-- Crear tabla de tokens de refresh
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP WITH TIME ZONE,
    user_agent TEXT,
    ip_address INET
);

-- Crear tabla de API keys
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,
    scopes TEXT[] DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

-- =============================================================================
-- Índices para optimización
-- =============================================================================

-- Índices para usuarios
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- Índices para roles y permisos
CREATE INDEX IF NOT EXISTS idx_user_roles_name ON user_roles(name);
CREATE INDEX IF NOT EXISTS idx_user_permissions_name ON user_permissions(name);
CREATE INDEX IF NOT EXISTS idx_user_permissions_resource ON user_permissions(resource_type, action);

-- Índices para asignaciones
CREATE INDEX IF NOT EXISTS idx_user_role_assignments_user ON user_role_assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_user_role_assignments_role ON user_role_assignments(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permission_assignments_role ON role_permission_assignments(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permission_assignments_permission ON role_permission_assignments(permission_id);

-- Índices para tokens
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires ON refresh_tokens(expires_at);

-- Índices para API keys
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires ON api_keys(expires_at);

-- =============================================================================
-- Triggers para actualización automática de timestamps
-- =============================================================================

-- Función para actualizar timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para actualizar updated_at
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_roles_updated_at 
    BEFORE UPDATE ON user_roles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_permissions_updated_at 
    BEFORE UPDATE ON user_permissions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Datos iniciales
-- =============================================================================

-- Insertar roles básicos
INSERT INTO user_roles (name, description) VALUES 
    ('admin', 'Administrador del sistema con acceso completo'),
    ('practitioner', 'Profesional de salud con acceso a recursos médicos'),
    ('patient', 'Paciente con acceso limitado a sus propios datos'),
    ('viewer', 'Usuario con acceso de solo lectura')
ON CONFLICT (name) DO NOTHING;

-- Insertar permisos básicos de FHIR
INSERT INTO user_permissions (name, description, resource_type, action) VALUES 
    -- Permisos de Patient
    ('patient.read', 'Leer información de pacientes', 'Patient', 'read'),
    ('patient.write', 'Crear y actualizar pacientes', 'Patient', 'write'),
    ('patient.delete', 'Eliminar pacientes', 'Patient', 'delete'),
    
    -- Permisos de Practitioner
    ('practitioner.read', 'Leer información de profesionales', 'Practitioner', 'read'),
    ('practitioner.write', 'Crear y actualizar profesionales', 'Practitioner', 'write'),
    ('practitioner.delete', 'Eliminar profesionales', 'Practitioner', 'delete'),
    
    -- Permisos de Observation
    ('observation.read', 'Leer observaciones médicas', 'Observation', 'read'),
    ('observation.write', 'Crear y actualizar observaciones', 'Observation', 'write'),
    ('observation.delete', 'Eliminar observaciones', 'Observation', 'delete'),
    
    -- Permisos de Encounter
    ('encounter.read', 'Leer encuentros médicos', 'Encounter', 'read'),
    ('encounter.write', 'Crear y actualizar encuentros', 'Encounter', 'write'),
    ('encounter.delete', 'Eliminar encuentros', 'Encounter', 'delete'),
    
    -- Permisos de Condition
    ('condition.read', 'Leer condiciones médicas', 'Condition', 'read'),
    ('condition.write', 'Crear y actualizar condiciones', 'Condition', 'write'),
    ('condition.delete', 'Eliminar condiciones', 'Condition', 'delete'),
    
    -- Permisos de MedicationRequest
    ('medicationrequest.read', 'Leer prescripciones médicas', 'MedicationRequest', 'read'),
    ('medicationrequest.write', 'Crear y actualizar prescripciones', 'MedicationRequest', 'write'),
    ('medicationrequest.delete', 'Eliminar prescripciones', 'MedicationRequest', 'delete'),
    
    -- Permisos administrativos
    ('admin.users', 'Administrar usuarios del sistema', 'User', 'admin'),
    ('admin.roles', 'Administrar roles y permisos', 'Role', 'admin'),
    ('admin.system', 'Acceso a configuración del sistema', 'System', 'admin'),
    
    -- Permisos especiales
    ('system.read', 'Acceso de lectura a recursos del sistema', 'System', 'read'),
    ('system.write', 'Acceso de escritura a recursos del sistema', 'System', 'write')
    
ON CONFLICT (name) DO NOTHING;

-- Asignar permisos a roles
INSERT INTO role_permission_assignments (role_id, permission_id) 
SELECT r.id, p.id 
FROM user_roles r, user_permissions p 
WHERE r.name = 'admin' -- Administradores tienen todos los permisos
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Permisos para practitioner
INSERT INTO role_permission_assignments (role_id, permission_id)
SELECT r.id, p.id
FROM user_roles r, user_permissions p
WHERE r.name = 'practitioner' 
AND p.name IN (
    'patient.read', 'patient.write',
    'practitioner.read', 'practitioner.write',
    'observation.read', 'observation.write',
    'encounter.read', 'encounter.write',
    'condition.read', 'condition.write',
    'medicationrequest.read', 'medicationrequest.write'
)
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Permisos para patient (solo sus propios datos)
INSERT INTO role_permission_assignments (role_id, permission_id)
SELECT r.id, p.id
FROM user_roles r, user_permissions p
WHERE r.name = 'patient'
AND p.name IN (
    'patient.read',
    'observation.read',
    'encounter.read',
    'condition.read',
    'medicationrequest.read'
)
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Permisos para viewer (solo lectura)
INSERT INTO role_permission_assignments (role_id, permission_id)
SELECT r.id, p.id
FROM user_roles r, user_permissions p
WHERE r.name = 'viewer'
AND p.action = 'read'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =============================================================================
-- Crear usuario administrador por defecto
-- =============================================================================

-- Insertar usuario admin por defecto (password: admin123)
-- Hash generado con bcrypt para "admin123"
INSERT INTO users (
    username, 
    email, 
    hashed_password, 
    full_name, 
    is_active, 
    is_superuser, 
    email_verified
) VALUES (
    'admin',
    'admin@localhost',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- admin123
    'Administrador del Sistema',
    true,
    true,
    true
) ON CONFLICT (username) DO NOTHING;

-- Asignar rol admin al usuario admin
INSERT INTO user_role_assignments (user_id, role_id)
SELECT u.id, r.id
FROM users u, user_roles r
WHERE u.username = 'admin' AND r.name = 'admin'
ON CONFLICT (user_id, role_id) DO NOTHING;

-- =============================================================================
-- Configuración de distribución para Citus
-- =============================================================================

-- Distribuir tablas principales por user_id para co-location
SELECT create_distributed_table('users', 'id');
SELECT create_distributed_table('user_role_assignments', 'user_id');
SELECT create_distributed_table('refresh_tokens', 'user_id');
SELECT create_distributed_table('api_keys', 'user_id');

-- Las tablas de referencia (roles, permisos) se mantienen replicadas
SELECT create_reference_table('user_roles');
SELECT create_reference_table('user_permissions'); 
SELECT create_reference_table('role_permission_assignments');

COMMIT;