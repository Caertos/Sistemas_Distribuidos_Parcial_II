#!/usr/bin/env bash
# scripts/bootup-clinical.sh
# Arranca Minikube (si está detenido), opcionalmente construye la imagen
# y reinicia los deployments en el namespace `clinical-database`.
# Uso:
#   BUILD_IMAGE=1 PORT_FORWARD=1 ./scripts/bootup-clinical.sh
# - BUILD_IMAGE=1: construye `backend-api:local` en el daemon de Minikube
# - PORT_FORWARD=1: lanza un port-forward en background hacia el servicio backend (LOCAL_PORT opcional)

set -euo pipefail
LOG=/tmp/clinical-boot.log
echo "[BOOT $(date +'%Y-%m-%dT%H:%M:%S%z')] Starting clinical boot tasks" >> "$LOG"

NS="clinical-database"
LOCAL_PORT=${LOCAL_PORT:-18000}

# 1) Start minikube if not running
if ! minikube status >/dev/null 2>&1; then
  echo "Starting minikube..." | tee -a "$LOG"
  minikube start --wait=all >> "$LOG" 2>&1 || { echo "minikube start failed" | tee -a "$LOG"; exit 1; }
else
  echo "minikube already present; checking components..." | tee -a "$LOG"
  minikube status >> "$LOG" 2>&1 || true
fi

# Ensure kubectl context is minikube (non-fatal)
kubectl config use-context minikube >> "$LOG" 2>&1 || true

# 2) Optionally build backend image inside minikube docker daemon
if [ "${BUILD_IMAGE:-0}" = "1" ]; then
  echo "Building backend image inside Minikube daemon..." | tee -a "$LOG"
  eval "$(minikube docker-env)" >> "$LOG" 2>&1
  docker build -t backend-api:local -f backend/Dockerfile . >> "$LOG" 2>&1 || { echo "docker build failed" | tee -a "$LOG"; exit 1; }
fi

# 3) Restart deployments in namespace
if kubectl get namespace "$NS" >/dev/null 2>&1; then
  echo "Restarting deployments in namespace $NS..." | tee -a "$LOG"
  for dep in $(kubectl -n "$NS" get deployments -o name); do
    echo "Restarting $dep" | tee -a "$LOG"
    kubectl -n "$NS" rollout restart "$dep" >> "$LOG" 2>&1 || echo "failed restarting $dep" | tee -a "$LOG"
  done
  echo "Waiting for deployments to become available (timeout 180s)" | tee -a "$LOG"
  kubectl -n "$NS" wait --for=condition=available deployment --all --timeout=180s >> "$LOG" 2>&1 || echo "Some deployments did not become ready in time" | tee -a "$LOG"
else
  echo "Namespace $NS not found; skipping deployments restart" | tee -a "$LOG"
fi

# 4) Optional: start port-forward in background
if [ "${PORT_FORWARD:-0}" = "1" ]; then
  # Service name expected: backend-service-nodeport
  echo "Starting port-forward from localhost:${LOCAL_PORT} -> 8000 (background)" | tee -a "$LOG"
  nohup kubectl -n "$NS" port-forward svc/backend-service-nodeport ${LOCAL_PORT}:8000 >/tmp/portfw-clinical.log 2>&1 &
  echo $! > /tmp/portfw-clinical.pid
  echo "port-forward pid=$(cat /tmp/portfw-clinical.pid)" | tee -a "$LOG"
fi

echo "[BOOT $(date +'%Y-%m-%dT%H:%M:%S%z')] Done" >> "$LOG"

# Exit success
exit 0
