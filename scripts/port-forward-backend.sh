#!/usr/bin/env bash
# Script para hacer port-forward al servicio backend-service-nodeport
# Uso: ./scripts/port-forward-backend.sh [LOCAL_PORT]
# Por defecto usa LOCAL_PORT=8000

set -euo pipefail

LOCAL_PORT=${1:-8000}
NAMESPACE="clinical-database"
SERVICE="backend-service-nodeport"
TARGET_PORT=8000

function err(){ echo "[ERROR] $*" >&2; }
function info(){ echo "[INFO] $*"; }

# Comprobaciones básicas
if ! command -v kubectl >/dev/null 2>&1; then
  err "kubectl no está instalado o no está en PATH"
  exit 2
fi

# Comprobar que el namespace existe
if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  err "Namespace '$NAMESPACE' no encontrado"
  kubectl get namespaces || true
  exit 3
fi

info "Iniciando port-forward: local $LOCAL_PORT -> svc/$SERVICE:$TARGET_PORT (namespace: $NAMESPACE)"
info "Presiona Ctrl+C para detener"

# Ejecutar port-forward en primer plano
kubectl -n "$NAMESPACE" port-forward "svc/$SERVICE" "$LOCAL_PORT:$TARGET_PORT"
