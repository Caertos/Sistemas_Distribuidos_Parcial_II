#!/bin/bash

# Script para reiniciar el sistema completo en Minikube con port-forward automático
# Autor: Sistema Médico FHIR
# Fecha: 12 de noviembre de 2025

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Iniciando sistema completo en Minikube...${NC}"

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

# Función para esperar a que los pods estén listos
wait_for_pods() {
    local max_attempts=60
    local attempt=1
    
    log_info "Esperando a que todos los pods estén listos..."
    
    while [ $attempt -le $max_attempts ]; do
        # Verificar pods de Citus
        citus_ready=$(kubectl get pods -l app=citus-coordinator --no-headers 2>/dev/null | grep -c "1/1.*Running" || echo "0")
        workers_ready=$(kubectl get pods -l app=citus-worker --no-headers 2>/dev/null | grep -c "1/1.*Running" || echo "0")
        
        # Verificar pods de FastAPI
        fastapi_ready=$(kubectl get pods -l app=fastapi-app --no-headers 2>/dev/null | grep -c "1/1.*Running" || echo "0")
        
        if [ "$citus_ready" -eq "1" ] && [ "$workers_ready" -eq "2" ] && [ "$fastapi_ready" -eq "2" ]; then
            log_success "Todos los pods están listos!"
            return 0
        fi
        
        echo -n "."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    log_error "Timeout esperando a que los pods estén listos"
    return 1
}

# Función para verificar conectividad
test_connectivity() {
    log_info "Verificando conectividad del sistema..."
    
    # Esperar un momento para que el port-forward se establezca
    sleep 3
    
    # Verificar health endpoint
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Conectividad verificada - sistema disponible en http://localhost:8000"
        return 0
    else
        log_warning "El endpoint de salud no responde aún, pero el port-forward está activo"
        return 1
    fi
}

# Función para limpiar procesos de port-forward previos
cleanup_port_forward() {
    log_info "Limpiando procesos de port-forward previos..."
    
    # Buscar y matar procesos de kubectl port-forward en puerto 8000
    if pgrep -f "kubectl port-forward.*8000:8000" > /dev/null; then
        pkill -f "kubectl port-forward.*8000:8000"
        log_success "Procesos de port-forward previos eliminados"
        sleep 2
    fi
}

# 1. Verificar estado de minikube
log_info "Verificando estado de Minikube..."
if ! minikube status | grep -q "kubelet: Running"; then
    log_info "Iniciando Minikube..."
    minikube start
    log_success "Minikube iniciado"
else
    log_success "Minikube ya está ejecutándose"
fi

# 2. Verificar que kubectl esté configurado
log_info "Verificando configuración de kubectl..."
if kubectl cluster-info > /dev/null 2>&1; then
    log_success "kubectl configurado correctamente"
else
    log_error "Error en la configuración de kubectl"
    exit 1
fi

# 3. Verificar que los recursos estén desplegados
log_info "Verificando recursos desplegados..."
if ! kubectl get deployment fastapi-app > /dev/null 2>&1; then
    log_error "Los recursos no están desplegados. Ejecuta primero: ./setup_system_minikube.sh"
    exit 1
fi

# 4. Esperar a que todos los pods estén listos
if ! wait_for_pods; then
    log_error "Los pods no están listos. Verifica el estado con: kubectl get pods"
    exit 1
fi

# 5. Mostrar estado de los recursos
log_info "Estado actual de los recursos:"
kubectl get pods
echo ""
kubectl get svc
echo ""

# 6. Limpiar port-forwards previos
cleanup_port_forward

# 7. Configurar port-forward
log_info "Configurando port-forward a localhost:8000..."

# Crear port-forward en background
kubectl port-forward svc/fastapi-app 8000:8000 > /dev/null 2>&1 &
PORT_FORWARD_PID=$!

# Guardar PID para poder matarlo después
echo $PORT_FORWARD_PID > /tmp/fastapi_port_forward.pid

log_success "Port-forward configurado (PID: $PORT_FORWARD_PID)"

# 8. Verificar conectividad
test_connectivity

# 9. Mostrar información de acceso
echo ""
log_success "🎉 Sistema completamente iniciado!"
echo -e "${GREEN}┌─────────────────────────────────────────────────────────┐${NC}"
echo -e "${GREEN}│                    ACCESO AL SISTEMA                     │${NC}"
echo -e "${GREEN}├─────────────────────────────────────────────────────────┤${NC}"
echo -e "${GREEN}│ URL Principal: ${BLUE}http://localhost:8000${GREEN}                   │${NC}"
echo -e "${GREEN}│ Health Check:  ${BLUE}http://localhost:8000/health${GREEN}            │${NC}"
echo -e "${GREEN}│ Login:         ${BLUE}http://localhost:8000/auth/login${GREEN}        │${NC}"
echo -e "${GREEN}│                                                         │${NC}"
echo -e "${GREEN}│ NodePort (alternativa): ${BLUE}http://$(minikube ip):30800${GREEN}     │${NC}"
echo -e "${GREEN}└─────────────────────────────────────────────────────────┘${NC}"
echo ""

# 10. Mostrar usuarios de prueba
echo -e "${YELLOW}👥 Usuarios de prueba disponibles:${NC}"
echo -e "   • ${BLUE}Admin:${NC} admin@hospital.com / admin123"
echo -e "   • ${BLUE}Cardiólogo:${NC} cardiologo1@hospital.com / cardio123"
echo -e "   • ${BLUE}Paciente:${NC} juan.perez@email.com / patient123"
echo -e "   • ${BLUE}Auditor:${NC} auditor@hospital.com / audit123"
echo ""

# 11. Instrucciones para detener
echo -e "${YELLOW}🛑 Para detener el port-forward:${NC}"
echo -e "   kill \$(cat /tmp/fastapi_port_forward.pid) 2>/dev/null || true"
echo -e "   rm -f /tmp/fastapi_port_forward.pid"
echo ""

# 12. Mostrar logs en tiempo real (opcional)
read -p "¿Quieres ver los logs en tiempo real? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Mostrando logs en tiempo real (Ctrl+C para salir)..."
    kubectl logs -f deployment/fastapi-app
fi

log_success "Script completado exitosamente!"