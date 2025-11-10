#!/usr/bin/env bash
# Script de limpieza completa para el Sistema FHIR en Kubernetes

set -euo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_status "🧹 Iniciando limpieza completa del Sistema FHIR en Kubernetes"

# 1. Eliminar todos los recursos desplegados
print_status "1/4 Eliminando recursos de Kubernetes..."

# Eliminar en orden inverso al despliegue
kubectl delete -f data-population-job.yml --ignore-not-found=true
kubectl delete -f nginx-deployment.yml --ignore-not-found=true
kubectl delete -f fastapi-deployment.yml --ignore-not-found=true
kubectl delete -f citus-worker-statefulset.yml --ignore-not-found=true
kubectl delete -f citus-coordinator.yml --ignore-not-found=true
kubectl delete -f secret-citus.yml --ignore-not-found=true

# Eliminar PVCs que podrían quedar
kubectl delete pvc --all --ignore-not-found=true

print_success "Recursos de Kubernetes eliminados"

# 2. Terminar port-forwards
print_status "2/4 Terminando port-forwards..."
pkill -f "kubectl port-forward" || true
print_success "Port-forwards terminados"

# 3. Limpiar imágenes Docker en Minikube
print_status "3/4 Limpiando imágenes Docker en Minikube..."
eval $(minikube docker-env)
docker rmi local/fastapi-fhir:latest local/nginx-fhir:latest local/citus-custom:12.1 --force || true
docker system prune -f || true
print_success "Imágenes Docker limpiadas"

# 4. Opcional: Eliminar cluster Minikube
read -p "¿Deseas eliminar completamente el cluster Minikube? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "4/4 Eliminando cluster Minikube..."
    minikube delete
    print_success "Cluster Minikube eliminado"
else
    print_status "4/4 Manteniendo cluster Minikube..."
    print_success "Cluster Minikube preservado"
fi

print_success "🎉 Limpieza completa terminada"
print_status "El sistema está listo para un nuevo despliegue"