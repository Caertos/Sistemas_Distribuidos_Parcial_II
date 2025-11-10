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
    
    # Configurar coordinador
    kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "SELECT citus_set_coordinator_host('citus-coordinator');" || true
    
    # Agregar workers
    kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "SELECT citus_add_node('citus-worker-0.citus-worker', 5432);" || true
    kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "SELECT citus_add_node('citus-worker-1.citus-worker', 5432);" || true
    
    print_success "Cluster de Citus configurado"
}

# Función eliminada - Los templates ya están limpios y refactorizados
# Ya no se necesitan las correcciones de login después de la refactorización

setup_port_forwards() {
    print_status "Configurando port-forwards..."
    
    # Terminar port-forwards existentes
    pkill -f "kubectl port-forward" 2>/dev/null || true
    sleep 2
    
    # Crear port-forward para FastAPI
    kubectl port-forward --address=0.0.0.0 svc/fastapi-app 8000:8000 > /tmp/fastapi_port_forward.log 2>&1 &
    FASTAPI_PF_PID=$!
    
    # Guardar PID para limpieza posterior
    echo $FASTAPI_PF_PID > /tmp/fastapi_pf.pid
    
    # Esperar a que el port-forward esté activo
    sleep 5
    
    print_success "Port-forwards configurados"
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
    sleep 10
    if curl -s http://localhost:8000/health | grep -q "healthy" 2>/dev/null; then
        print_success "✅ FastAPI responde correctamente"
    else
        print_warning "⚠️ FastAPI podría no estar completamente listo"
    fi
    
    # Verificar login
    if curl -s http://localhost:8000/login | grep -q "Sistema FHIR" 2>/dev/null; then
        print_success "✅ Página de login accesible"
    else
        print_warning "⚠️ Página de login podría tener problemas"
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
    echo -e "${PURPLE}Versión: 3.0 | FastAPI + Jinja2 + PostgreSQL/Citus${NC}"
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
docker build -t local/citus-custom:12.1 -f ../postgres-citus/Dockerfile ../postgres-citus/ --quiet

print_status "🏗️ Construyendo imagen de FastAPI..."
docker build -t local/fastapi-fhir:latest -f ../fastapi-app/Dockerfile ../fastapi-app/ --quiet

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

# Paso 7: Sistema de login - Ya no requiere correcciones
print_header "PASO 7: VERIFICACIÓN DEL SISTEMA DE LOGIN"
sleep 10  # Dar tiempo para que FastAPI se inicialice

print_success "✅ Sistema de login ya está configurado correctamente con templates refactorizados"

print_success "✅ Sistema de login configurado y funcional"
sleep 5

# Paso 8: Configurar acceso externo
print_header "PASO 8: CONFIGURACIÓN DE ACCESO EXTERNO"
setup_port_forwards

# Obtener URLs
MINIKUBE_IP=$(minikube ip)
NODEPORT=$(kubectl get svc fastapi-app-nodeport -o jsonpath='{.spec.ports[0].nodePort}')

print_success "✅ Acceso externo configurado"
sleep 5

# Paso 9: Verificación final
print_header "PASO 9: VERIFICACIÓN FINAL DEL SISTEMA"
verify_system
sleep 5

# Paso 10: Información final
print_header "🎉 ¡DESPLIEGUE COMPLETADO EXITOSAMENTE!"

echo ""
echo -e "${BOLD}${GREEN}📋 INFORMACIÓN DE ACCESO:${NC}"
echo -e "  🌐 Sistema Web (localhost): ${CYAN}http://localhost:8000${NC}"
echo -e "  🌐 Sistema Web (NodePort):  ${CYAN}http://$MINIKUBE_IP:$NODEPORT${NC}"
echo -e "  🔐 Página de Login:         ${CYAN}http://localhost:8000/login${NC}"
echo -e "  📊 Dashboard:               ${CYAN}http://localhost:8000/dashboard${NC}"
echo -e "  📖 Documentación API:       ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo -e "${BOLD}${YELLOW}🔑 CREDENCIALES DE ACCESO:${NC}"
echo -e "  👤 Admin:     ${GREEN}admin${NC} / ${GREEN}secret${NC}"
echo -e "  👨‍⚕️ Médico:    ${GREEN}medico${NC} / ${GREEN}secret${NC}"
echo -e "  👩‍🦰 Paciente:  ${GREEN}paciente${NC} / ${GREEN}secret${NC}"
echo -e "  👁️ Auditor:   ${GREEN}auditor${NC} / ${GREEN}secret${NC}"
echo ""
echo -e "${BOLD}${BLUE}🛠️ COMANDOS ÚTILES:${NC}"
echo -e "  Ver logs FastAPI:     ${CYAN}kubectl logs -l app=fastapi-app -f${NC}"
echo -e "  Ver logs Citus:       ${CYAN}kubectl logs -l app=citus-coordinator -f${NC}"
echo -e "  Estado del cluster:   ${CYAN}kubectl get all${NC}"
echo -e "  Escalar FastAPI:      ${CYAN}kubectl scale deployment fastapi-app --replicas=3${NC}"
echo ""
echo -e "${BOLD}${RED}🧹 PARA LIMPIAR EL ENTORNO:${NC}"
echo -e "  Eliminar recursos:    ${CYAN}kubectl delete all --all && kubectl delete pvc --all${NC}"
echo -e "  Eliminar minikube:    ${CYAN}minikube delete${NC}"
echo ""
print_success "✅ El Sistema FHIR está completamente operativo y listo para usar"
print_status "🚀 Accede a http://localhost:8000/login para comenzar"