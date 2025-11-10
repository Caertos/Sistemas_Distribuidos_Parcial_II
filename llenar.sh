#!/bin/bash

# llenar.sh
# Script para cargar datos de prueba completos en el sistema FHIR distribuido
# 
# Este script inserta:
# - 10 clientes (pacientes)  
# - 5 médicos distintos
# - 2 administradores
# - 1 auditor (mantiene el existente)
# - Datos clínicos coherentes y realistas
#
# Desarrollado por: Sistema FHIR
# Fecha: $(date '+%Y-%m-%d')

set -e  # Salir si cualquier comando falla
set -u  # Salir si se usa una variable no definida

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'  
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración de base de datos
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="hce" 
DB_USER="postgres"
DB_PASS="postgres_pass"

# Función para logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[PASO]${NC} $1"
}

# Función para ejecutar SQL
execute_sql() {
    local sql="$1"  
    local description="$2"
    
    log_info "Ejecutando: $description"
    
    if ! PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$sql" > /dev/null 2>&1; then
        log_error "Error ejecutando: $description"
        return 1
    fi
    
    log_info "✅ Completado: $description"
}

# Función para verificar conexión a BD
check_database() {
    log_step "🔍 Verificando conexión a base de datos..."
    
    if ! PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        log_error "No se puede conectar a la base de datos"
        log_error "Asegúrate de que Docker Compose esté ejecutándose: docker compose up -d"
        exit 1
    fi
    
    log_info "✅ Conexión exitosa a base de datos"
}

# Función para hash de contraseña (usando la función simple_hash del sistema)
create_temp_hash_function() {
    log_info "Creando función temporal para hash de contraseñas..."
    
    local sql="
    CREATE OR REPLACE FUNCTION temp_simple_hash(password TEXT)
    RETURNS TEXT AS \$\$
    BEGIN
        RETURN encode(digest(password || 'demo_salt_fhir', 'sha256'), 'hex');
    END;
    \$\$ LANGUAGE plpgsql;
    "
    
    execute_sql "$sql" "Crear función hash temporal"
}

# Función para limpiar función temporal
cleanup_temp_functions() {
    log_info "Limpiando funciones temporales..."
    execute_sql "DROP FUNCTION IF EXISTS temp_simple_hash(TEXT);" "Eliminar función hash temporal"
}

# Función principal de inserción de datos
insert_data() {
    log_step "📊 Insertando datos de prueba..."
    
    # Crear la función hash temporal
    create_temp_hash_function
    
    # 1. MÉDICOS ADICIONALES Y VÍNCULOS CON USUARIOS
    log_info "👨‍⚕️ Creando médicos adicionales y vinculando usuarios existentes..."
    
    local medicos_sql="
    -- Actualizar usuario médico existente para vincularlo con profesional
    UPDATE users 
    SET fhir_practitioner_id = '1',
        full_name = 'Dr. Juan García'
    WHERE username = 'medico';
    
    -- Crear usuarios para profesionales existentes  
    INSERT INTO users (username, email, hashed_password, full_name, user_type, is_active, is_verified, fhir_practitioner_id)
    VALUES 
        ('dra.lopez', 'maria.lopez@hospital.com', temp_simple_hash('pediatra123'), 'Dra. María López', 'practitioner', true, true, '2'),
        ('dr.rodriguez', 'carlos.rodriguez@hospital.com', temp_simple_hash('cardio123'), 'Dr. Carlos Rodríguez', 'practitioner', true, true, '3'),
        ('dra.martinez', 'ana.martinez@hospital.com', temp_simple_hash('neuro123'), 'Dra. Ana Martínez', 'practitioner', true, true, '4'),
        ('dr.hernandez', 'luis.hernandez@hospital.com', temp_simple_hash('trauma123'), 'Dr. Luis Hernández', 'practitioner', true, true, '5')
    ON CONFLICT (username) DO UPDATE SET
        email = EXCLUDED.email,
        full_name = EXCLUDED.full_name,
        fhir_practitioner_id = EXCLUDED.fhir_practitioner_id,
        updated_at = NOW();
    
    -- Asignar rol de practitioner a nuevos usuarios médicos
    INSERT INTO user_roles (user_id, role_id)
    SELECT u.id, r.id 
    FROM users u, roles r 
    WHERE u.username IN ('dra.lopez', 'dr.rodriguez', 'dra.martinez', 'dr.hernandez') 
    AND r.name = 'practitioner'
    ON CONFLICT (user_id, role_id) DO NOTHING;
    "
    
    execute_sql "$medicos_sql" "Crear vínculos usuario-médico"
    
    # 2. ADMINISTRADORES ADICIONALES
    log_info "👤 Creando administrador adicional..."
    
    local admin_sql="
    INSERT INTO users (username, email, hashed_password, full_name, user_type, is_active, is_verified)
    VALUES 
        ('admin2', 'admin2@hospital.com', temp_simple_hash('admin2_123'), 'Administrador Auxiliar', 'admin', true, true)
    ON CONFLICT (username) DO UPDATE SET
        email = EXCLUDED.email,
        full_name = EXCLUDED.full_name,
        updated_at = NOW();
    
    -- Asignar rol de admin
    INSERT INTO user_roles (user_id, role_id)
    SELECT u.id, r.id 
    FROM users u, roles r 
    WHERE u.username = 'admin2' AND r.name = 'admin'
    ON CONFLICT (user_id, role_id) DO NOTHING;
    "
    
    execute_sql "$admin_sql" "Crear administrador adicional"
    
    # 3. PACIENTES ADICIONALES (5 + 5 nuevos para totalizar 10)
    log_info "🏥 Creando pacientes adicionales y usuarios asociados..."
    
    local pacientes_sql="
    -- Insertar nuevos pacientes
    INSERT INTO paciente (paciente_id, documento_id, nombre, apellido, sexo, fecha_nacimiento, contacto, ciudad)
    VALUES 
        (6, 1006789012, 'Ana', 'Morales', 'femenino', '1987-09-12', '3001234567', 'Bogotá'),
        (7, 1007890123, 'Miguel', 'Vargas', 'masculino', '1993-04-25', '3109876543', 'Medellín'),
        (8, 1008901234, 'Sofia', 'Ruiz', 'femenino', '1991-12-03', '3207654321', 'Cali'),
        (9, 1009012345, 'Diego', 'Mendoza', 'masculino', '1989-07-18', '3156789012', 'Barranquilla'), 
        (10, 1010123456, 'Valentina', 'Cruz', 'femenino', '1994-02-14', '3145678901', 'Cartagena')
    ON CONFLICT (documento_id, paciente_id) DO NOTHING;
    
    -- Crear usuarios para pacientes nuevos
    INSERT INTO users (username, email, hashed_password, full_name, user_type, is_active, is_verified, fhir_patient_id)
    VALUES 
        ('ana.morales', 'ana.morales@email.com', temp_simple_hash('paciente123'), 'Ana Morales', 'patient', true, true, '6'),
        ('miguel.vargas', 'miguel.vargas@email.com', temp_simple_hash('paciente123'), 'Miguel Vargas', 'patient', true, true, '7'),
        ('sofia.ruiz', 'sofia.ruiz@email.com', temp_simple_hash('paciente123'), 'Sofia Ruiz', 'patient', true, true, '8'),
        ('diego.mendoza', 'diego.mendoza@email.com', temp_simple_hash('paciente123'), 'Diego Mendoza', 'patient', true, true, '9'),
        ('valentina.cruz', 'valentina.cruz@email.com', temp_simple_hash('paciente123'), 'Valentina Cruz', 'patient', true, true, '10')
    ON CONFLICT (username) DO UPDATE SET
        email = EXCLUDED.email,
        full_name = EXCLUDED.full_name,
        fhir_patient_id = EXCLUDED.fhir_patient_id,
        updated_at = NOW();
    
    -- Actualizar usuario paciente existente para vincularlo
    UPDATE users 
    SET fhir_patient_id = '2',
        full_name = 'María García'
    WHERE username = 'paciente';
    
    -- Asignar rol de patient a nuevos usuarios pacientes
    INSERT INTO user_roles (user_id, role_id)
    SELECT u.id, r.id 
    FROM users u, roles r 
    WHERE u.username IN ('ana.morales', 'miguel.vargas', 'sofia.ruiz', 'diego.mendoza', 'valentina.cruz') 
    AND r.name = 'patient'
    ON CONFLICT (user_id, role_id) DO NOTHING;
    "
    
    execute_sql "$pacientes_sql" "Crear pacientes adicionales"
    
    # 4. ENCUENTROS MÉDICOS REALISTAS
    log_info "📋 Creando encuentros médicos adicionales..."
    
    local encuentros_sql="
    INSERT INTO encuentro (paciente_id, documento_id, fecha, motivo, diagnostico, profesional_id)
    VALUES 
        -- Ana Morales - Dra. López (Pediatría - aunque es adulto, consulta ginecológica)
        (6, 1006789012, '2025-11-08 10:30:00', 'Control ginecológico anual', 'Examen normal', 2),
        -- Miguel Vargas - Dr. García (Medicina General)  
        (7, 1007890123, '2025-11-07 14:15:00', 'Dolor de cabeza recurrente', 'Cefalea tensional', 1),
        -- Sofia Ruiz - Dr. Rodríguez (Cardiología)
        (8, 1008901234, '2025-11-06 09:00:00', 'Palpitaciones', 'Arritmia leve', 3),
        -- Diego Mendoza - Dr. Hernández (Traumatología)
        (9, 1009012345, '2025-11-05 16:45:00', 'Dolor lumbar', 'Lumbalgia mecánica', 5),
        -- Valentina Cruz - Dra. Martínez (Neurología)
        (10, 1010123456, '2025-11-04 11:20:00', 'Migrañas frecuentes', 'Migraña sin aura', 4)
    ON CONFLICT DO NOTHING;
    "
    
    execute_sql "$encuentros_sql" "Crear encuentros médicos"
    
    # 5. CONDICIONES CON CÓDIGOS CIE ACTUALIZADOS  
    log_info "🏷️ Insertando condiciones con códigos CIE realistas..."
    
    local condiciones_sql="
    INSERT INTO condicion (paciente_id, documento_id, codigo, descripcion, gravedad, fecha_inicio)
    VALUES 
        -- Ana Morales
        (6, 1006789012, 'Z30.9', 'Consulta anticonceptiva', 'Leve', '2025-11-08'),
        -- Miguel Vargas  
        (7, 1007890123, 'G44.2', 'Cefalea de tipo tensional', 'Moderada', '2025-10-15'),
        -- Sofia Ruiz
        (8, 1008901234, 'I49.9', 'Arritmia cardíaca no especificada', 'Moderada', '2025-11-06'),
        -- Diego Mendoza
        (9, 1009012345, 'M54.5', 'Dolor lumbar bajo', 'Moderada', '2025-10-20'),
        -- Valentina Cruz
        (10, 1010123456, 'G43.9', 'Migraña sin especificación', 'Moderada', '2025-09-01'),
        -- Condiciones adicionales para pacientes existentes
        (1, 1001234567, 'Z00.0', 'Examen médico general', 'Leve', '2025-01-10'),
        (4, 1004567890, 'Z23', 'Necesidad de inmunización', 'Leve', '2025-01-13')
    ON CONFLICT DO NOTHING;
    "
    
    execute_sql "$condiciones_sql" "Insertar condiciones médicas"
    
    # 6. SIGNOS VITALES REALISTAS
    log_info "💓 Insertando signos vitales para todos los pacientes..."
    
    local signos_sql="
    INSERT INTO signos_vitales (documento_id, paciente_id, fecha, presion_sistolica, presion_diastolica, 
                               frecuencia_cardiaca, frecuencia_respiratoria, temperatura, saturacion_oxigeno, 
                               peso, talla, imc)
    VALUES 
        -- Ana Morales (29 años)
        (1006789012, 6, '2025-11-08 10:35:00', 115, 75, 68, 16, 36.2, 98, 58.5, 162, 22.3),
        -- Miguel Vargas (31 años)
        (1007890123, 7, '2025-11-07 14:20:00', 128, 82, 74, 18, 36.8, 97, 78.2, 175, 25.5),
        -- Sofia Ruiz (33 años)  
        (1008901234, 8, '2025-11-06 09:10:00', 135, 88, 85, 19, 36.4, 96, 65.3, 168, 23.1),
        -- Diego Mendoza (35 años)
        (1009012345, 9, '2025-11-05 16:50:00', 142, 90, 72, 17, 36.6, 98, 82.1, 180, 25.3),
        -- Valentina Cruz (30 años)
        (1010123456, 10, '2025-11-04 11:25:00', 118, 78, 76, 16, 36.3, 99, 55.8, 160, 21.8),
        -- Signos adicionales para pacientes existentes
        (1001234567, 1, '2025-11-10 09:00:00', 122, 78, 70, 16, 36.5, 98, 75.0, 175, 24.5),
        (1004567890, 4, '2025-11-09 10:30:00', 105, 65, 88, 22, 36.1, 99, 22.5, 110, 18.6)
    ON CONFLICT DO NOTHING;
    "
    
    execute_sql "$signos_sql" "Insertar signos vitales"
    
    # 7. MEDICAMENTOS PRESCRITOS
    log_info "💊 Insertando medicamentos y prescripciones..."
    
    local medicamentos_sql="
    INSERT INTO medicamento (documento_id, paciente_id, codigo_medicamento, nombre_medicamento, 
                           dosis, via_administracion, frecuencia, fecha_inicio, prescriptor_id, estado)
    VALUES 
        -- Para paciente con gastritis (Laura Ramírez)
        (1002345678, 2, 'A02BC01', 'Omeprazol', '20mg', 'oral', 'cada 24 horas', '2024-06-01', 1, 'activo'),
        -- Para paciente con hipertensión (Jorge Torres)  
        (1003456789, 3, 'C09AA02', 'Enalapril', '10mg', 'oral', 'cada 12 horas', '2020-03-15', 3, 'activo'),
        -- Para Miguel Vargas (cefalea)
        (1007890123, 7, 'N02BE01', 'Paracetamol', '500mg', 'oral', 'cada 8 horas', '2025-11-07', 1, 'activo'),
        -- Para Sofia Ruiz (arritmia)
        (1008901234, 8, 'C01BD01', 'Amiodarona', '200mg', 'oral', 'cada 24 horas', '2025-11-06', 3, 'activo'),
        -- Para Diego Mendoza (lumbalgia)
        (1009012345, 9, 'M01AE01', 'Ibuprofeno', '400mg', 'oral', 'cada 8 horas', '2025-11-05', 5, 'activo'),
        -- Para Valentina Cruz (migraña)
        (1010123456, 10, 'N02CC01', 'Sumatriptán', '50mg', 'oral', 'según necesidad', '2025-11-04', 4, 'activo')
    ON CONFLICT DO NOTHING;
    "
    
    execute_sql "$medicamentos_sql" "Insertar medicamentos"
    
    # 8. OBSERVACIONES ADICIONALES
    log_info "📊 Insertando observaciones clínicas adicionales..."
    
    local observaciones_sql="
    INSERT INTO observacion (paciente_id, documento_id, tipo, valor, unidad, fecha)
    VALUES 
        -- Ana Morales
        (6, 1006789012, 'Presión Arterial', '115/75', 'mmHg', '2025-11-08 10:35:00'),
        (6, 1006789012, 'Peso', '58.5', 'kg', '2025-11-08 10:36:00'),
        (6, 1006789012, 'IMC', '22.3', 'kg/m²', '2025-11-08 10:37:00'),
        -- Miguel Vargas
        (7, 1007890123, 'Presión Arterial', '128/82', 'mmHg', '2025-11-07 14:20:00'),
        (7, 1007890123, 'Intensidad Dolor', '6', 'escala 1-10', '2025-11-07 14:21:00'),
        -- Sofia Ruiz  
        (8, 1008901234, 'Presión Arterial', '135/88', 'mmHg', '2025-11-06 09:10:00'),
        (8, 1008901234, 'Frecuencia Cardíaca', '85', 'bpm', '2025-11-06 09:11:00'),
        -- Diego Mendoza
        (9, 1009012345, 'Presión Arterial', '142/90', 'mmHg', '2025-11-05 16:50:00'),
        (9, 1009012345, 'Dolor Lumbar', '7', 'escala 1-10', '2025-11-05 16:51:00'),
        -- Valentina Cruz
        (10, 1010123456, 'Presión Arterial', '118/78', 'mmHg', '2025-11-04 11:25:00'),
        (10, 1010123456, 'Frecuencia Cefalea', '15', 'días/mes', '2025-11-04 11:26:00')
    ON CONFLICT DO NOTHING;
    "
    
    execute_sql "$observaciones_sql" "Insertar observaciones clínicas"
    
    # 9. ALERGIAS E INTOLERANCIAS
    log_info "⚠️ Insertando alergias e intolerancias..."
    
    local alergias_sql="
    INSERT INTO alergia_intolerancia (documento_id, paciente_id, tipo, categoria, descripcion_sustancia, 
                                    severidad, manifestacion, fecha_inicio, estado)
    VALUES 
        (1002345678, 2, 'alergia', 'medicamento', 'Penicilina', 'moderada', 'Erupción cutánea', '2018-05-12', 'activa'),
        (1007890123, 7, 'intolerancia', 'comida', 'Lactosa', 'leve', 'Molestias digestivas', '2020-03-01', 'activa'),
        (1008901234, 8, 'alergia', 'ambiente', 'Polen de gramíneas', 'leve', 'Rinitis', '2019-04-15', 'activa'),
        (1010123456, 10, 'alergia', 'medicamento', 'Aspirina', 'severa', 'Broncoespasmo', '2021-09-22', 'activa')
    ON CONFLICT DO NOTHING;
    "
    
    execute_sql "$alergias_sql" "Insertar alergias e intolerancias"
    
    # Limpiar función temporal
    cleanup_temp_functions
    
    log_info "✅ Todos los datos han sido insertados exitosamente"
}

# Función para mostrar resumen de datos insertados
show_summary() {
    log_step "📈 Resumen de datos insertados..."
    
    local summary_sql="
    SELECT 'RESUMEN FINAL DE DATOS:' as resumen;
    
    SELECT 
        'Usuarios totales' as tipo,
        COUNT(*) as cantidad
    FROM users
    UNION ALL
    SELECT 
        'Pacientes totales' as tipo,
        COUNT(*) as cantidad  
    FROM paciente
    UNION ALL
    SELECT 
        'Profesionales totales' as tipo,
        COUNT(*) as cantidad
    FROM profesional
    UNION ALL
    SELECT 
        'Encuentros médicos' as tipo,
        COUNT(*) as cantidad
    FROM encuentro
    UNION ALL
    SELECT 
        'Condiciones médicas' as tipo,
        COUNT(*) as cantidad
    FROM condicion
    UNION ALL
    SELECT 
        'Medicamentos activos' as tipo,
        COUNT(*) as cantidad
    FROM medicamento
    WHERE estado = 'activo'
    UNION ALL
    SELECT 
        'Observaciones clínicas' as tipo,
        COUNT(*) as cantidad
    FROM observacion
    UNION ALL
    SELECT 
        'Signos vitales' as tipo,
        COUNT(*) as cantidad
    FROM signos_vitales
    UNION ALL
    SELECT 
        'Alergias registradas' as tipo,
        COUNT(*) as cantidad
    FROM alergia_intolerancia;
    
    SELECT 'USUARIOS POR TIPO:' as detalle;
    SELECT user_type, COUNT(*) as cantidad
    FROM users 
    WHERE is_active = true
    GROUP BY user_type
    ORDER BY user_type;
    "
    
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$summary_sql"
}

# Función principal
main() {
    clear
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}   SCRIPT DE CARGA DE DATOS     ${NC}"
    echo -e "${BLUE}   Sistema FHIR Distribuido     ${NC}"
    echo -e "${BLUE}=================================${NC}"
    echo ""
    
    log_step "🚀 Iniciando carga de datos de prueba..."
    
    # Verificar conexión a BD
    check_database
    
    # Insertar todos los datos
    insert_data
    
    # Mostrar resumen
    show_summary
    
    echo ""
    echo -e "${GREEN}=================================${NC}"
    echo -e "${GREEN}     ✅ CARGA COMPLETADA         ${NC}"  
    echo -e "${GREEN}=================================${NC}"
    echo ""
    echo -e "${YELLOW}📋 USUARIOS CREADOS:${NC}"
    echo "   • 2 Administradores: admin, admin2"
    echo "   • 5 Médicos: medico, dra.lopez, dr.rodriguez, dra.martinez, dr.hernandez"  
    echo "   • 10 Pacientes: paciente, ana.morales, miguel.vargas, sofia.ruiz, diego.mendoza, valentina.cruz + 4 existentes"
    echo "   • 1 Auditor: auditor (existente)"
    echo ""
    echo -e "${YELLOW}🔑 CONTRASEÑAS:${NC}"
    echo "   • Administradores: admin123, admin2_123"
    echo "   • Médicos: medico123, pediatra123, cardio123, neuro123, trauma123"
    echo "   • Pacientes: paciente123 (para todos)"
    echo "   • Auditor: auditor123"
    echo ""
    echo -e "${YELLOW}🔗 ENDPOINT DE PRUEBA:${NC}"
    echo "   curl -X POST http://localhost:8000/auth/login \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"username\": \"dra.martinez\", \"password\": \"neuro123\"}'"  
    echo ""
    echo -e "${GREEN}🎉 ¡Datos cargados exitosamente! El sistema está listo para usar.${NC}"
}

# Ejecutar script principal
main "$@"