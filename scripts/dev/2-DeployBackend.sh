#!/usr/bin/env bash
set -euo pipefail

TITLE="=== Desplegando Backend en Minikube ==="
echo
echo "$TITLE"
echo

# Directorio k8s del backend
K8S_DIR="$(dirname "${BASH_SOURCE[0]}")/../../k8s/2-Backend"

# Namespace por defecto (puedes pasar otro como primer argumento)
NAMESPACE="${1:-clinical-database}"

 # Helper: construir imagen usando Minikube (preferible) o caida a docker-env
 build_image_minikube() {
	local image="$1"; shift
	local dockerfile="$1"; shift
	local context="$1"; shift

	echo "Preparando build de imagen: $image (dockerfile=$dockerfile, context=$context)"

	# Intentar usar 'minikube image build' (no requiere docker local)
	if minikube image build -h >/dev/null 2>&1; then
		echo "Usando 'minikube image build' para crear $image"
		if minikube image build -t "$image" -f "$dockerfile" "$context"; then
			echo "Imagen '$image' construida en Minikube"
			return 0
		else
			echo "WARN: fallo 'minikube image build' para $image, intentando fallback a docker" >&2
		fi
	fi

	# Fallback: cargar en docker del minikube activando docker-env
	echo "Fallback: activando docker-env de Minikube y usando 'docker build'"
	eval "$(minikube -p minikube docker-env)" >/dev/null 2>&1 || true
	if ! command -v docker >/dev/null 2>&1; then
		echo "ERROR: docker no disponible para fallback build" >&2
		return 1
	fi

	if docker build -f "$dockerfile" -t "$image" "$context"; then
		echo "Imagen '$image' construida en Docker de Minikube (fallback)"
		return 0
	fi

	echo "ERROR: fallo al construir la imagen $image" >&2
	return 1
}


# Construye la imagen del backend dentro del Docker de Minikube si no existe.
# Esto evita ImagePullBackOff cuando el deployment usa la imagen local `backend-api:local`.
ensure_backend_image_in_minikube() {
	BACKEND_DIR="$(dirname "${BASH_SOURCE[0]}")/../../backend"
	PROJECT_ROOT="$(dirname "${BASH_SOURCE[0]}")/../.."
	echo "Comprobando imagen 'backend-api:local' en Docker de Minikube..."
	if [ ! -d "$BACKEND_DIR" ]; then
		echo "WARN: No se encontró el directorio del backend en $BACKEND_DIR. Omitiendo build de imagen local."
		return 0
	fi

	if kubectl get nodes >/dev/null 2>&1; then
		if kubectl -n kube-system get pods >/dev/null 2>&1; then
			: # cluster accesible
		fi
	fi

	# Si la imagen ya existe localmente en el daemon de minikube, no reconstruir
	eval "$(minikube -p minikube docker-env)" >/dev/null 2>&1 || true
	if command -v docker >/dev/null 2>&1 && docker image inspect backend-api:local >/dev/null 2>&1; then
		echo "Imagen 'backend-api:local' ya presente en Docker de Minikube."
		return 0
	fi

	echo "Construyendo imagen 'backend-api:local' en Minikube desde: $PROJECT_ROOT"
	echo "  (usando Dockerfile en backend/ con contexto en raíz del proyecto)"
	build_image_minikube "backend-api:local" "$BACKEND_DIR/Dockerfile" "$PROJECT_ROOT" || {
		echo "ERROR: fallo construyendo la imagen backend-api:local" >&2
		return 1
	}
	echo "Imagen 'backend-api:local' construida correctamente."
}

TIMEOUT_ROLLOUT=180

command_exists() { command -v "$1" >/dev/null 2>&1; }

for cmd in minikube kubectl; do
	if ! command_exists "$cmd"; then
		echo "ERROR: '$cmd' no está instalado o no está en PATH" >&2
		exit 1
	fi
done

if [ ! -d "$K8S_DIR" ]; then
	echo "ERROR: No se encontró el directorio de manifests: $K8S_DIR" >&2
	exit 1
fi

# Asegurar que el namespace exista
if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  echo "Namespace '$NAMESPACE' no existe. Creándolo..."
  kubectl create namespace "$NAMESPACE" || true
fi

echo "Aplicando manifests del backend en namespace '$NAMESPACE' desde $K8S_DIR..."
# Asegurar que la imagen local del backend esté disponible en Minikube antes de aplicar manifests
ensure_backend_image_in_minikube || { echo "ERROR: No se pudo preparar la imagen del backend en Minikube" >&2; exit 1; }

# Aplicar los manifests en el namespace objetivo; si los manifests contienen namespace propio, kubectl reportará y seguirá
kubectl apply -f "$K8S_DIR" -n "$NAMESPACE" || kubectl apply -f "$K8S_DIR" || true

echo "Esperando despliegues en namespace '$NAMESPACE'..."
deploys=$(kubectl get deployments -n "$NAMESPACE" --no-headers -o custom-columns=NAME:.metadata.name 2>/dev/null || true)
if [ -z "$deploys" ]; then
	echo "No se detectaron Deployments en namespace '$NAMESPACE'. Se verificarán Pods directamente."
else
	for d in $deploys; do
		echo " - Esperando rollout del deployment: $d"
		if ! kubectl rollout status deployment/$d -n "$NAMESPACE" --timeout=${TIMEOUT_ROLLOUT}s; then
			echo "WARNING: Rollout failed o timeout para deployment $d — intentar remedial: forzar set-image y restart" >&2
			# Forzar que el deployment use la imagen local y reiniciar el rollout
			kubectl -n "$NAMESPACE" set image deployment/$d backend=backend-api:local || true
			kubectl rollout restart deployment/$d -n "$NAMESPACE" || true
			# Intentar de nuevo con un timeout mayor
			kubectl rollout status deployment/$d -n "$NAMESPACE" --timeout=300s || {
				echo "ERROR: Rollout still failed después del restart para deployment $d" >&2
				kubectl describe deployment/$d -n "$NAMESPACE" || true
				kubectl get pods -n "$NAMESPACE" || true
				exit 1
			}
		fi
	done
fi

echo "Verificando pods en namespace '$NAMESPACE'..."
unready=0
while IFS= read -r line; do
	name=$(echo "$line" | awk '{print $1}')
	ready_field=$(echo "$line" | awk '{print $2}')
	status_field=$(echo "$line" | awk '{print $3}')
		# Ignorar pods de jobs Completed (inicializadores)
		if [ "$status_field" = "Completed" ]; then
			continue
		fi
	ready_num=$(echo "$ready_field" | cut -d/ -f1 || true)
	ready_den=$(echo "$ready_field" | cut -d/ -f2 || true)
	if [ -n "$ready_num" ] && [ -n "$ready_den" ]; then
		if [ "$ready_num" != "$ready_den" ]; then
			unready=$((unready+1))
			echo "  - Pod no listo: $name (READY=${ready_field}, STATUS=${status_field})"
		fi
	else
		if echo "$status_field" | grep -E "Pending|CrashLoopBackOff|Error|ImagePullBackOff" >/dev/null; then
			unready=$((unready+1))
			echo "  - Pod problemático: $name (STATUS=${status_field})"
		fi
	fi
done < <(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null || true)

if [ "$unready" -gt 0 ]; then
	echo "ERROR: Se detectaron ${unready} pods no listos en '$NAMESPACE'" >&2
	kubectl get pods -n "$NAMESPACE" || true
	exit 1
fi

echo "Revisando servicios expuestos en namespace '$NAMESPACE'..."
services=$(kubectl get svc -n "$NAMESPACE" --no-headers -o custom-columns=NAME:.metadata.name,TYPE:.spec.type,PORT:.spec.ports[0].port 2>/dev/null || true)
echo "$services" | while IFS= read -r svcline; do
	svcname=$(echo "$svcline" | awk '{print $1}')
	svctype=$(echo "$svcline" | awk '{print $2}')
	svcport=$(echo "$svcline" | awk '{print $3}')
	if [ -z "$svcname" ]; then
		continue
	fi
	echo " - Servicio: $svcname (type=$svctype, port=$svcport)"
	if [ "$svctype" = "NodePort" ]; then
		# intentar obtener URL con minikube
		url=$(minikube service "$svcname" -n "$NAMESPACE" --url 2>/dev/null || true)
		if [ -n "$url" ]; then
			echo "   -> Accesible en: $url"
		else
			echo "   -> Servicio NodePort pero no se obtuvo URL con 'minikube service'"
		fi
	elif [ "$svctype" = "ClusterIP" ]; then
		# Permitir auto-aceptar prompts exportando AUTO_ACCEPT=1
		if [ "${AUTO_ACCEPT:-0}" -eq 1 ]; then
			ans="s"
		else
			# read puede fallar con EOF si este while se ejecuta
			# dentro de una tubería; proteger con || true para
			# evitar que set -e termine el script.
			read -r -p "El servicio '$svcname' es ClusterIP. ¿Deseas hacer port-forward local a su puerto $svcport? (s/n): " ans || true
		fi
		if [[ "${ans,,}" == "s" ]]; then
			local_port="$svcport"
			echo "   -> Iniciando port-forward: localhost:${local_port} -> svc/${svcname}:${svcport} (en background)"
			nohup kubectl port-forward -n "$NAMESPACE" svc/$svcname ${local_port}:${svcport} >/dev/null 2>&1 &
			pf_pid=$!
			echo "   -> Port-forward PID: $pf_pid"
			sleep 1
		fi
	else
		echo "   -> Servicio de tipo $svctype (revisar si requiere acceso externo)"
	fi
done

echo
echo "¡Backend desplegado correctamente! ✅"

