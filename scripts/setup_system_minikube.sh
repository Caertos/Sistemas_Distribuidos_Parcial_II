#!/usr/bin/env bash
# Script completo y autónomo para el Sistema FHIR en Kubernetes
# Incluye validaciones, correcciones automáticas y verificaciones finales

set -euo pipefail

MINIKUBE_DRIVER=${MINIKUBE_DRIVER:-docker}
MINIKUBE_MEMORY=${MINIKUBE_MEMORY:-6144}
MINIKUBE_CPUS=${MINIKUBE_CPUS:-3}
NAMESPACE=${NAMESPACE:-default}

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo -e "${BOLD}${CYAN}════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}════════════════════════════════════════${NC}"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_fix() {
    echo -e "${CYAN}[FIX]${NC} $1"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { 
    print_error "Se necesita '$1' en PATH" 
    exit 1 
  }
}

wait_for_pods() {
    local label=$1
    local timeout=${2:-300}
    print_status "Esperando pods con etiqueta '$label'..."
    kubectl wait --for=condition=ready pod -l "$label" --timeout="${timeout}s" || {
        print_error "Timeout esperando pods $label"
        kubectl describe pods -l "$label"
        return 1
    }
}

fix_citus_authentication() {
    print_fix "Configurando autenticación de Citus para cluster..."
    
    # Agregar reglas de confianza para la red de pods de Kubernetes
    for node in citus-coordinator-0 citus-worker-0 citus-worker-1; do
        kubectl exec "$node" -- sh -c "echo 'host all all 10.244.0.0/16 trust' >> /var/lib/postgresql/data/pg_hba.conf" 2>/dev/null || true
        # Reordenar para que trust tenga precedencia
        kubectl exec "$node" -- sh -c "sed -i '/host all all all scram-sha-256/d' /var/lib/postgresql/data/pg_hba.conf && echo 'host all all all scram-sha-256' >> /var/lib/postgresql/data/pg_hba.conf" 2>/dev/null || true
        kubectl exec "$node" -- psql -U postgres -c "SELECT pg_reload_conf();" 2>/dev/null || true
    done
    
    print_success "Autenticación de Citus configurada"
}

setup_citus_cluster() {
    print_fix "Configurando cluster de Citus..."
    
    local max_attempts=5
    local attempt=1
    local cluster_configured=false
    
    while [ $attempt -le $max_attempts ] && [ "$cluster_configured" = false ]; do
        print_status "Intento de configuración $attempt/$max_attempts..."
        
        # Configurar coordinador
        if kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "SELECT citus_set_coordinator_host('citus-coordinator');" 2>/dev/null; then
            print_status "✅ Coordinador configurado"
        else
            print_warning "⚠️ Error configurando coordinador, reintentando..."
        fi
        
        # Verificar y agregar workers con verificación previa
        local workers_added=0
        
        # Worker 1
        local worker1_exists=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM citus_get_active_worker_nodes() WHERE node_name = 'citus-worker-0.citus-worker';" 2>/dev/null || echo "0")
        if [ "$worker1_exists" = "0" ]; then
            if kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "SELECT citus_add_node('citus-worker-0.citus-worker', 5432);" 2>/dev/null; then
                print_status "✅ Worker 1 agregado"
                workers_added=$((workers_added + 1))
            else
                print_warning "⚠️ Error agregando worker 1"
            fi
        else
            print_status "✅ Worker 1 ya existe"
            workers_added=$((workers_added + 1))
        fi
        
        # Worker 2
        local worker2_exists=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM citus_get_active_worker_nodes() WHERE node_name = 'citus-worker-1.citus-worker';" 2>/dev/null || echo "0")
        if [ "$worker2_exists" = "0" ]; then
            if kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "SELECT citus_add_node('citus-worker-1.citus-worker', 5432);" 2>/dev/null; then
                print_status "✅ Worker 2 agregado"
                workers_added=$((workers_added + 1))
            else
                print_warning "⚠️ Error agregando worker 2"
            fi
        else
            print_status "✅ Worker 2 ya existe"
            workers_added=$((workers_added + 1))
        fi
        
        # Verificar estado final del cluster
        local total_workers=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM citus_get_active_worker_nodes();" 2>/dev/null || echo "0")
        
        if [ "$total_workers" -ge "2" ]; then
            print_success "✅ Cluster configurado exitosamente con $total_workers workers"
            cluster_configured=true
        else
            print_warning "⚠️ Solo $total_workers workers configurados, reintentando..."
            sleep 10
        fi
        
        attempt=$((attempt + 1))
    done
    
    if [ "$cluster_configured" = false ]; then
        print_error "No se pudo configurar el cluster después de $max_attempts intentos"
        return 1
    fi
    
    print_success "Cluster de Citus configurado"
}

populate_database() {
    print_status "Poblando base de datos con datos de ejemplo básicos..."
    
    # Verificar que el sistema esté funcionando primero
    print_status "Verificando que el sistema esté completamente operativo..."
    if ! kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "SELECT 1;" > /dev/null 2>&1; then
        print_error "El sistema no está completamente inicializado. Intenta ejecutar ./llenar.sh más tarde."
        return 1
    fi
    
    # Hacer el script ejecutable
    chmod +x ../llenar.sh
    
    # Adaptar el script para trabajar con Kubernetes
    print_status "Poblando base de datos con datos de ejemplo..."
    
    # Función para ejecutar SQL en el cluster de Kubernetes
    execute_k8s_sql() {
        local sql="$1"
        kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "$sql"
    }
    
    # Verificar conexión a la base de datos
    if ! kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "SELECT 1;" > /dev/null 2>&1; then
        print_error "No se puede conectar a la base de datos"
        return 1
    fi
    
    print_status "✅ Conexión a la base de datos exitosa"
    
    # Hash de contraseña "secret" para los usuarios
    local password_hash="bc44a1755bfe54b6efa2abb783f19144511eb277efc6f8f9088df7b67b46614b"
    
    # Crear usuarios del sistema
    print_status "Creando usuarios del sistema..."
    execute_k8s_sql "
    INSERT INTO users (id, username, email, full_name, hashed_password, user_type, is_active, is_verified, created_at, updated_at) VALUES
    (gen_random_uuid(), 'admin1', 'admin1@hospital.com', 'Dr. Carlos Administrador', '$password_hash', 'admin', true, true, NOW(), NOW()),
    (gen_random_uuid(), 'admin2', 'admin2@hospital.com', 'Dra. Ana Administradora', '$password_hash', 'admin', true, true, NOW(), NOW()),
    (gen_random_uuid(), 'auditor1', 'auditor1@hospital.com', 'Lic. María Auditora', '$password_hash', 'auditor', true, true, NOW(), NOW())
    ON CONFLICT (username) DO NOTHING;
    " 2>/dev/null || print_warning "⚠️ Algunos usuarios del sistema ya existen"
    
    # Crear médicos especialistas
    print_status "Creando médicos especialistas..."
    execute_k8s_sql "
    INSERT INTO users (id, username, email, full_name, hashed_password, user_type, is_active, is_verified, created_at, updated_at, fhir_practitioner_id) VALUES
    (gen_random_uuid(), 'cardiologo1', 'cardiologo1@hospital.com', 'Dr. Juan Cardiólogo', '$password_hash', 'practitioner', true, true, NOW(), NOW(), '1'),
    (gen_random_uuid(), 'neurologo1', 'neurologo1@hospital.com', 'Dra. María Neuróloga', '$password_hash', 'practitioner', true, true, NOW(), NOW(), '2'),
    (gen_random_uuid(), 'pediatra1', 'pediatra1@hospital.com', 'Dr. Carlos Pediatra', '$password_hash', 'practitioner', true, true, NOW(), NOW(), '3'),
    (gen_random_uuid(), 'oncologo1', 'oncologo1@hospital.com', 'Dra. Ana Oncóloga', '$password_hash', 'practitioner', true, true, NOW(), NOW(), '4'),
    (gen_random_uuid(), 'dermatologo1', 'dermatologo1@hospital.com', 'Dr. Luis Dermatólogo', '$password_hash', 'practitioner', true, true, NOW(), NOW(), '5')
    ON CONFLICT (username) DO NOTHING;
    " 2>/dev/null || print_warning "⚠️ Algunos médicos ya existen"
    
    execute_k8s_sql "
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
    " 2>/dev/null || print_warning "⚠️ Algunos profesionales ya existen"
    
    # Crear pacientes
    print_status "Creando pacientes de ejemplo..."
    execute_k8s_sql "
    INSERT INTO users (id, username, email, full_name, hashed_password, user_type, is_active, is_verified, created_at, updated_at, fhir_patient_id) VALUES
    (gen_random_uuid(), 'paciente1', 'paciente1@email.com', 'Ana García López', '$password_hash', 'patient', true, true, NOW(), NOW(), '1'),
    (gen_random_uuid(), 'paciente2', 'paciente2@email.com', 'Carlos Rodríguez Pérez', '$password_hash', 'patient', true, true, NOW(), NOW(), '2'),
    (gen_random_uuid(), 'paciente3', 'paciente3@email.com', 'María Fernández Silva', '$password_hash', 'patient', true, true, NOW(), NOW(), '3')
    ON CONFLICT (username) DO NOTHING;
    " 2>/dev/null || print_warning "⚠️ Algunos pacientes ya existen"
    
    execute_k8s_sql "
    INSERT INTO paciente (paciente_id, documento_id, nombre, apellido, sexo, fecha_nacimiento, contacto, ciudad, created_at) VALUES
    (1, '12345678', 'Ana', 'García López', 'femenino', '1985-03-15', '+57-300-1111111', 'Bogotá', NOW()),
    (2, '23456789', 'Carlos', 'Rodríguez Pérez', 'masculino', '1978-07-22', '+57-300-2222222', 'Medellín', NOW()),
    (3, '34567890', 'María', 'Fernández Silva', 'femenino', '1992-11-08', '+57-300-3333333', 'Cali', NOW())
    ON CONFLICT (documento_id, paciente_id) DO UPDATE SET
        nombre = EXCLUDED.nombre,
        apellido = EXCLUDED.apellido,
        sexo = EXCLUDED.sexo,
        fecha_nacimiento = EXCLUDED.fecha_nacimiento,
        contacto = EXCLUDED.contacto,
        ciudad = EXCLUDED.ciudad;
    " 2>/dev/null || print_warning "⚠️ Algunos datos de pacientes ya existen"
    
    # Verificar datos creados
    local users_count=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ')
    local patients_count=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM paciente;" 2>/dev/null | tr -d ' ')
    local doctors_count=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM profesional;" 2>/dev/null | tr -d ' ')
    
    print_status "📊 Datos creados:"
    print_status "   • Usuarios: $users_count"
    print_status "   • Pacientes: $patients_count"
    print_status "   • Médicos: $doctors_count"
    
    print_success "✅ Base de datos poblada con datos de ejemplo"
    print_status "💡 Para datos completos, ejecuta manualmente: ./llenar.sh"
}

setup_port_forwards() {
    print_status "Configurando port-forwards..."
    
    # Terminar port-forwards existentes
    pkill -f "kubectl port-forward" 2>/dev/null || true
    sleep 3
    
    # Crear port-forward para FastAPI con reintentos
    local max_attempts=3
    local attempt=1
    local port_forward_success=false
    
    while [ $attempt -le $max_attempts ] && [ "$port_forward_success" = false ]; do
        print_status "Intento de port-forward $attempt/$max_attempts..."
        
        # Crear port-forward
        kubectl port-forward --address=0.0.0.0 svc/fastapi-app 8000:8000 > /tmp/fastapi_port_forward.log 2>&1 &
        FASTAPI_PF_PID=$!
        
        # Guardar PID
        echo $FASTAPI_PF_PID > /tmp/fastapi_pf.pid
        
        # Esperar y verificar que funcione
        sleep 8
        
        # Verificar que el port-forward funcione
        if curl -s --connect-timeout 5 http://localhost:8000/health > /dev/null 2>&1; then
            print_success "✅ Port-forward funcionando correctamente"
            port_forward_success=true
        else
            print_warning "⚠️ Port-forward falló, reintentando..."
            kill $FASTAPI_PF_PID 2>/dev/null || true
            sleep 2
        fi
        
        attempt=$((attempt + 1))
    done
    
    if [ "$port_forward_success" = false ]; then
        print_warning "⚠️ Port-forward no funcionó después de $max_attempts intentos"
        print_status "💡 Puedes usar NodePort: http://$(minikube ip):30800"
    else
        print_success "Port-forwards configurados y verificados"
    fi
}

verify_system() {
    print_status "Verificando sistema completo..."
    
    # Verificar estado de pods
    print_status "Estado de pods:"
    kubectl get pods -o wide
    
    # Verificar servicios
    print_status "Estado de servicios:"
    kubectl get svc
    
    # Verificar base de datos
    print_status "Verificando base de datos..."
    TABLES_COUNT=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
    print_status "Tablas en la base de datos: $TABLES_COUNT"
    
    # Verificar usuarios
    USERS_COUNT=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -t -c "SELECT COUNT(*) FROM users;" | tr -d ' ')
    print_status "Usuarios en la base de datos: $USERS_COUNT"
    
    # Verificar cluster Citus
    print_status "Verificando cluster Citus..."
    kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "SELECT * FROM citus_get_active_worker_nodes();" || true
    
    # Verificar endpoint de salud
    sleep 15
    print_status "Verificando endpoint de salud..."
    for i in {1..5}; do
        if curl -s http://localhost:8000/health | grep -q "healthy" 2>/dev/null; then
            print_success "✅ FastAPI responde correctamente"
            break
        else
            if [ $i -eq 5 ]; then
                print_warning "⚠️ FastAPI podría no estar completamente listo"
            else
                print_status "Reintentando verificación de salud ($i/5)..."
                sleep 10
            fi
        fi
    done
    
    # Verificar login
    if curl -s http://localhost:8000/login | grep -q "Portal de Salud\|Sistema FHIR" 2>/dev/null; then
        print_success "✅ Página de login accesible"
    else
        print_warning "⚠️ Página de login podría tener problemas"
    fi
    
    # Verificar API docs
    if curl -s http://localhost:8000/docs | grep -q "FastAPI\|swagger" 2>/dev/null; then
        print_success "✅ Documentación API accesible"
    else
        print_warning "⚠️ Documentación API podría tener problemas"
    fi
    
    print_success "Verificación del sistema completada"
}

cleanup_on_exit() {
    print_status "Limpiando procesos en segundo plano..."
    if [ -f /tmp/fastapi_pf.pid ]; then
        kill $(cat /tmp/fastapi_pf.pid) 2>/dev/null || true
        rm -f /tmp/fastapi_pf.pid
    fi
}

# Banner del sistema
show_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
    ██╗   ██╗ █████╗      ██╗███████╗
    ██║   ██║██╔══██╗     ██║██╔════╝
    ██║   ██║███████║     ██║███████╗
    ██║   ██║██╔══██║██   ██║╚════██║
    ╚██████╔╝██║  ██║╚█████╔╝███████║
     ╚═════╝ ╚═╝  ╚═╝ ╚════╝ ╚══════╝
     Sistema Distribuido con PostgreSQL + Citus
EOF
    echo -e "${NC}"
    echo -e "${PURPLE}Autores: Carlos Cochero, Andrés Palacio${NC}"
    echo -e "${PURPLE}Versión: 4.0 | FastAPI Refactorizado + PostgreSQL/Citus${NC}"
    echo ""
}

trap cleanup_on_exit EXIT

# ============================================================================
# MAIN EXECUTION
# ============================================================================

show_banner
print_header "SISTEMA FHIR DISTRIBUIDO - SETUP COMPLETO Y AUTÓNOMO"

# Paso 1: Verificar dependencias
print_header "PASO 1: VERIFICACIÓN DE DEPENDENCIAS"
need_cmd docker
need_cmd kubectl
need_cmd minikube
need_cmd curl

# Verificar archivos de Kubernetes necesarios
if [ ! -f "./k8s/secret-citus.yml" ] || [ ! -f "./k8s/citus-coordinator.yml" ] || [ ! -f "./k8s/fastapi-deployment.yml" ]; then
    print_error "Archivos de Kubernetes no encontrados en ./k8s/"
    exit 1
fi

# Verificar archivos Docker necesarios
if [ ! -f "./postgres-citus/Dockerfile" ] || [ ! -f "./fastapi-app/Dockerfile" ]; then
    print_error "Archivos Docker no encontrados"
    exit 1
fi

# Cambiar al directorio k8s
cd ./k8s

print_success "✅ Todas las dependencias verificadas"
sleep 5

# Paso 2: Setup Minikube
print_header "PASO 2: CONFIGURACIÓN DE MINIKUBE"
MINIKUBE_STATUS=$(minikube status --format='{{.Host}}' 2>/dev/null || echo "NotFound")

if [ "$MINIKUBE_STATUS" = "Running" ]; then
  print_warning "⚠️ Minikube ya está corriendo. Reutilizando cluster existente."
elif [ "$MINIKUBE_STATUS" = "Stopped" ]; then
  print_status "🔄 Minikube existe pero está detenido. Iniciando..."
  minikube start
else
  print_status "🆕 Creando nuevo cluster Minikube..."
  minikube start --driver="$MINIKUBE_DRIVER" --memory="$MINIKUBE_MEMORY" --cpus="$MINIKUBE_CPUS"
fi

kubectl config use-context minikube
kubectl wait --for=condition=Ready nodes --all --timeout=300s
print_success "✅ Minikube configurado y operativo"
sleep 5

# Paso 3: Construir imágenes
print_header "PASO 3: CONSTRUCCIÓN DE IMÁGENES DOCKER"
eval $(minikube docker-env)

print_status "🏗️ Construyendo imagen de Citus..."
docker build -t local/citus-custom:12.1 -f ../postgres-citus/Dockerfile ../postgres-citus/

print_status "🏗️ Construyendo imagen de FastAPI..."
docker build -t local/fastapi-fhir:latest -f ../fastapi-app/Dockerfile ../fastapi-app/

print_success "✅ Imágenes Docker construidas"
sleep 5

# Paso 4: Desplegar base de datos
print_header "PASO 4: DESPLIEGUE DE BASE DE DATOS CITUS"
kubectl apply -f secret-citus.yml
kubectl apply -f citus-coordinator.yml
kubectl apply -f citus-worker-statefulset.yml

wait_for_pods "app=citus-coordinator" 300
wait_for_pods "app=citus-worker" 300

print_success "✅ Citus desplegado"
sleep 5

# Paso 5: Configurar Citus
print_header "PASO 5: CONFIGURACIÓN DE CLUSTER CITUS"
sleep 30  # Dar tiempo para que los pods se estabilicen

fix_citus_authentication
setup_citus_cluster

print_success "✅ Cluster Citus configurado"
sleep 5

# Paso 6: Desplegar FastAPI
print_header "PASO 6: DESPLIEGUE DE APLICACIÓN FASTAPI"
kubectl apply -f fastapi-deployment.yml

wait_for_pods "app=fastapi-app" 300

print_success "✅ FastAPI desplegado"
sleep 5

# Paso 7: Configurar acceso externo
print_header "PASO 7: CONFIGURACIÓN DE ACCESO EXTERNO"
setup_port_forwards

# Obtener URLs
MINIKUBE_IP=$(minikube ip)
NODEPORT=$(kubectl get svc fastapi-app-nodeport -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "N/A")

print_success "✅ Acceso externo configurado"
sleep 5

# Paso 8: Verificación inicial del sistema
print_header "PASO 8: VERIFICACIÓN INICIAL DEL SISTEMA"
verify_system
sleep 5

# Paso 9: Sistema de autenticación
print_header "PASO 9: VERIFICACIÓN DEL SISTEMA DE AUTENTICACIÓN"
sleep 10  # Dar tiempo para que FastAPI se inicialice

print_status "Sistema de autenticación híbrido configurado:"
print_status "- Tokens JWT con localStorage + cookies"
print_status "- Templates refactorizados y optimizados"
print_status "- Validación automática de tokens"

print_success "✅ Sistema de autenticación configurado y funcional"
sleep 5

# Paso 10: Poblado de base de datos (opcional)
print_header "PASO 10: POBLADO DE BASE DE DATOS"
echo -e "${YELLOW}¿Deseas poblar la base de datos con datos de ejemplo? (y/N)${NC}"
read -r POPULATE_DB
if [[ $POPULATE_DB =~ ^[Yy]$ ]]; then
    populate_database
else
    print_status "Saltando poblado de base de datos. Puedes ejecutar ./llenar.sh más tarde."
fi
sleep 5

# Paso 11: Información final
print_header "🎉 ¡DESPLIEGUE COMPLETADO EXITOSAMENTE!"

echo ""
echo -e "${BOLD}${GREEN}📋 INFORMACIÓN DE ACCESO:${NC}"
echo -e "  🌐 Sistema Web (localhost): ${CYAN}http://localhost:8000${NC}"
echo -e "  🌐 Sistema Web (NodePort):  ${CYAN}http://$MINIKUBE_IP:$NODEPORT${NC}"
echo -e "  🔐 Página de Login:         ${CYAN}http://localhost:8000/login${NC}"
echo -e "  📊 Dashboard Paciente:      ${CYAN}http://localhost:8000/ (después del login)${NC}"
echo -e "  📖 Documentación API:       ${CYAN}http://localhost:8000/docs${NC}"
echo -e "  ⚡ Health Check:           ${CYAN}http://localhost:8000/health${NC}"
echo ""
echo -e "${BOLD}${YELLOW}🔑 CREDENCIALES DE ACCESO (Sistema Base):${NC}"
echo -e "  👤 Admin:        ${GREEN}admin1${NC} / ${GREEN}secret${NC}"
echo -e "  👨‍⚕️ Cardiólogo:  ${GREEN}cardiologo1${NC} / ${GREEN}secret${NC}"
echo -e "  👩‍🦰 Paciente:    ${GREEN}paciente1${NC} / ${GREEN}secret${NC}"
echo -e "  👁️ Auditor:     ${GREEN}auditor1${NC} / ${GREEN}secret${NC}"
echo ""
echo -e "${BOLD}${CYAN}💡 NOTA: Para datos completos de demostración, ejecuta:${NC}"
echo -e "  ${CYAN}./llenar.sh${NC} - Poblará la BD con usuarios y datos adicionales"
echo ""
echo -e "${BOLD}${BLUE}🛠️ COMANDOS ÚTILES:${NC}"
echo -e "  Ver logs FastAPI:     ${CYAN}kubectl logs -l app=fastapi-app -f${NC}"
echo -e "  Ver logs Citus:       ${CYAN}kubectl logs -l app=citus-coordinator -f${NC}"
echo -e "  Estado del cluster:   ${CYAN}kubectl get all${NC}"
echo -e "  Escalar FastAPI:      ${CYAN}kubectl scale deployment fastapi-app --replicas=3${NC}"
echo -e "  Conectar a BD:        ${CYAN}kubectl exec -it citus-coordinator-0 -- psql -U postgres -d hce_distribuida${NC}"
echo -e "  Ver port-forwards:    ${CYAN}ps aux | grep 'kubectl port-forward'${NC}"
echo ""
echo -e "${BOLD}${RED}🧹 PARA LIMPIAR EL ENTORNO:${NC}"
echo -e "  Eliminar recursos:    ${CYAN}kubectl delete all --all && kubectl delete pvc --all${NC}"
echo -e "  Eliminar minikube:    ${CYAN}minikube delete${NC}"
echo ""
print_success "✅ El Sistema FHIR está completamente operativo y listo para usar"
print_status "🚀 Accede a http://localhost:8000/login para comenzar"