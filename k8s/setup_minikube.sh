#!/usr/bin/env bash
# Script de preparación para Minikube: valida dependencias, arranca Minikube y aplica manifests de Citus
# Uso: ./k8s/setup_minikube.sh

set -euo pipefail

MINIKUBE_DRIVER=${MINIKUBE_DRIVER:-docker}
MINIKUBE_MEMORY=${MINIKUBE_MEMORY:-4096}
MINIKUBE_CPUS=${MINIKUBE_CPUS:-2}
NAMESPACE=${NAMESPACE:-default}
IMAGE_TAG=${IMAGE_TAG:-local/citus-custom:12.1}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "ERROR: se necesita '$1' en PATH" >&2; exit 1; }
}

echo "1) Verificando dependencias..."
need_cmd docker
need_cmd kubectl
need_cmd minikube

echo "Dependencias OK. Driver: $MINIKUBE_DRIVER, memoria: $MINIKUBE_MEMORY, cpus: $MINIKUBE_CPUS"

echo "2) Verificando estado de Minikube..."
MINIKUBE_STATUS=$(minikube status --format='{{.Host}}' 2>/dev/null || echo "NotFound")

if [ "$MINIKUBE_STATUS" = "Running" ]; then
  echo "Minikube ya está corriendo. Reutilizando cluster existente."
elif [ "$MINIKUBE_STATUS" = "Stopped" ]; then
  echo "Minikube existe pero está detenido. Iniciando..."
  minikube start
else
  echo "Creando nuevo cluster Minikube (puede tardar 2-3 minutos)..."
  minikube start --driver="$MINIKUBE_DRIVER" --memory="$MINIKUBE_MEMORY" --cpus="$MINIKUBE_CPUS"
fi

echo "3) Esperando a que Minikube esté completamente listo..."
# Esperar a que el API server esté disponible
kubectl wait --for=condition=Ready nodes --all --timeout=180s

echo "4) Configurando contexto kubectl"
kubectl config use-context minikube
kubectl cluster-info
echo "5) Construyendo/cargando imagen personalizada para Citus: $IMAGE_TAG"

# Verificar si la imagen ya existe en Minikube
if minikube image list | grep -q "$IMAGE_TAG"; then
  echo "Imagen $IMAGE_TAG ya existe en Minikube. Saltando construcción."
else
  echo "Construyendo imagen localmente..."
  docker build -t "$IMAGE_TAG" -f ../postgres-citus/Dockerfile ../postgres-citus/
  echo "Cargando imagen en Minikube..."
  minikube image load "$IMAGE_TAG"
  echo "Imagen cargada exitosamente."
fi

echo "6) Aplicando Secret y manifests de Citus"
echo "   - Aplicando secret..."
kubectl apply -f secret-citus.yml
echo "   - Aplicando coordinator..."
kubectl apply -f citus-coordinator.yml
echo "   - Aplicando workers..."
kubectl apply -f citus-worker-statefulset.yml
echo "   ✓ Manifests aplicados"

echo "7) Esperando a que los pods estén listos..."
echo "   - Esperando coordinator..."
kubectl wait --for=condition=ready pod -l app=citus-coordinator -n "$NAMESPACE" --timeout=300s
echo "   - Esperando workers..."
kubectl wait --for=condition=ready pod -l app=citus-worker -n "$NAMESPACE" --timeout=300s
echo "   ✓ Todos los pods están Ready"

echo "8) Estado actual de los pods:"
kubectl get pods -l 'app in (citus-coordinator,citus-worker)' -o wide

echo "9) Esperando 30s adicionales para que PostgreSQL inicialice completamente..."
sleep 30

echo "10) Registrar workers automáticamente y ejecutar rebalance/drain"
# Ejecutar el script de registro (internamente hace citus_set_coordinator_host y citus_add_node)
./register_citus_k8s.sh --rebalance --drain

echo "11) Levantando port-forward para exponer el coordinator en localhost:5432 (background)"
# Lanzar port-forward en background y enviar logs a un archivo para depuración
kubectl port-forward --namespace "$NAMESPACE" svc/citus-coordinator 5432:5432 > /tmp/citus_port_forward.log 2>&1 &
PF_PID=$!
echo "Port-forward pid: $PF_PID (logs en /tmp/citus_port_forward.log)"

echo "12) Esperando 10s para que el port-forward se establezca..."
sleep 10

echo "13) Ejecutando verificación automática (verify_lab.sh)"
K8S_VERIFY_TIMEOUT=${K8S_VERIFY_TIMEOUT:-120}
export PGPASSWORD=${PGPASSWORD:-postgres}
TRIES=0
until ./verify_lab.sh; do
  TRIES=$((TRIES+1))
  if [ "$TRIES" -ge 6 ]; then
    echo "verify_lab.sh falló repetidamente; mira /tmp/citus_port_forward.log y los logs de pods." >&2
    exit 1
  fi
  echo "verify_lab.sh falló; reintentando en 10s... (intento $TRIES)"
  sleep 10
done

echo "Setup Minikube completado y verificado. Si quieres detener port-forward: kill $PF_PID" 
