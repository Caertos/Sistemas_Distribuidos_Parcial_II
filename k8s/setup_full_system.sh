#!/usr/bin/env bash
# Script completo de setup para el Sistema FHIR en Kubernetes
# Incluye construcción de imágenes, despliegue de Citus, FastAPI y población de datos

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

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { 
    print_error "Se necesita '$1' en PATH" 
    exit 1 
  }
}

print_status "🚀 Iniciando setup completo del Sistema FHIR en Kubernetes"

# 1. Verificar dependencias
print_status "1/10 Verificando dependencias..."
need_cmd docker
need_cmd kubectl
need_cmd minikube
print_success "Dependencias verificadas"

# 2. Setup Minikube
print_status "2/10 Configurando Minikube..."
MINIKUBE_STATUS=$(minikube status --format='{{.Host}}' 2>/dev/null || echo "NotFound")

if [ "$MINIKUBE_STATUS" = "Running" ]; then
  print_warning "Minikube ya está corriendo. Reutilizando cluster existente."
elif [ "$MINIKUBE_STATUS" = "Stopped" ]; then
  print_status "Minikube existe pero está detenido. Iniciando..."
  minikube start
else
  print_status "Creando nuevo cluster Minikube..."
  minikube start --driver="$MINIKUBE_DRIVER" --memory="$MINIKUBE_MEMORY" --cpus="$MINIKUBE_CPUS"
fi

kubectl config use-context minikube
kubectl wait --for=condition=Ready nodes --all --timeout=180s
print_success "Minikube configurado y listo"

# 3. Construir imágenes Docker
print_status "3/10 Construyendo imágenes Docker..."

# Configurar docker para usar el daemon de minikube
eval $(minikube docker-env)

# Construir imagen de Citus
print_status "Construyendo imagen de Citus..."
docker build -t local/citus-custom:12.1 -f ../postgres-citus/Dockerfile ../postgres-citus/

# Construir imagen de FastAPI
print_status "Construyendo imagen de FastAPI..."
docker build -t local/fastapi-fhir:latest -f ../fastapi-app/Dockerfile ../fastapi-app/

# Construir imagen de Nginx (saltado temporalmente)
print_warning "Omitiendo construcción de Nginx por ahora..."
# docker build -t local/nginx-fhir:latest -f ../nginx/Dockerfile ../nginx/

print_success "Imágenes Docker construidas"

# 4. Desplegar Citus
print_status "4/10 Desplegando base de datos Citus..."
kubectl apply -f secret-citus.yml
kubectl apply -f citus-coordinator.yml
kubectl apply -f citus-worker-statefulset.yml

print_status "Esperando a que Citus esté listo..."
kubectl wait --for=condition=ready pod -l app=citus-coordinator --timeout=300s
kubectl wait --for=condition=ready pod -l app=citus-worker --timeout=300s
print_success "Citus desplegado y listo"

# 5. Configurar workers de Citus
print_status "5/10 Configurando workers de Citus..."
sleep 30
./register_citus_k8s.sh --rebalance --drain
print_success "Workers de Citus configurados"

# 6. Desplegar FastAPI
print_status "6/10 Desplegando aplicación FastAPI..."
kubectl apply -f fastapi-deployment.yml

print_status "Esperando a que FastAPI esté listo..."
kubectl wait --for=condition=ready pod -l app=fastapi-app --timeout=300s
print_success "FastAPI desplegado y listo"

# 7. Desplegar Nginx (omitido temporalmente)
print_status "7/10 Omitiendo despliegue de Nginx..."
print_warning "Nginx omitido - acceso directo a FastAPI"
# kubectl apply -f nginx-deployment.yml
# kubectl wait --for=condition=ready pod -l app=nginx-proxy --timeout=180s
print_success "Nginx omitido correctamente"

# 8. Poblar datos
print_status "8/10 Poblando base de datos con datos de prueba..."
kubectl apply -f data-population-job.yml

print_status "Esperando a que el job de población complete..."
kubectl wait --for=condition=complete job/data-population-job --timeout=300s
print_success "Datos de prueba insertados"

# 9. Configurar acceso externo
print_status "9/10 Configurando acceso externo..."

# Port-forward para FastAPI (background)
kubectl port-forward svc/fastapi-app 8000:8000 > /tmp/fastapi_port_forward.log 2>&1 &
FASTAPI_PF_PID=$!

# Port-forward para Nginx omitido
# kubectl port-forward svc/nginx-proxy 8080:80 > /tmp/nginx_port_forward.log 2>&1 &
# NGINX_PF_PID=$!

# Obtener URLs de Minikube
FASTAPI_URL=$(minikube service fastapi-app-nodeport --url)
NGINX_URL="No desplegado"

print_success "Acceso externo configurado"

# 10. Verificación final
print_status "10/10 Verificación final del sistema..."
sleep 15

# Verificar salud de FastAPI
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    print_success "FastAPI está respondiendo correctamente"
else
    print_warning "FastAPI podría no estar completamente listo"
fi

# Mostrar estado de pods
print_status "Estado de todos los pods:"
kubectl get pods -o wide

echo ""
print_success "🎉 ¡Setup completo del Sistema FHIR en Kubernetes terminado!"
echo ""
print_status "📋 Información de acceso:"
echo "  📌 FastAPI (port-forward): http://localhost:8000"
echo "  📌 FastAPI (NodePort): $FASTAPI_URL"
echo "  📌 Nginx (port-forward): http://localhost:8080"
echo "  📌 Nginx (NodePort): $NGINX_URL"
echo "  📌 Documentación API: http://localhost:8000/docs"
echo "  📌 Login: http://localhost:8000/login"
echo ""
print_status "🔑 Credenciales de acceso:"
echo "  👤 Paciente: paciente / paciente123"
echo "  👩‍⚕️ Médico: medico / medico123"
echo "  👨‍💼 Admin: admin / admin123"
echo "  🔍 Auditor: auditor / auditor123"
echo ""
print_status "🛠️ Comandos útiles:"
echo "  Ver logs FastAPI: kubectl logs -l app=fastapi-app -f"
echo "  Ver logs Citus: kubectl logs -l app=citus-coordinator -f"
echo "  Detener port-forwards: kill $FASTAPI_PF_PID"
echo "  Escalar FastAPI: kubectl scale deployment fastapi-app --replicas=3"
echo ""
print_status "Para limpiar el entorno:"
echo "  kubectl delete -f ."
echo "  minikube delete"