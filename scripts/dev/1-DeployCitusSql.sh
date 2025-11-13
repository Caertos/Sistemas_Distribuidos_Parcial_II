#!/usr/bin/env bash
set -euo pipefail

# PARA PRUEBAS: este script expone el coordinator mediante NodePort (puerto 30007)
# NO usar esta configuración en producción. Está pensada sólo para pruebas/QA


ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Encabezado informativo (con color cyan)
CYAN='\033[0;36m'
NC='\033[0m'

cat <<HEADER
${CYAN}==================================================
INICIANDO INSTALACION DE BASE DE DATOS DISTRIBUIDA
==================================================${NC}
HEADER

echo "ROOT_DIR=$ROOT_DIR"

IMAGE_NAME="postgres-citus:local"
# Namespace por defecto; si existe el manifest lo sobrescribimos
NAMESPACE="ClinicalDataBase"

set -euo pipefail

log() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
err() { echo "[ERROR] $*" >&2; }

ensure_command() {
	if ! command -v "$1" >/dev/null 2>&1; then
		err "Se necesita '$1' pero no está instalado o no está en PATH."
		exit 1
	fi
}

log "1) Preparando entorno k8s / docker"
ensure_command kubectl

# Intentar extraer el namespace desde el manifest si existe y normalizarlo a RFC1123 (minusculas y '-')
if [ -f "$ROOT_DIR/k8s/1-CitusSql/citus-namespace.yaml" ]; then
	ns_from_file=$(sed -n 's/^[[:space:]]*name:[[:space:]]*\([^[:space:]]\+\)[[:space:]]*$/\1/p' "$ROOT_DIR/k8s/1-CitusSql/citus-namespace.yaml" | head -n1 || true)
	if [ -n "$ns_from_file" ]; then
		# Normalizar: minusculas, reemplazar caracteres inválidos por '-', eliminar guiones al inicio/fin
		ns_normalized=$(echo "$ns_from_file" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/^-*//; s/-*$//')
		if [ -z "$ns_normalized" ]; then
			warn "El namespace extraído '$ns_from_file' no es convertible a un nombre válido; se usará: $NAMESPACE"
		else
			if [ "$ns_normalized" != "$ns_from_file" ]; then
				warn "Namespace en manifest ('$ns_from_file') no cumple RFC1123; se usará la versión normalizada: $ns_normalized"
			else
				log "Namespace detectado en manifest: $ns_normalized"
			fi
			NAMESPACE="$ns_normalized"
		fi
	else
		warn "No se pudo extraer namespace desde k8s/1-CitusSql/citus-namespace.yaml; se usará: $NAMESPACE"
	fi
else
	warn "Manifest k8s/1-CitusSql/citus-namespace.yaml no encontrado; se usará namespace por defecto: $NAMESPACE"
fi

# Comprobar si hay contexto activo
current_ctx=$(kubectl config current-context 2>/dev/null || true)
if [ -z "$current_ctx" ]; then
	warn "kubectl no tiene current-context configurado. Intentando arrancar/usar un cluster local..."

	if command -v minikube >/dev/null 2>&1; then
		log "minikube detectado. Iniciando minikube (si no está ya running)..."
		if ! minikube status >/dev/null 2>&1; then
			minikube start
		fi
		kubectl config use-context minikube || true
		current_ctx=$(kubectl config current-context 2>/dev/null || true)
		log "Context actual: $current_ctx"
	elif command -v kind >/dev/null 2>&1; then
		log "kind detectado. Creando cluster 'citus-kind' si no existe..."
		if ! kind get clusters | grep -q '^citus-kind$'; then
			kind create cluster --name citus-kind
		fi
		kubectl cluster-info --context kind-citus-kind >/dev/null 2>&1 || true
		kubectl config use-context kind-citus-kind || true
		current_ctx=$(kubectl config current-context 2>/dev/null || true)
		log "Context actual: $current_ctx"
	elif [ -n "${KUBECONFIG-}" ] && [ -f "$KUBECONFIG" ]; then
		log "Usando KUBECONFIG definido: $KUBECONFIG"
		current_ctx=$(kubectl config current-context 2>/dev/null || true)
	else
		err "No hay contexto de Kubernetes activo y no se detectó minikube ni kind. Exporta KUBECONFIG o instala minikube/kind."
		exit 1
	fi
else
	log "kubectl current-context: $current_ctx"
fi

log "2) Construyendo la imagen de Citus desde $ROOT_DIR/postgres-citus"
cd "$ROOT_DIR/postgres-citus"

# Construir y cargar la imagen en el runtime correspondiente
if command -v minikube >/dev/null 2>&1 && kubectl config current-context 2>/dev/null | grep -q minikube; then
	log "Construyendo imagen y cargándola en minikube"
	docker build -t "$IMAGE_NAME" .
	log "Cargando imagen en minikube..."
	minikube image load "$IMAGE_NAME"
elif command -v kind >/dev/null 2>&1 && kubectl config current-context 2>/dev/null | grep -q citus-kind; then
	log "Construyendo imagen y cargándola en kind (citus-kind)"
	docker build -t "$IMAGE_NAME" .
	kind load docker-image --name citus-kind "$IMAGE_NAME"
else
	log "Construyendo imagen local con docker (suponiendo que el cluster puede acceder a imágenes locales)"
	docker build -t "$IMAGE_NAME" .
fi

log "3) Aplicando manifests k8s"
cd "$ROOT_DIR"

# Intentamos aplicar normalmente; si falla por error de validación OpenAPI, reintentamos con --validate=false
apply_manifest() {
	local file="$1"
	if ! kubectl apply -f "$file"; then
		# Detectar error común de OpenAPI/local validation intentando reintentar con --validate=false
		warn "kubectl apply falló al aplicar $file; reintentando con --validate=false"
		kubectl apply -f "$file" --validate=false
	fi
}

# Si el manifest de namespace existía pero el nombre original era inválido, generamos un manifest corregido
ns_manifest_path="$ROOT_DIR/k8s/1-CitusSql/citus-namespace.yaml"
if [ -f "$ns_manifest_path" ]; then
	# extraer nombre original si existe
	orig_ns=$(sed -n 's/^[[:space:]]*name:[[:space:]]*\([^[:space:]]\+\)[[:space:]]*$/\1/p' "$ns_manifest_path" | head -n1 || true)
	if [ -n "$orig_ns" ] && [ "$orig_ns" != "$NAMESPACE" ]; then
		warn "Creando manifest temporal de Namespace con nombre corregido: $NAMESPACE"
		tmp_ns_manifest=$(mktemp)
		cat > "$tmp_ns_manifest" <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: $NAMESPACE
EOF
		apply_manifest "$tmp_ns_manifest"
		rm -f "$tmp_ns_manifest"
	else
		apply_manifest "$ns_manifest_path"
	fi
fi

apply_manifest k8s/1-CitusSql/citus-statefulsets.yaml
apply_manifest k8s/1-CitusSql/citus-init-job.yaml

log "4) Esperando pods (coordinator + workers) hasta que estén listos"
kubectl -n "$NAMESPACE" wait --for=condition=ready pod -l app=citus-coordinator --timeout=180s || true
kubectl -n "$NAMESPACE" wait --for=condition=ready pod -l app=citus-worker --timeout=180s || true

log "5) Esperando a que el Job de inicialización (citus-init-db) termine (si se ejecutó)"
kubectl -n "$NAMESPACE" wait --for=condition=complete --timeout=120s job/citus-init-db || echo "Job 'citus-init-db' no llegó a completar en 120s. Revisa: kubectl -n $NAMESPACE logs job/citus-init-db"

echo "Hecho. Para acceder al coordinator desde fuera de minikube (PARA PRUEBAS):"
echo "- Si usas minikube: minikube service citus-coordinator -n $NAMESPACE --url"
echo "- O acceder al nodo:puerto -> NodePort 30007 (si tu cluster lo permite)"

echo "Ver pods: kubectl -n $NAMESPACE get pods"
echo "Ver servicios: kubectl -n $NAMESPACE get svc"

