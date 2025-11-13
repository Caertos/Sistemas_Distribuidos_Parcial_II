#!/bin/bash

# Script para detener el sistema completo en Minikube
# Autor: Sistema Médico FHIR
# Fecha: 12 de noviembre de 2025

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Deteniendo sistema completo en Minikube...${NC}"

# Función para mostrar mensajes con colores
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. Detener port-forward
log_info "Deteniendo procesos de port-forward..."
if [ -f /tmp/fastapi_port_forward.pid ]; then
    PID=$(cat /tmp/fastapi_port_forward.pid)
    if kill $PID 2>/dev/null; then
        log_success "Port-forward detenido (PID: $PID)"
    else
        log_warning "El proceso de port-forward ya no existe"
    fi
    rm -f /tmp/fastapi_port_forward.pid
fi

# Buscar y matar cualquier proceso de port-forward restante
if pgrep -f "kubectl port-forward.*8000:8000" > /dev/null; then
    pkill -f "kubectl port-forward.*8000:8000"
    log_success "Procesos de port-forward adicionales eliminados"
fi

# 2. Mostrar opciones de detención
echo ""
echo -e "${YELLOW}Selecciona el nivel de detención:${NC}"
echo "1) Solo detener port-forward (pods siguen ejecutándose)"
echo "2) Detener todos los pods (mantener minikube activo)"
echo "3) Detener minikube completamente"
echo "4) Limpiar todo (detener minikube y limpiar recursos)"

read -p "Selecciona una opción (1-4): " -n 1 -r
echo
echo ""

case $REPLY in
    1)
        log_success "Solo se detuvo el port-forward. Los pods siguen ejecutándose."
        log_info "Para acceder al sistema usa: http://$(minikube ip 2>/dev/null || echo 'MINIKUBE_IP'):30800"
        ;;
    2)
        log_info "Eliminando deployments y servicios..."
        kubectl delete -f ../k8s/ --ignore-not-found=true
        log_success "Todos los pods y servicios eliminados"
        ;;
    3)
        log_info "Deteniendo minikube..."
        minikube stop
        log_success "Minikube detenido"
        ;;
    4)
        log_info "Eliminando recursos de Kubernetes..."
        kubectl delete -f ../k8s/ --ignore-not-found=true 2>/dev/null || true
        
        log_info "Deteniendo minikube..."
        minikube stop 2>/dev/null || true
        
        log_info "Eliminando cluster de minikube..."
        minikube delete 2>/dev/null || true
        
        log_success "Sistema completamente limpio"
        ;;
    *)
        log_success "Solo se detuvo el port-forward (opción por defecto)"
        ;;
esac

echo ""
log_success "🎉 Operación completada!"

# Mostrar estado final
if minikube status | grep -q "kubelet: Running" 2>/dev/null; then
    echo -e "${GREEN}Estado de Minikube: ${BLUE}Ejecutándose${NC}"
    if kubectl get pods 2>/dev/null | grep -q "Running"; then
        echo -e "${GREEN}Pods activos: ${BLUE}Sí${NC}"
        echo -e "${GREEN}Acceso alternativo: ${BLUE}http://$(minikube ip):30800${NC}"
    else
        echo -e "${YELLOW}Pods activos: ${RED}No${NC}"
    fi
else
    echo -e "${YELLOW}Estado de Minikube: ${RED}Detenido${NC}"
fi

echo ""
echo -e "${YELLOW}💡 Para reiniciar todo el sistema ejecuta:${NC}"
echo -e "   ${BLUE}./restart_minikube_system.sh${NC}"