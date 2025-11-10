#!/bin/bash
set -e

# =============================================================================
# Script para poblar la base de datos con datos de ejemplo
# Sistema FHIR Distribuido - Parcial II Sistemas Distribuidos
# =============================================================================

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Variables de configuración
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="hce_distribuida"
DB_USER="postgres"
DB_PASSWORD="postgres123"

# Función para ejecutar SQL
execute_sql() {
    local sql="$1"
    docker exec citus-coordinator psql -U "$DB_USER" -d "$DB_NAME" -c "$sql"
}

# Función para verificar conexión a la base de datos
check_db_connection() {
    log "Verificando conexión a la base de datos..."
    if ! docker exec citus-coordinator psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        error "No se puede conectar a la base de datos"
        error "Asegúrate de que los contenedores estén ejecutándose"
        exit 1
    fi
    log "✅ Conexión a la base de datos exitosa"
}

# Función para verificar si ya existen datos
check_existing_data() {
    log "Verificando datos existentes..."
    
    local user_count=$(docker exec citus-coordinator psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM users;" | tr -d ' ')
    local patient_count=$(docker exec citus-coordinator psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM paciente;" | tr -d ' ')
    
    if [[ $existing_users -gt 0 || $existing_patients -gt 0 ]]; then
        echo_warning "Ya existen datos en la base de datos:"
        echo_warning "- Usuarios: $existing_users"
        echo_warning "- Pacientes: $existing_patients"
        echo ""
        
        # Si se pasa --force, continuar sin preguntar
        if [[ "$1" == "--force" ]]; then
            echo_info "Modo --force activado, continuando sin preguntar..."
        else
            echo -n "¿Deseas continuar y agregar más datos? (s/N): "
            read -r response
            if [[ ! "$response" =~ ^[Ss]$ ]]; then
                echo_info "Operación cancelada por el usuario"
                exit 1
            fi
        fi
    fi
}

# Función para crear usuarios básicos del sistema
create_system_users() {
    log "Creando usuarios del sistema..."
    
    # Hash de contraseña "secret" con salt
    local password_hash="bc44a1755bfe54b6efa2abb783f19144511eb277efc6f8f9088df7b67b46614b"
    
    # Crear 2 administradores
    execute_sql "
    INSERT INTO users (id, username, email, full_name, hashed_password, user_type, is_active, is_verified, created_at, updated_at) VALUES
    (gen_random_uuid(), 'admin1', 'admin1@hospital.com', 'Dr. Carlos Administrador', '$password_hash', 'admin', true, true, NOW(), NOW()),
    (gen_random_uuid(), 'admin2', 'admin2@hospital.com', 'Dra. Ana Administradora', '$password_hash', 'admin', true, true, NOW(), NOW())
    ON CONFLICT (username) DO NOTHING;
    "
    
    # Crear 1 auditor
    execute_sql "
    INSERT INTO users (id, username, email, full_name, hashed_password, user_type, is_active, is_verified, created_at, updated_at) VALUES
    (gen_random_uuid(), 'auditor1', 'auditor1@hospital.com', 'Lic. María Auditora', '$password_hash', 'auditor', true, true, NOW(), NOW())
    ON CONFLICT (username) DO NOTHING;
    "
    
    log "✅ Usuarios del sistema creados"
}

# Función para crear médicos
create_doctors() {
    log "Creando médicos especialistas..."
    
    local password_hash="bc44a1755bfe54b6efa2abb783f19144511eb277efc6f8f9088df7b67b46614b"
    
    # Crear usuarios médicos
    execute_sql "
    INSERT INTO users (id, username, email, full_name, hashed_password, user_type, is_active, is_verified, created_at, updated_at, fhir_practitioner_id) VALUES
    (gen_random_uuid(), 'cardiologo1', 'cardiologo1@hospital.com', 'Dr. Juan Cardiólogo', '$password_hash', 'practitioner', true, true, NOW(), NOW(), '1'),
    (gen_random_uuid(), 'neurologo1', 'neurologo1@hospital.com', 'Dra. María Neuróloga', '$password_hash', 'practitioner', true, true, NOW(), NOW(), '2'),
    (gen_random_uuid(), 'pediatra1', 'pediatra1@hospital.com', 'Dr. Carlos Pediatra', '$password_hash', 'practitioner', true, true, NOW(), NOW(), '3'),
    (gen_random_uuid(), 'oncologo1', 'oncologo1@hospital.com', 'Dra. Ana Oncóloga', '$password_hash', 'practitioner', true, true, NOW(), NOW(), '4'),
    (gen_random_uuid(), 'dermatologo1', 'dermatologo1@hospital.com', 'Dr. Luis Dermatólogo', '$password_hash', 'practitioner', true, true, NOW(), NOW(), '5')
    ON CONFLICT (username) DO NOTHING;
    "
    
    # Crear registros de profesionales
    execute_sql "
    INSERT INTO profesional (profesional_id, nombre, apellido, especialidad, registro_medico) VALUES
    (1, 'Juan', 'Cardiólogo', 'Cardiología', 'RM001'),
    (2, 'María', 'Neuróloga', 'Neurología', 'RM002'),
    (3, 'Carlos', 'Pediatra', 'Pediatría', 'RM003'),
    (4, 'Ana', 'Oncóloga', 'Oncología', 'RM004'),
    (5, 'Luis', 'Dermatólogo', 'Dermatología', 'RM005')
    ON CONFLICT (profesional_id) DO UPDATE SET
        nombre = EXCLUDED.nombre,
        apellido = EXCLUDED.apellido,
        especialidad = EXCLUDED.especialidad,
        registro_medico = EXCLUDED.registro_medico;
    "
    
    log "✅ Médicos especialistas creados"
}

# Función para crear pacientes
create_patients() {
    log "Creando 10 pacientes con historias clínicas..."
    
    local password_hash="bc44a1755bfe54b6efa2abb783f19144511eb277efc6f8f9088df7b67b46614b"
    
    # Crear usuarios pacientes
    execute_sql "
    INSERT INTO users (id, username, email, full_name, hashed_password, user_type, is_active, is_verified, created_at, updated_at, fhir_patient_id) VALUES
    (gen_random_uuid(), 'paciente1', 'paciente1@email.com', 'Ana García López', '$password_hash', 'patient', true, true, NOW(), NOW(), '1'),
    (gen_random_uuid(), 'paciente2', 'paciente2@email.com', 'Carlos Rodríguez Pérez', '$password_hash', 'patient', true, true, NOW(), NOW(), '2'),
    (gen_random_uuid(), 'paciente3', 'paciente3@email.com', 'María Fernández Silva', '$password_hash', 'patient', true, true, NOW(), NOW(), '3'),
    (gen_random_uuid(), 'paciente4', 'paciente4@email.com', 'José Martínez Gómez', '$password_hash', 'patient', true, true, NOW(), NOW(), '4'),
    (gen_random_uuid(), 'paciente5', 'paciente5@email.com', 'Laura Sánchez Ruiz', '$password_hash', 'patient', true, true, NOW(), NOW(), '5'),
    (gen_random_uuid(), 'paciente6', 'paciente6@email.com', 'Pedro López Vargas', '$password_hash', 'patient', true, true, NOW(), NOW(), '6'),
    (gen_random_uuid(), 'paciente7', 'paciente7@email.com', 'Carmen Díaz Torres', '$password_hash', 'patient', true, true, NOW(), NOW(), '7'),
    (gen_random_uuid(), 'paciente8', 'paciente8@email.com', 'Miguel Herrera Cruz', '$password_hash', 'patient', true, true, NOW(), NOW(), '8'),
    (gen_random_uuid(), 'paciente9', 'paciente9@email.com', 'Isabel Morales Jiménez', '$password_hash', 'patient', true, true, NOW(), NOW(), '9'),
    (gen_random_uuid(), 'paciente10', 'paciente10@email.com', 'Roberto Castillo Mendoza', '$password_hash', 'patient', true, true, NOW(), NOW(), '10')
    ON CONFLICT (username) DO NOTHING;
    "
    
    # Crear registros de pacientes
    execute_sql "
    INSERT INTO paciente (paciente_id, documento_id, nombre, apellido, sexo, fecha_nacimiento, contacto, ciudad, created_at) VALUES
    (1, '12345678', 'Ana', 'García López', 'femenino', '1985-03-15', '+57-300-1111111', 'Bogotá', NOW()),
    (2, '23456789', 'Carlos', 'Rodríguez Pérez', 'masculino', '1978-07-22', '+57-300-2222222', 'Medellín', NOW()),
    (3, '34567890', 'María', 'Fernández Silva', 'femenino', '1992-11-08', '+57-300-3333333', 'Cali', NOW()),
    (4, '45678901', 'José', 'Martínez Gómez', 'masculino', '1965-01-30', '+57-300-4444444', 'Barranquilla', NOW()),
    (5, '56789012', 'Laura', 'Sánchez Ruiz', 'femenino', '1988-09-14', '+57-300-5555555', 'Cartagena', NOW()),
    (6, '67890123', 'Pedro', 'López Vargas', 'masculino', '1975-12-03', '+57-300-6666666', 'Bucaramanga', NOW()),
    (7, '78901234', 'Carmen', 'Díaz Torres', 'femenino', '1990-05-27', '+57-300-7777777', 'Pereira', NOW()),
    (8, '89012345', 'Miguel', 'Herrera Cruz', 'masculino', '1982-08-16', '+57-300-8888888', 'Manizales', NOW()),
    (9, '90123456', 'Isabel', 'Morales Jiménez', 'femenino', '1995-02-11', '+57-300-9999999', 'Ibagué', NOW()),
    (10, '01234567', 'Roberto', 'Castillo Mendoza', 'masculino', '1970-10-25', '+57-300-0000000', 'Santa Marta', NOW())
    ON CONFLICT (documento_id, paciente_id) DO UPDATE SET
        nombre = EXCLUDED.nombre,
        apellido = EXCLUDED.apellido,
        sexo = EXCLUDED.sexo,
        fecha_nacimiento = EXCLUDED.fecha_nacimiento,
        contacto = EXCLUDED.contacto,
        ciudad = EXCLUDED.ciudad;
    "
    
    log "✅ Pacientes creados"
}

# Función para crear condiciones médicas (enfermedades)
create_medical_conditions() {
    log "Creando condiciones médicas y diagnósticos..."
    
    execute_sql "
    INSERT INTO condicion (condicion_id, paciente_id, documento_id, codigo, descripcion, gravedad, fecha_inicio, created_at) VALUES
    (1, 1, '12345678', 'I50.9', 'Insuficiencia cardíaca congestiva', 'moderada', '2024-01-15', NOW()),
    (2, 2, '23456789', 'G93.1', 'Lesión cerebral anóxica', 'severa', '2023-08-20', NOW()),
    (3, 3, '34567890', 'J45.9', 'Asma bronquial no especificada', 'leve', '2024-03-10', NOW()),
    (4, 4, '45678901', 'C78.0', 'Tumor maligno secundario de pulmón', 'severa', '2024-02-05', NOW()),
    (5, 5, '56789012', 'L40.9', 'Psoriasis no especificada', 'moderada', '2024-01-20', NOW()),
    (6, 6, '67890123', 'I25.9', 'Enfermedad cardíaca isquémica crónica', 'moderada', '2023-11-12', NOW()),
    (7, 7, '78901234', 'G40.9', 'Epilepsia no especificada', 'moderada', '2024-01-08', NOW()),
    (8, 8, '89012345', 'J44.1', 'Enfermedad pulmonar obstructiva crónica con exacerbación', 'severa', '2024-02-28', NOW()),
    (9, 9, '90123456', 'C50.9', 'Tumor maligno de mama', 'moderada', '2024-01-30', NOW()),
    (10, 10, '01234567', 'L30.9', 'Dermatitis no especificada', 'leve', '2024-03-05', NOW())
    ON CONFLICT (documento_id, condicion_id) DO UPDATE SET
        paciente_id = EXCLUDED.paciente_id,
        codigo = EXCLUDED.codigo,
        descripcion = EXCLUDED.descripcion,
        gravedad = EXCLUDED.gravedad,
        fecha_inicio = EXCLUDED.fecha_inicio;
    "
    
    log "✅ Condiciones médicas creadas"
}

# Función para crear medicamentos y prescripciones
create_medications() {
    log "Creando medicamentos y prescripciones..."
    
    execute_sql "
    INSERT INTO medicamento (medicamento_id, documento_id, paciente_id, prescriptor_id, nombre_medicamento, codigo_medicamento, dosis, frecuencia, via_administracion, fecha_inicio, fecha_fin, estado, notas, created_at) VALUES
    (1, '12345678', 1, 1, 'Enalapril', 'MED001', '10mg', '1 vez al día', 'oral', '2024-01-15', '2024-07-15', 'activo', 'Tomar con el desayuno', NOW()),
    (2, '12345678', 1, 1, 'Furosemida', 'MED002', '40mg', '1 vez al día', 'oral', '2024-01-15', '2024-07-15', 'activo', 'Tomar en ayunas', NOW()),
    (3, '23456789', 2, 2, 'Clopidogrel', 'MED003', '75mg', '1 vez al día', 'oral', '2023-08-20', '2024-08-20', 'activo', 'Antiagregante plaquetario', NOW()),
    (4, '34567890', 3, 3, 'Salbutamol', 'MED004', '100mcg', '2 puff cada 6 horas', 'inhalatoria', '2024-03-10', NULL, 'activo', 'Broncodilatador de rescate', NOW()),
    (5, '45678901', 4, 4, 'Morfina', 'MED005', '10mg', 'cada 8 horas', 'oral', '2024-02-05', NULL, 'activo', 'Para control del dolor', NOW()),
    (6, '56789012', 5, 5, 'Betametasona', 'MED006', '0.1%', '2 veces al día', 'topica', '2024-01-20', '2024-04-20', 'activo', 'Aplicar en lesiones', NOW()),
    (7, '67890123', 6, 1, 'Atorvastatina', 'MED007', '20mg', '1 vez al día', 'oral', '2023-11-12', NULL, 'activo', 'Tomar por la noche', NOW()),
    (8, '78901234', 7, 2, 'Carbamazepina', 'MED008', '200mg', '2 veces al día', 'oral', '2024-01-08', NULL, 'activo', 'Anticonvulsivante', NOW()),
    (9, '89012345', 8, 3, 'Prednisolona', 'MED009', '20mg', '1 vez al día', 'oral', '2024-02-28', '2024-03-28', 'completado', 'Corticoide', NOW()),
    (10, '90123456', 9, 4, 'Tamoxifeno', 'MED010', '20mg', '1 vez al día', 'oral', '2024-01-30', NULL, 'activo', 'Terapia hormonal', NOW())
    ON CONFLICT (documento_id, medicamento_id) DO UPDATE SET
        paciente_id = EXCLUDED.paciente_id,
        prescriptor_id = EXCLUDED.prescriptor_id,
        nombre_medicamento = EXCLUDED.nombre_medicamento,
        codigo_medicamento = EXCLUDED.codigo_medicamento,
        dosis = EXCLUDED.dosis,
        frecuencia = EXCLUDED.frecuencia,
        via_administracion = EXCLUDED.via_administracion,
        fecha_inicio = EXCLUDED.fecha_inicio,
        fecha_fin = EXCLUDED.fecha_fin,
        estado = EXCLUDED.estado,
        notas = EXCLUDED.notas;
    "
    
    log "✅ Medicamentos y prescripciones creados"
}

# Función para crear encuentros médicos
create_encounters() {
    log "Creando encuentros médicos..."
    
    execute_sql "
    INSERT INTO encuentro (encuentro_id, documento_id, paciente_id, profesional_id, fecha, motivo, diagnostico, created_at) VALUES
    (1, '12345678', 1, 1, '2024-01-15 10:00:00', 'Control cardiológico', 'Insuficiencia cardíaca', NOW()),
    (2, '23456789', 2, 2, '2024-02-20 14:30:00', 'Control neurológico post-ACV', 'Secuelas de ACV', NOW()),
    (3, '34567890', 3, 3, '2024-03-10 09:15:00', 'Crisis asmática', 'Asma bronquial', NOW()),
    (4, '45678901', 4, 4, '2024-02-05 08:00:00', 'Sesión de quimioterapia', 'Cáncer de pulmón', NOW()),
    (5, '56789012', 5, 5, '2024-01-20 11:00:00', 'Lesiones en piel', 'Psoriasis', NOW()),
    (6, '67890123', 6, 1, '2024-02-15 16:00:00', 'Control cardíaco', 'Cardiopatía isquémica', NOW()),
    (7, '78901234', 7, 2, '2024-01-08 22:30:00', 'Crisis epiléptica', 'Epilepsia', NOW()),
    (8, '89012345', 8, 3, '2024-02-28 06:00:00', 'Exacerbación EPOC', 'EPOC exacerbada', NOW()),
    (9, '90123456', 9, 4, '2024-01-30 07:00:00', 'Mastectomía', 'Cáncer de mama', NOW()),
    (10, '01234567', 10, 5, '2024-03-05 15:30:00', 'Lesiones dérmicas', 'Dermatitis atópica', NOW())
    ON CONFLICT (documento_id, encuentro_id) DO UPDATE SET
        paciente_id = EXCLUDED.paciente_id,
        profesional_id = EXCLUDED.profesional_id,
        fecha = EXCLUDED.fecha,
        motivo = EXCLUDED.motivo,
        diagnostico = EXCLUDED.diagnostico;
    "
    
    log "✅ Encuentros médicos creados"
}

# Función para crear observaciones médicas
create_observations() {
    log "Creando observaciones médicas..."
    
    execute_sql "
    INSERT INTO observacion (observacion_id, documento_id, paciente_id, referencia_encuentro, tipo, valor, unidad, fecha, created_at) VALUES
    (1, '12345678', 1, 1, 'presion_sistolica', '140', 'mmHg', '2024-01-15 10:15:00', NOW()),
    (2, '12345678', 1, 1, 'presion_diastolica', '90', 'mmHg', '2024-01-15 10:15:00', NOW()),
    (3, '23456789', 2, 2, 'glucosa', '180', 'mg/dL', '2024-02-20 09:00:00', NOW()),
    (4, '34567890', 3, 3, 'frecuencia_cardiaca', '98', 'bpm', '2024-03-10 09:20:00', NOW()),
    (5, '45678901', 4, 4, 'hemoglobina', '8.5', 'g/dL', '2024-02-05 07:30:00', NOW()),
    (6, '56789012', 5, 5, 'examen_dermatologico', 'Lesiones eritematosas', 'observacion', '2024-01-20 11:15:00', NOW()),
    (7, '67890123', 6, 6, 'presion_sistolica', '125', 'mmHg', '2024-02-15 16:10:00', NOW()),
    (8, '78901234', 7, 7, 'examen_neurologico', 'Sin déficit focal', 'observacion', '2024-01-08 23:00:00', NOW()),
    (9, '89012345', 8, 8, 'saturacion_oxigeno', '89', '%', '2024-02-28 06:30:00', NOW()),
    (10, '90123456', 9, 9, 'biopsia', 'Carcinoma ductal invasivo', 'resultado', '2024-02-05 12:00:00', NOW())
    ON CONFLICT (documento_id, observacion_id) DO UPDATE SET
        paciente_id = EXCLUDED.paciente_id,
        referencia_encuentro = EXCLUDED.referencia_encuentro,
        tipo = EXCLUDED.tipo,
        valor = EXCLUDED.valor,
        unidad = EXCLUDED.unidad,
        fecha = EXCLUDED.fecha;
    "
    
    log "✅ Observaciones médicas creadas"
}

# Función para mostrar resumen
show_summary() {
    log "📊 RESUMEN DE DATOS CREADOS"
    echo "================================"
    
    local users=$(docker exec citus-coordinator psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM users;" | tr -d ' ')
    local patients=$(docker exec citus-coordinator psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM paciente;" | tr -d ' ')
    local doctors=$(docker exec citus-coordinator psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM profesional;" | tr -d ' ')
    local conditions=$(docker exec citus-coordinator psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM condicion;" | tr -d ' ')
    local medications=$(docker exec citus-coordinator psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM medicamento;" | tr -d ' ')
    local encounters=$(docker exec citus-coordinator psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM encuentro;" | tr -d ' ')
    local observations=$(docker exec citus-coordinator psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM observacion;" | tr -d ' ')
    
    info "Total usuarios: $users"
    info "Total pacientes: $patients"
    info "Total médicos: $doctors"
    info "Total condiciones médicas: $conditions"
    info "Total medicamentos: $medications"
    info "Total encuentros: $encounters"
    info "Total observaciones: $observations"
    
    echo ""
    log "🔐 CREDENCIALES DE ACCESO"
    echo "========================"
    info "Administradores: admin1/secret, admin2/secret"
    info "Auditor: auditor1/secret"
    info "Médicos: cardiologo1/secret, neurologo1/secret, pediatra1/secret, oncologo1/secret, dermatologo1/secret"
    info "Pacientes: paciente1/secret hasta paciente10/secret"
    
    echo ""
    log "🌐 Acceso al sistema:"
    info "Login: http://localhost:8000/login"
    info "API Docs: http://localhost:8000/docs"
}

# Función principal
main() {
    log "🚀 Iniciando poblado de base de datos del Sistema FHIR"
    log "======================================================"
    
    check_db_connection
    check_existing_data
    
    info "Iniciando creación de datos..."
    
    create_system_users
    create_doctors
    create_patients
    create_medical_conditions
    create_medications
    create_encounters
    create_observations
    
    show_summary
    
    log "✅ ¡Poblado de base de datos completado exitosamente!"
}

# Verificar si se debe ejecutar automáticamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ "$1" == "--auto" ]]; then
        # Ejecución automática desde setup.sh
        main
    else
        # Ejecución manual - preguntar confirmación
        echo -e "${BLUE}Sistema FHIR - Poblado de Base de Datos${NC}"
        echo "======================================"
        echo ""
        echo "Este script creará datos de ejemplo incluyendo:"
        echo "• 2 administradores + 1 auditor"
        echo "• 5 médicos especialistas"
        echo "• 10 pacientes con historias clínicas completas"
        echo "• Condiciones médicas, medicamentos y encuentros"
        echo ""
        echo -n "¿Deseas continuar? (s/N): "
        read -r response
        
        if [[ "$response" =~ ^[Ss]$ ]]; then
            main
        else
            info "Operación cancelada por el usuario"
            exit 0
        fi
    fi
fi