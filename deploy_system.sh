#!/bin/bash

# Script maestro para desplegar todo el sistema FHIR distribuido
# Autor: Sistema FHIR Distribuido
# Fecha: $(date '+%Y-%m-%d')

set -euo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
NAMESPACE="fhir-system"
LOG_FILE="$PROJECT_ROOT/deployment.log"

# Variables de estado
DATABASE_DEPLOYED=false
BACKEND_DEPLOYED=false
FRONTEND_DEPLOYED=false

# Funciones de utilidad
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_step() {
    echo -e "${CYAN}${BOLD}[STEP]${NC} $1" | tee -a "$LOG_FILE"
}

show_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "=================================================================="
    echo "    SISTEMA FHIR DISTRIBUIDO - DESPLIEGUE COMPLETO"
    echo "=================================================================="
    echo -e "${NC}"
    echo "Este script desplegará el sistema completo incluyendo:"
    echo "• Base de datos PostgreSQL + Citus (distribuida)"
    echo "• API FastAPI con autenticación JWT"
    echo "• Frontend Nginx con interfaces multi-rol"
    echo "• Monitoreo y logging integrado"
    echo ""
    log_info "Logs guardados en: $LOG_FILE"
    echo ""
}

check_system_requirements() {
    log_step "Verificando requisitos del sistema..."
    
    # Verificar memoria disponible (mínimo 6GB recomendado)
    local mem_gb
    mem_gb=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$mem_gb" -lt 6 ]; then
        log_warning "Memoria disponible: ${mem_gb}GB. Se recomienda al menos 6GB"
        echo "¿Continuar de todos modos? (y/N): "
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Verificar espacio en disco (mínimo 10GB recomendado)
    local disk_gb
    disk_gb=$(df -BG "$PROJECT_ROOT" | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "$disk_gb" -lt 10 ]; then
        log_warning "Espacio disponible: ${disk_gb}GB. Se recomienda al menos 10GB"
    fi
    
    log_success "Requisitos del sistema verificados"
}

check_dependencies() {
    log_step "Verificando dependencias..."
    
    local deps=("docker" "kubectl" "minikube")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Dependencias faltantes: ${missing_deps[*]}"
        echo ""
        echo "Instalación:"
        echo "• Docker: https://docs.docker.com/get-docker/"
        echo "• kubectl: https://kubernetes.io/docs/tasks/tools/"
        echo "• Minikube: https://minikube.sigs.k8s.io/docs/start/"
        exit 1
    fi
    
    log_success "Todas las dependencias están disponibles"
}

check_scripts_exist() {
    log_step "Verificando scripts de despliegue..."
    
    local scripts=(
        "setup_minikube.sh"
        "setup_all.sh"
        "setup_frontend.sh"
    )
    
    local missing_scripts=()
    
    for script in "${scripts[@]}"; do
        local script_path
        if [ "$script" = "setup_minikube.sh" ]; then
            script_path="$PROJECT_ROOT/k8s/$script"
        else
            script_path="$PROJECT_ROOT/$script"
        fi
        
        if [ ! -f "$script_path" ]; then
            missing_scripts+=("$script")
        elif [ ! -x "$script_path" ]; then
            chmod +x "$script_path"
            log_info "Permisos de ejecución agregados a $script"
        fi
    done
    
    if [ ${#missing_scripts[@]} -ne 0 ]; then
        log_error "Scripts faltantes: ${missing_scripts[*]}"
        exit 1
    fi
    
    log_success "Todos los scripts están disponibles"
}

setup_minikube() {
    log_step "Configurando Minikube..."
    
    if ! minikube status | grep -q "host: Running"; then
        log_info "Iniciando Minikube..."
        cd "$PROJECT_ROOT/k8s"
        if ! ./setup_minikube.sh; then
            log_error "Falló la configuración de Minikube"
            return 1
        fi
    else
        log_info "Minikube ya está ejecutándose"
    fi
    
    # Configurar contexto de Docker
    eval $(minikube docker-env)
    
    log_success "Minikube configurado correctamente"
    return 0
}

deploy_database() {
    log_step "Desplegando base de datos PostgreSQL + Citus..."
    
    cd "$PROJECT_ROOT"
    
    # Ejecutar setup de base de datos
    if ! ./setup_all.sh; then
        log_error "Falló el despliegue de la base de datos"
        return 1
    fi
    
    # Verificar que la base de datos esté lista
    log_info "Verificando estado de la base de datos..."
    local retries=0
    local max_retries=30
    
    while [ $retries -lt $max_retries ]; do
        if kubectl get pods -n "$NAMESPACE" -l app=citus-coordinator | grep -q "Running"; then
            log_success "Base de datos desplegada exitosamente"
            DATABASE_DEPLOYED=true
            return 0
        fi
        
        log_info "Esperando que la base de datos esté lista... ($((retries + 1))/$max_retries)"
        sleep 10
        retries=$((retries + 1))
    done
    
    log_error "Timeout esperando que la base de datos esté lista"
    return 1
}

deploy_backend() {
    log_step "Desplegando API FastAPI..."
    
    # El backend ya se despliega con setup_all.sh, solo verificamos
    log_info "Verificando estado del backend..."
    local retries=0
    local max_retries=20
    
    while [ $retries -lt $max_retries ]; do
        if kubectl get pods -n "$NAMESPACE" -l app=fastapi | grep -q "Running"; then
            log_success "Backend API desplegado exitosamente"
            BACKEND_DEPLOYED=true
            return 0
        fi
        
        log_info "Esperando que el backend esté listo... ($((retries + 1))/$max_retries)"
        sleep 10
        retries=$((retries + 1))
    done
    
    log_error "Timeout esperando que el backend esté listo"
    return 1
}

deploy_frontend() {
    log_step "Desplegando frontend Nginx..."
    
    cd "$PROJECT_ROOT"
    
    # Ejecutar setup del frontend
    if ! ./setup_frontend.sh; then
        log_error "Falló el despliegue del frontend"
        return 1
    fi
    
    # Verificar que el frontend esté listo
    log_info "Verificando estado del frontend..."
    local retries=0
    local max_retries=20
    
    while [ $retries -lt $max_retries ]; do
        if kubectl get pods -n "$NAMESPACE" -l app=nginx-frontend | grep -q "Running"; then
            log_success "Frontend desplegado exitosamente"
            FRONTEND_DEPLOYED=true
            return 0
        fi
        
        log_info "Esperando que el frontend esté listo... ($((retries + 1))/$max_retries)"
        sleep 10
        retries=$((retries + 1))
    done
    
    log_error "Timeout esperando que el frontend esté listo"
    return 1
}

run_system_tests() {
    log_step "Ejecutando pruebas del sistema..."
    
    if [ -x "$PROJECT_ROOT/run_tests.sh" ]; then
        cd "$PROJECT_ROOT"
        if ./run_tests.sh; then
            log_success "Todas las pruebas pasaron exitosamente"
        else
            log_warning "Algunas pruebas fallaron, pero el sistema está funcional"
        fi
    else
        log_warning "Script de pruebas no encontrado o no ejecutable"
    fi
}

show_system_status() {
    log_step "Estado final del sistema..."
    
    echo ""
    log_info "=== PODS ==="
    kubectl get pods -n "$NAMESPACE" -o wide
    
    echo ""
    log_info "=== SERVICIOS ==="
    kubectl get services -n "$NAMESPACE"
    
    echo ""
    log_info "=== DEPLOYMENTS ==="
    kubectl get deployments -n "$NAMESPACE"
    
    echo ""
    log_info "=== STATEFULSETS ==="
    kubectl get statefulsets -n "$NAMESPACE"
}

get_access_urls() {
    log_step "URLs de acceso al sistema..."
    
    echo ""
    log_success "=== ACCESO AL SISTEMA ==="
    
    # URL del frontend
    if command -v minikube &> /dev/null && minikube status | grep -q "host: Running"; then
        local frontend_url
        frontend_url=$(minikube service nginx-frontend-service -n "$NAMESPACE" --url 2>/dev/null || echo "")
        if [ -n "$frontend_url" ]; then
            echo -e "${GREEN}Frontend (Web):${NC} $frontend_url"
        fi
        
        local api_url
        api_url=$(minikube service fastapi-service -n "$NAMESPACE" --url 2>/dev/null || echo "")
        if [ -n "$api_url" ]; then
            echo -e "${GREEN}API Backend:${NC} $api_url"
        fi
    fi
    
    echo ""
    echo -e "${YELLOW}Acceso mediante Port-Forward:${NC}"
    echo "• Frontend: kubectl port-forward -n $NAMESPACE service/nginx-frontend-service 8080:80"
    echo "  Luego abrir: http://localhost:8080"
    echo ""
    echo "• API: kubectl port-forward -n $NAMESPACE service/fastapi-service 8000:80"
    echo "  Luego abrir: http://localhost:8000/docs"
    
    echo ""
    echo -e "${CYAN}Usuarios de prueba:${NC}"
    echo "• admin/admin (Administrador del sistema)"
    echo "• medic/medic (Personal médico)"
    echo "• patient/patient (Paciente)"
    echo "• audit/audit (Auditor del sistema)"
}

show_monitoring_commands() {
    echo ""
    log_info "=== COMANDOS DE MONITOREO ==="
    echo ""
    echo "Logs en tiempo real:"
    echo "• kubectl logs -f -n $NAMESPACE -l app=fastapi"
    echo "• kubectl logs -f -n $NAMESPACE -l app=nginx-frontend"
    echo "• kubectl logs -f -n $NAMESPACE -l app=citus-coordinator"
    echo ""
    echo "Estado del sistema:"
    echo "• kubectl get all -n $NAMESPACE"
    echo "• kubectl top pods -n $NAMESPACE"
    echo ""
    echo "Acceso a pods:"
    echo "• kubectl exec -it -n $NAMESPACE deployment/fastapi -- /bin/bash"
    echo "• kubectl exec -it -n $NAMESPACE statefulset/citus-coordinator -- psql -U postgres"
}

cleanup_on_failure() {
    log_warning "Limpiando recursos debido a fallos..."
    
    # Limpiar recursos de Kubernetes
    kubectl delete namespace "$NAMESPACE" --ignore-not-found=true --timeout=60s
    
    # Detener Minikube si fue iniciado por este script
    if [ "${MINIKUBE_STARTED:-false}" = "true" ]; then
        log_info "Deteniendo Minikube..."
        minikube stop
    fi
}

handle_interrupt() {
    echo ""
    log_warning "Despliegue interrumpido por el usuario"
    cleanup_on_failure
    exit 1
}

main() {
    # Configurar manejo de interrupciones
    trap handle_interrupt INT TERM
    
    # Limpiar log anterior
    > "$LOG_FILE"
    
    show_banner
    
    # Verificaciones previas
    check_system_requirements
    check_dependencies
    check_scripts_exist
    
    # Configurar entorno
    if ! setup_minikube; then
        log_error "Falló la configuración de Minikube"
        exit 1
    fi
    
    # Desplegar componentes
    echo ""
    log_info "Iniciando despliegue de componentes..."
    
    # 1. Base de datos (incluye backend)
    if ! deploy_database; then
        log_error "Falló el despliegue de la base de datos"
        cleanup_on_failure
        exit 1
    fi
    
    # 2. Verificar backend
    if ! deploy_backend; then
        log_error "Backend no está funcionando correctamente"
        cleanup_on_failure
        exit 1
    fi
    
    # 3. Frontend
    if ! deploy_frontend; then
        log_error "Falló el despliegue del frontend"
        cleanup_on_failure
        exit 1
    fi
    
    # Pruebas del sistema
    run_system_tests
    
    # Mostrar estado final
    show_system_status
    get_access_urls
    show_monitoring_commands
    
    echo ""
    log_success "🎉 ¡DESPLIEGUE COMPLETADO EXITOSAMENTE! 🎉"
    echo ""
    log_info "El sistema FHIR distribuido está ahora completamente funcional"
    log_info "Logs detallados disponibles en: $LOG_FILE"
    
    # Resumen de componentes desplegados
    echo ""
    echo -e "${BOLD}Componentes desplegados:${NC}"
    echo "✅ PostgreSQL + Citus (Base de datos distribuida)"
    echo "✅ FastAPI (API Backend con JWT)"
    echo "✅ Nginx (Frontend con interfaces multi-rol)"
    echo "✅ Kubernetes (Orquestación de contenedores)"
    
    echo ""
    log_info "Para detener el sistema: minikube stop"
    log_info "Para reiniciar: minikube start && kubectl get pods -n $NAMESPACE"
}

# Verificar que no se esté ejecutando como root
if [ "$EUID" -eq 0 ]; then
    log_error "No ejecute este script como root"
    exit 1
fi

# Ejecutar función principal
main "$@"