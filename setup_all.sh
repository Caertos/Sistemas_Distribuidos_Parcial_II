#!/usr/bin/env bash
# setup_all.sh - script todo-en-uno para el laboratorio
# Uso:
#   ./setup_all.sh compose   # levantar con docker-compose y registrar
#   ./setup_all.sh minikube  # levantar con minikube y registrar
# Si no se pasa argumento, por defecto usa 'compose'.

set -euo pipefail

MODE=${1:-compose}

case "$MODE" in
  compose)
    echo "==> Modo: docker-compose (rápido para laboratorio)"
    echo "Levantando servicios con docker compose..."
    docker compose up -d
    echo "Esperando 5s para que Postgres inicie..."
    sleep 5
    echo "Ejecutando registro y rebalance en entorno docker-compose..."
    bash register_citus.sh --rebalance --drain
    echo "Hecho: servicios levantados y registro ejecutado (docker-compose)."
    ;;
  minikube)
    echo "==> Modo: Minikube"
    echo "Ejecutando k8s/setup_minikube.sh"
    ./k8s/setup_minikube.sh
    echo "Ejecutando registro en cluster Minikube"
    ./k8s/register_citus_k8s.sh --rebalance --drain
    echo "Hecho: Minikube desplegado y registro ejecutado."
    ;;
  *)
    echo "Uso: $0 [compose|minikube]"
    exit 1
    ;;
esac
