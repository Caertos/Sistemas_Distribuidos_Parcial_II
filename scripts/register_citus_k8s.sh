#!/usr/bin/env bash
# Script para registrar workers en un cluster Kubernetes (Minikube)
# Uso: ./register_citus_k8s.sh [--rebalance] [--drain]

set -eu

DB_NAME=${DB_NAME:-hce_distribuida}
NAMESPACE=${NAMESPACE:-default}

# workers esperados: citus-worker-0.citus-worker, citus-worker-1.citus-worker, ...
WORKER_COUNT=${WORKER_COUNT:-2}

# opciones
DO_REBALANCE=false
DO_DRAIN=false
for arg in "$@"; do
  case "$arg" in
    --rebalance) DO_REBALANCE=true ;; 
    --drain) DO_DRAIN=true ;; 
    --help|-h)
      echo "Uso: $0 [--rebalance] [--drain]"
      exit 0
      ;;
  esac
done

# esperar a que el coordinator esté listo
echo "Esperando pod del coordinator..."
kubectl wait --for=condition=ready pod -l app=citus-coordinator -n "$NAMESPACE" --timeout=180s
COORD_POD=$(kubectl get pods -l app=citus-coordinator -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}')

echo "Coordinator pod: $COORD_POD"

# configurar hostname del coordinator para que los workers se conecten por DNS
echo "Setting coordinator host to 'citus-coordinator'"
kubectl exec -n "$NAMESPACE" "$COORD_POD" -- psql -U postgres -d "$DB_NAME" -c "SELECT citus_set_coordinator_host('citus-coordinator');" || true

# registrar cada worker por su DNS estable
for i in $(seq 0 $((WORKER_COUNT-1))); do
  worker_host="citus-worker-$i.citus-worker"
  echo "Registrando worker: $worker_host"
  # Usar citus_add_node en lugar de master_add_node (función moderna)
  kubectl exec -n "$NAMESPACE" "$COORD_POD" -- psql -U postgres -d "$DB_NAME" -c "SELECT citus_add_node('$worker_host',5432);" || true
done

if [ "$DO_REBALANCE" = true ]; then
  echo "Ejecutando rebalance_table_shards()"
  kubectl exec -n "$NAMESPACE" "$COORD_POD" -- psql -U postgres -d "$DB_NAME" -c "SELECT rebalance_table_shards();" || true
fi

if [ "$DO_DRAIN" = true ]; then
  echo "Ejecutando citus_drain_node('citus-coordinator',5432)"
  kubectl exec -n "$NAMESPACE" "$COORD_POD" -- psql -U postgres -d "$DB_NAME" -c "SELECT citus_drain_node('citus-coordinator',5432);" || true
fi

echo "Registro finalizado. Revisa los logs y el estado de los pods."
