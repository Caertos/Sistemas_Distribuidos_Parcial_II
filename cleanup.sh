#!/usr/bin/env bash
# cleanup.sh - Script para limpiar recursos del proyecto
# Uso: 
#   ./cleanup.sh                  - Limpieza completa (interactiva)
#   ./cleanup.sh --light          - Limpieza ligera (solo cache/temporales)
#   ./cleanup.sh --light --rebuild - Limpieza ligera + reconstruir imágenes

# No usar pipefail para que continue incluso si algunos comandos fallan
set -eo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }

echo "============================================"
echo "  Limpieza de Recursos - Citus Cluster"
echo "============================================"
echo ""

# Verificar si es modo ligero
if [ "$1" == "--light" ]; then
    log_info "Modo de limpieza ligera activado"
    echo ""
    
    # Solo limpiar archivos temporales y cache
    log_info "🧹 Limpiando archivos temporales..."
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find ./fastapi-app/logs -name "*.log" -mtime +7 -delete 2>/dev/null || true
    rm -f /tmp/citus_port_forward.log
    rm -f k8s/verify_report.json 2>/dev/null || true
    
    log_info "🐳 Limpiando cache de Docker (sin eliminar contenedores)..."
    docker system prune -f 2>/dev/null || true
    
    # Opción de rebuild
    if [ "$2" == "--rebuild" ]; then
        log_info "🔨 Reconstruyendo imágenes Docker..."
        docker compose build --no-cache
    fi
    
    echo ""
    log_info "✅ Limpieza ligera completada"
    echo "🚀 Sistema listo para usar"
    exit 0
fi

read -p "¿Estás seguro de que deseas eliminar TODOS los recursos? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Operación cancelada"
    exit 0
fi

echo ""
log_warn "Iniciando limpieza completa..."
echo ""

# 1. Matar port-forward
log_info "1. Deteniendo port-forward..."
pkill -f "kubectl.*port-forward.*citus" 2>/dev/null || true
pkill -f "port-forward.*5432" 2>/dev/null || true

# 2. Eliminar recursos de Kubernetes
if kubectl cluster-info &>/dev/null; then
    log_info "2. Eliminando recursos de Kubernetes..."
    
    kubectl delete statefulset citus-coordinator citus-worker --ignore-not-found=true 2>/dev/null || true
    kubectl delete service citus-coordinator citus-worker --ignore-not-found=true 2>/dev/null || true
    kubectl delete secret citus-secret --ignore-not-found=true 2>/dev/null || true
    kubectl delete pvc --all --ignore-not-found=true 2>/dev/null || true
    
    log_info "   Recursos de Kubernetes eliminados"
else
    log_warn "2. Kubernetes no disponible, saltando..."
fi

# 3. Eliminar Minikube (opcional)
echo ""
if minikube status &>/dev/null; then
    read -p "¿Deseas eliminar completamente el cluster de Minikube? (yes/no): " DELETE_MINIKUBE
    
    if [ "$DELETE_MINIKUBE" = "yes" ]; then
        log_warn "3. Eliminando cluster de Minikube..."
        minikube delete 2>/dev/null || true
        log_info "   Minikube eliminado"
    else
        log_info "3. Manteniendo cluster de Minikube"
    fi
else
    log_info "3. Minikube no está corriendo, saltando..."
fi

# 4. Limpiar Docker Compose (si existe)
if [ -f "docker-compose.yml" ]; then
    echo ""
    read -p "¿Deseas limpiar recursos de Docker Compose? (yes/no): " CLEAN_COMPOSE
    
    if [ "$CLEAN_COMPOSE" = "yes" ]; then
        log_info "4. Limpiando Docker Compose..."
        docker compose down -v 2>/dev/null || true
        log_info "   Docker Compose limpio"
    else
        log_info "4. Manteniendo recursos de Docker Compose"
    fi
fi

# 5. Limpiar archivos temporales del sistema
log_info "5. Limpiando archivos temporales del sistema..."
rm -f /tmp/citus_port_forward.log
rm -f k8s/verify_report.json 2>/dev/null || true

# 5.1. Limpiar archivos Python compilados
log_info "   Eliminando archivos Python compilados..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# 5.2. Limpiar logs antiguos
log_info "   Limpiando logs antiguos (>7 días)..."
find ./fastapi-app/logs -name "*.log" -mtime +7 -delete 2>/dev/null || true

log_info "   Archivos temporales eliminados"

echo ""
log_info "============================================"
log_info "  Limpieza completada exitosamente"
log_info "============================================"
echo ""
echo "Para volver a desplegar el sistema:"
echo "  Docker Compose: ./setup_all.sh compose"
echo "  Minikube:       ./setup_all.sh minikube"
echo ""
echo "Para limpieza ligera sin eliminar contenedores:"
echo "  Ejecuta: ./cleanup.sh --light"
echo ""
