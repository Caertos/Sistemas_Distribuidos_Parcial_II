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

echo "2) Arrancando Minikube (puede tardar)..."
# Intentamos arrancar minikube; si existe y está detenido, lo start
if minikube status >/dev/null 2>&1; then
  echo "Minikube ya existe; intentando start..."
  minikube start --driver="$MINIKUBE_DRIVER" || true
else
  minikube start --driver="$MINIKUBE_DRIVER" --memory="$MINIKUBE_MEMORY" --cpus="$MINIKUBE_CPUS"
fi

echo "3) Configurando contexto kubectl y addons mínimos"
kubectl config current-context || true
echo "4) Construyendo/cargando imagen personalizada para Citus: $IMAGE_TAG"

# Intentar construir la imagen directamente en Minikube (si soportado).
if minikube image build -t "$IMAGE_TAG" -f postgres-citus/Dockerfile postgres-citus/; then
  echo "Imagen construida en Minikube: $IMAGE_TAG"
else
  echo "minikube image build no disponible o falló; construyendo localmente y cargando en Minikube..."
  docker build -t "$IMAGE_TAG" -f postgres-citus/Dockerfile postgres-citus/
  echo "Cargando imagen en Minikube..."
  minikube image load "$IMAGE_TAG"
fi

echo "5) Aplicando Secret y manifests de Citus"
kubectl apply -f k8s/secret-citus.yml
kubectl apply -f k8s/citus-coordinator.yml
kubectl apply -f k8s/citus-worker-statefulset.yml

echo "6) Esperando pods listos (coordinator y workers)"
kubectl wait --for=condition=ready pod -l app=citus-coordinator -n "$NAMESPACE" --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=citus-worker -n "$NAMESPACE" --timeout=300s || true

echo "7) Resultado: listar pods"
kubectl get pods -l 'app in (citus-coordinator,citus-worker)' -o wide

echo "8) Registrar workers automáticamente y ejecutar rebalance/drain"
# Ejecutar el script de registro (internamente hace citus_set_coordinator_host y master_add_node)
./k8s/register_citus_k8s.sh --rebalance --drain

echo "9) Levantando port-forward para exponer el coordinator en localhost:5432 (background)"
# Lanzar port-forward en background y enviar logs a un archivo para depuración
kubectl port-forward --namespace "$NAMESPACE" svc/citus-coordinator 5432:5432 > /tmp/citus_port_forward.log 2>&1 &
PF_PID=$!
echo "Port-forward pid: $PF_PID (logs en /tmp/citus_port_forward.log)"

echo "10) Ejecutando verificación automática (verify_lab.sh)"
K8S_VERIFY_TIMEOUT=${K8S_VERIFY_TIMEOUT:-120}
export PGPASSWORD=${PGPASSWORD:-postgres}
TRIES=0
until ./k8s/verify_lab.sh; do
  TRIES=$((TRIES+1))
  if [ "$TRIES" -ge 6 ]; then
    echo "verify_lab.sh falló repetidamente; mira /tmp/citus_port_forward.log y los logs de pods." >&2
    exit 1
  fi
  echo "verify_lab.sh falló; reintentando en 10s... (intento $TRIES)"
  sleep 10
done

echo "Setup Minikube completado y verificado. Si quieres detener port-forward: kill $PF_PID" 
