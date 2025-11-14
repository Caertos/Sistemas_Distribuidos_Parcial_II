#!/usr/bin/env bash
set -euo pipefail

TITLE="=== Desplegando Postgres-Citus en Minikube ==="
echo
echo "$TITLE"
echo

# Rutas
K8S_DIR="$(dirname "${BASH_SOURCE[0]}")/../../k8s/1-CitusSql"
POSTGRES_CITUS_DIR="$(dirname "${BASH_SOURCE[0]}")/../../postgres-citus"

# Timeouts (segundos)
STATEFULSET_TIMEOUT=300
JOB_TIMEOUT=180

command_exists() { command -v "$1" >/dev/null 2>&1; }

for cmd in minikube kubectl docker; do
  if ! command_exists "$cmd"; then
    echo "ERROR: '$cmd' no está instalado o no está en PATH" >&2
    exit 1
  fi
done

echo "Construyendo imagen 'postgres-citus:local' en el entorno Docker de minikube..."
# Guardar entorno actual y activar Docker de minikube
eval "$(minikube -p minikube docker-env)"

if [ -d "$POSTGRES_CITUS_DIR" ]; then
  docker build -t postgres-citus:local "$POSTGRES_CITUS_DIR"
else
  echo "WARN: No se encontró el directorio $POSTGRES_CITUS_DIR, asumiendo que la imagen ya existe en minikube." >&2
fi

# Aplicar manifests
echo "Aplicando manifests en $K8S_DIR..."
kubectl apply -f "$K8S_DIR/citus-namespace.yaml"
kubectl apply -f "$K8S_DIR/citus-statefulsets.yaml"

echo "Esperando que el statefulset 'citus-coordinator' esté listo (timeout ${STATEFULSET_TIMEOUT}s)..."
kubectl rollout status statefulset/citus-coordinator -n clinical-database --timeout=${STATEFULSET_TIMEOUT}s

echo "Esperando que los workers 'citus-worker' estén listos (timeout ${STATEFULSET_TIMEOUT}s)..."
kubectl rollout status statefulset/citus-worker -n clinical-database --timeout=${STATEFULSET_TIMEOUT}s

echo "Iniciando job de inicialización (citus-init-db)..."
kubectl apply -f "$K8S_DIR/citus-init-job.yaml"

echo "Esperando completion del job 'citus-init-db' (timeout ${JOB_TIMEOUT}s)..."
kubectl wait --for=condition=complete job/citus-init-db -n clinical-database --timeout=${JOB_TIMEOUT}s || {
  echo "ERROR: El job de inicialización no completó correctamente" >&2
  kubectl logs job/citus-init-db -n clinical-database || true
  exit 1
}

echo
echo "La base de datos y los pods en el namespace 'clinical-database' deberían estar levantándose."

# Esperar que los pods en el namespace clinical-database estén listos (timeout)
PODS_TIMEOUT=180
PODS_INTERVAL=5
pods_elapsed=0
echo "Esperando que los pods en 'clinical-database' estén listos (timeout ${PODS_TIMEOUT}s)..."
while [ "$pods_elapsed" -lt "$PODS_TIMEOUT" ]; do
  problems=0
  while IFS= read -r line; do
    name=$(echo "$line" | awk '{print $1}')
    ready_field=$(echo "$line" | awk '{print $2}')
    status_field=$(echo "$line" | awk '{print $3}')
    ready_num=$(echo "$ready_field" | cut -d/ -f1 || true)
    ready_den=$(echo "$ready_field" | cut -d/ -f2 || true)

    if [ -n "$ready_num" ] && [ -n "$ready_den" ]; then
      if [ "$ready_num" != "$ready_den" ]; then
        problems=$((problems+1))
        echo "  - Pod no listo: $name (READY=${ready_field}, STATUS=${status_field})"
      fi
    else
      if echo "$status_field" | grep -E "Pending|CrashLoopBackOff|Error|ImagePullBackOff" >/dev/null; then
        problems=$((problems+1))
        echo "  - Pod problemático: $name (STATUS=${status_field})"
      fi
    fi
  done < <(kubectl get pods -n clinical-database --no-headers 2>/dev/null || true)

  if [ "$problems" -eq 0 ]; then
    echo "Todos los pods en 'clinical-database' están listos"
    break
  fi

  echo "Quedan ${problems} pods problemáticos en 'clinical-database'; reintentando en ${PODS_INTERVAL}s..."
  sleep "$PODS_INTERVAL"
  pods_elapsed=$((pods_elapsed + PODS_INTERVAL))
done

if [ "$pods_elapsed" -ge "$PODS_TIMEOUT" ]; then
  echo "ERROR: Timeout esperando pods listos en 'clinical-database'" >&2
  kubectl get pods -n clinical-database || true
  exit 1
fi

# Preguntar si poblar la DB
read -r -p "¿Deseas poblar la base de datos ahora? (s/n): " RESP
if [[ "${RESP,,}" == "s" ]]; then
  POPULATE_SCRIPT="$K8S_DIR/populate_db_k8s.sh"
  if [ ! -f "$POPULATE_SCRIPT" ]; then
    echo "ERROR: No se encontró $POPULATE_SCRIPT" >&2
    exit 1
  fi

  echo "Dando permisos de ejecución al script de población y ejecutándolo..."
  chmod +x "$POPULATE_SCRIPT"
  "$POPULATE_SCRIPT"
  echo
  echo "✅ Población de la base de datos finalizada con éxito"
else
  echo "Se omitió la población de la base de datos."
fi

echo
echo "¡Despliegue de Postgres-Citus finalizado correctamente! ✅"

