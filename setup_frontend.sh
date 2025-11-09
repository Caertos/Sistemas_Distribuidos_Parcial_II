#!/bin/bash

# Script para construir y desplegar el frontend Nginx
# Autor: Sistema FHIR Distribuido
# Fecha: $(date '+%Y-%m-%d')

set -euo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
NGINX_IMAGE_NAME="fhir-nginx-frontend"
NGINX_IMAGE_TAG="latest"
NAMESPACE="fhir-system"

# Funciones de utilidad
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Verificando dependencias..."
    
    local deps=("docker" "kubectl")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Dependencias faltantes: ${missing_deps[*]}"
        log_error "Por favor instale las dependencias antes de continuar"
        exit 1
    fi
    
    log_success "Todas las dependencias están disponibles"
}

check_docker_daemon() {
    log_info "Verificando que Docker esté ejecutándose..."
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon no está ejecutándose"
        log_error "Por favor inicie Docker antes de continuar"
        exit 1
    fi
    
    log_success "Docker daemon está ejecutándose"
}

verify_project_structure() {
    log_info "Verificando estructura del proyecto..."
    
    local required_files=(
        "nginx/Dockerfile"
        "nginx/nginx.conf"
        "fastapi-app/static"
        "fastapi-app/templates"
        "k8s/nginx-frontend.yml"
    )
    
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [ ! -e "$PROJECT_ROOT/$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -ne 0 ]; then
        log_error "Archivos/directorios faltantes: ${missing_files[*]}"
        exit 1
    fi
    
    log_success "Estructura del proyecto verificada"
}

build_nginx_image() {
    log_info "Construyendo imagen Docker de Nginx..."
    
    cd "$PROJECT_ROOT"
    
    # Construir la imagen
    if ! docker build -t "${NGINX_IMAGE_NAME}:${NGINX_IMAGE_TAG}" -f nginx/Dockerfile .; then
        log_error "Falló la construcción de la imagen Docker"
        exit 1
    fi
    
    log_success "Imagen Docker construida: ${NGINX_IMAGE_NAME}:${NGINX_IMAGE_TAG}"
}

check_minikube() {
    log_info "Verificando estado de Minikube..."
    
    if ! command -v minikube &> /dev/null; then
        log_error "Minikube no está instalado"
        log_error "Para instalarlo: https://minikube.sigs.k8s.io/docs/start/"
        exit 1
    fi
    
    if ! minikube status | grep -q "host: Running"; then
        log_warning "Minikube no está ejecutándose. Iniciando..."
        minikube start --driver=docker --memory=4096 --cpus=2
    fi
    
    # Configurar Docker para usar el registro de Minikube
    eval $(minikube docker-env)
    
    log_success "Minikube está listo"
}

load_image_to_minikube() {
    log_info "Cargando imagen a Minikube..."
    
    # Rebuild con el contexto de Docker de Minikube
    cd "$PROJECT_ROOT"
    docker build -t "${NGINX_IMAGE_NAME}:${NGINX_IMAGE_TAG}" -f nginx/Dockerfile .
    
    log_success "Imagen cargada en Minikube"
}

create_namespace() {
    log_info "Creando namespace si no existe..."
    
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        kubectl create namespace "$NAMESPACE"
        log_success "Namespace '$NAMESPACE' creado"
    else
        log_info "Namespace '$NAMESPACE' ya existe"
    fi
}

deploy_nginx_frontend() {
    log_info "Desplegando Nginx frontend en Kubernetes..."
    
    # Aplicar manifiestos
    if ! kubectl apply -f "$PROJECT_ROOT/k8s/nginx-frontend.yml"; then
        log_error "Falló el despliegue de Nginx frontend"
        exit 1
    fi
    
    log_success "Nginx frontend desplegado exitosamente"
}

wait_for_deployment() {
    log_info "Esperando que el deployment esté listo..."
    
    # Esperar que el deployment esté listo
    if ! kubectl wait --for=condition=available --timeout=300s deployment/nginx-frontend -n "$NAMESPACE"; then
        log_error "Timeout esperando que el deployment esté listo"
        show_deployment_status
        exit 1
    fi
    
    log_success "Deployment está listo"
}

show_deployment_status() {
    log_info "Estado del deployment:"
    kubectl get pods -n "$NAMESPACE" -l app=nginx-frontend
    kubectl get services -n "$NAMESPACE" -l app=nginx-frontend
    
    log_info "Logs del deployment:"
    kubectl logs -n "$NAMESPACE" -l app=nginx-frontend --tail=50
}

get_service_url() {
    log_info "Obteniendo URL del servicio..."
    
    # Obtener la URL del servicio
    local service_url
    if command -v minikube &> /dev/null && minikube status | grep -q "host: Running"; then
        service_url=$(minikube service nginx-frontend-service -n "$NAMESPACE" --url)
        log_success "Servicio disponible en: $service_url"
        echo ""
        log_info "También puede acceder mediante port-forward:"
        log_info "kubectl port-forward -n $NAMESPACE service/nginx-frontend-service 8080:80"
        log_info "Luego abrir: http://localhost:8080"
    else
        log_info "Para acceder al servicio, use port-forward:"
        log_info "kubectl port-forward -n $NAMESPACE service/nginx-frontend-service 8080:80"
        log_info "Luego abrir: http://localhost:8080"
    fi
}

run_health_checks() {
    log_info "Ejecutando verificaciones de salud..."
    
    # Verificar pods
    local ready_pods
    ready_pods=$(kubectl get pods -n "$NAMESPACE" -l app=nginx-frontend -o jsonpath='{.items[*].status.containerStatuses[*].ready}' | grep -o true | wc -l)
    
    if [ "$ready_pods" -gt 0 ]; then
        log_success "$ready_pods pods de Nginx están listos"
    else
        log_error "No hay pods de Nginx listos"
        return 1
    fi
    
    # Verificar servicio
    if kubectl get service nginx-frontend-service -n "$NAMESPACE" &> /dev/null; then
        log_success "Servicio de Nginx está disponible"
    else
        log_error "Servicio de Nginx no está disponible"
        return 1
    fi
    
    return 0
}

cleanup_on_error() {
    log_warning "Limpiando recursos debido a error..."
    kubectl delete -f "$PROJECT_ROOT/k8s/nginx-frontend.yml" --ignore-not-found=true
}

show_next_steps() {
    echo ""
    log_success "=== DESPLIEGUE COMPLETADO ==="
    echo ""
    log_info "Próximos pasos:"
    echo "1. Verificar que FastAPI esté ejecutándose:"
    echo "   kubectl get pods -n $NAMESPACE -l app=fastapi"
    echo ""
    echo "2. Acceder a la aplicación:"
    if command -v minikube &> /dev/null && minikube status | grep -q "host: Running"; then
        echo "   minikube service nginx-frontend-service -n $NAMESPACE"
    else
        echo "   kubectl port-forward -n $NAMESPACE service/nginx-frontend-service 8080:80"
        echo "   Luego abrir: http://localhost:8080"
    fi
    echo ""
    echo "3. Monitorear logs:"
    echo "   kubectl logs -f -n $NAMESPACE -l app=nginx-frontend"
    echo ""
    echo "4. Verificar estado:"
    echo "   kubectl get all -n $NAMESPACE"
    echo ""
    log_info "Usuarios de prueba disponibles:"
    echo "   - admin/admin (Administrador)"
    echo "   - medic/medic (Médico)"
    echo "   - patient/patient (Paciente)"
    echo "   - audit/audit (Auditor)"
}

main() {
    echo ""
    log_info "=== SETUP NGINX FRONTEND PARA SISTEMA FHIR ==="
    echo ""
    
    # Verificaciones previas
    check_dependencies
    check_docker_daemon
    verify_project_structure
    
    # Configurar Minikube si está disponible
    if command -v minikube &> /dev/null; then
        check_minikube
    else
        log_warning "Minikube no está disponible, usando contexto actual de kubectl"
    fi
    
    # Construir y desplegar
    build_nginx_image
    
    if command -v minikube &> /dev/null && minikube status | grep -q "host: Running"; then
        load_image_to_minikube
    fi
    
    create_namespace
    deploy_nginx_frontend
    wait_for_deployment
    
    # Verificaciones finales
    if run_health_checks; then
        show_deployment_status
        get_service_url
        show_next_steps
    else
        log_error "Falló la verificación de salud"
        show_deployment_status
        exit 1
    fi
    
    log_success "¡Setup de Nginx frontend completado exitosamente!"
}

# Manejo de errores
trap 'log_error "Script interrumpido"; cleanup_on_error; exit 1' INT TERM

# Verificar si se está ejecutando como root (no recomendado)
if [ "$EUID" -eq 0 ]; then
    log_warning "No se recomienda ejecutar este script como root"
    read -p "¿Continuar? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Ejecutar función principal
main "$@"