#!/usr/bin/env bash
set -euo pipefail

TITLE="=== Desplegando Frontend integrado con Backend en Minikube ==="
echo
echo "$TITLE"
echo

# Directorio k8s del backend (ya contiene el frontend integrado)
K8S_DIR="$(dirname "${BASH_SOURCE[0]}")/../../k8s/2-Backend"
BACKEND_DIR="$(dirname "${BASH_SOURCE[0]}")/../../backend"
FRONTEND_DIR="$(dirname "${BASH_SOURCE[0]}")/../../frontend"

# Namespace por defecto (puedes pasar otro como primer argumento)
NAMESPACE="${1:-clinical-database}"

TIMEOUT_ROLLOUT=180

command_exists() { command -v "$1" >/dev/null 2>&1; }

for cmd in minikube kubectl; do
	if ! command_exists "$cmd"; then
		echo "ERROR: '$cmd' no está instalado o no está en PATH" >&2
		exit 1
	fi
done

# Helper shared: construir imagen en Minikube (preferible) o fallback a docker
build_image_minikube() {
	local image="$1"; shift
	local dockerfile="$1"; shift
	local context="$1"; shift

	echo "Preparando build de imagen: $image (dockerfile=$dockerfile, context=$context)"
	if minikube image build -h >/dev/null 2>&1; then
		echo "Usando 'minikube image build' para crear $image"
		if minikube image build -t "$image" -f "$dockerfile" "$context"; then
			echo "Imagen '$image' construida en Minikube"
			return 0
		else
			echo "WARN: fallo 'minikube image build' para $image, intentando fallback a docker" >&2
		fi
	fi

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

if [ ! -d "$K8S_DIR" ]; then
	echo "ERROR: No se encontró el directorio de manifests: $K8S_DIR" >&2
	exit 1
fi

if [ ! -d "$BACKEND_DIR" ]; then
	echo "ERROR: No se encontró el directorio del backend: $BACKEND_DIR" >&2
	exit 1
fi

if [ ! -d "$FRONTEND_DIR" ]; then
	echo "ERROR: No se encontró el directorio del frontend: $FRONTEND_DIR" >&2
	exit 1
fi

# Asegurar que el namespace exista
if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  echo "Namespace '$NAMESPACE' no existe. Creándolo..."
  kubectl create namespace "$NAMESPACE" || true
fi

echo "Construyendo imagen 'backend-api:local' con frontend integrado en Minikube..."
PROJECT_ROOT="$(dirname "${BASH_SOURCE[0]}")/../.."
build_image_minikube "backend-api:local" "$BACKEND_DIR/Dockerfile" "$PROJECT_ROOT" || {
	echo "ERROR: fallo construyendo la imagen backend-api:local con frontend" >&2
	exit 1
}
echo "Imagen 'backend-api:local' construida correctamente con frontend integrado."

# Construir la imagen del frontend nginx (si existe Dockerfile)
NGINX_DOCKERFILE="$PROJECT_ROOT/nginx/Dockerfile"
if [ -f "$NGINX_DOCKERFILE" ]; then
	echo "Construyendo imagen 'frontend-nginx:local' usando $NGINX_DOCKERFILE"
	build_image_minikube "frontend-nginx:local" "$NGINX_DOCKERFILE" "$PROJECT_ROOT" || {
		echo "WARN: fallo construyendo frontend-nginx:local; el Deployment puede dar ImagePullBackOff" >&2
	}
else
	echo "WARN: no se encontró $NGINX_DOCKERFILE; omitiendo build de frontend-nginx:local"
fi

echo "Aplicando manifests del backend+frontend en namespace '$NAMESPACE' desde $K8S_DIR..."
# Aplicar los manifests en el namespace objetivo
kubectl apply -f "$K8S_DIR" -n "$NAMESPACE" || kubectl apply -f "$K8S_DIR" || true

echo "Esperando despliegues en namespace '$NAMESPACE'..."
deploys=$(kubectl get deployments -n "$NAMESPACE" --no-headers -o custom-columns=NAME:.metadata.name 2>/dev/null || true)
if [ -z "$deploys" ]; then
	echo "No se detectaron Deployments en namespace '$NAMESPACE'. Se verificarán Pods directamente."
else
	for d in $deploys; do
		echo " - Esperando rollout del deployment: $d"
		# Forzar que el deployment use la imagen recién construida en cada contenedor
		containers=$(kubectl -n "$NAMESPACE" get deployment "$d" -o jsonpath='{.spec.template.spec.containers[*].name}' 2>/dev/null || true)
		for c in $containers; do
			if [[ "$c" == *frontend* ]] || [[ "$c" == *nginx* ]]; then
				kubectl -n "$NAMESPACE" set image deployment/$d $c=frontend-nginx:local || true
			else
				kubectl -n "$NAMESPACE" set image deployment/$d $c=backend-api:local || true
			fi
		done
		kubectl rollout restart deployment/$d -n "$NAMESPACE" || true

		if ! kubectl rollout status deployment/$d -n "$NAMESPACE" --timeout=${TIMEOUT_ROLLOUT}s; then
			echo "WARNING: Rollout failed o timeout para deployment $d — intentando con timeout mayor" >&2
			kubectl rollout status deployment/$d -n "$NAMESPACE" --timeout=300s || {
				echo "ERROR: Rollout still failed después del restart para deployment $d" >&2
				kubectl describe deployment/$d -n "$NAMESPACE" || true
				echo "Verificando pods con ImagePullBackOff o errores:"
				kubectl get pods -n "$NAMESPACE" --no-headers | grep -E "ImagePullBackOff|ErrImagePull|CrashLoopBackOff" || true
				echo "Si ves ImagePullBackOff, asegúrate de construir las imágenes locales: 'minikube image build -t frontend-nginx:local -f nginx/Dockerfile .' o ejecutar './setup.sh' para automatizarlo."
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
			echo "   -> Puedes acceder al frontend en: $url/login"
		else
			echo "   -> Servicio NodePort pero no se obtuvo URL con 'minikube service'"
		fi
	elif [ "$svctype" = "ClusterIP" ]; then
		# Permitir auto-aceptar prompts exportando AUTO_ACCEPT=1
		if [ "${AUTO_ACCEPT:-0}" -eq 1 ]; then
			ans="s"
		else
			read -r -p "El servicio '$svcname' es ClusterIP. ¿Deseas hacer port-forward local a su puerto $svcport? (s/n): " ans || true
		fi
		if [[ "${ans,,}" == "s" ]]; then
			local_port="$svcport"
			echo "   -> Iniciando port-forward: localhost:${local_port} -> svc/${svcname}:${svcport} (en background)"
			nohup kubectl port-forward -n "$NAMESPACE" svc/$svcname ${local_port}:${svcport} >/dev/null 2>&1 &
			pf_pid=$!
			echo "   -> Port-forward PID: $pf_pid"
			echo "   -> Puedes acceder al frontend en: http://localhost:${local_port}/login"
			sleep 1
		fi
	else
		echo "   -> Servicio de tipo $svctype (revisar si requiere acceso externo)"
	fi
done

echo
echo "¡Frontend integrado con Backend desplegado correctamente! ✅"
echo
echo "Acceso al sistema:"
echo "  - Login: /login"
echo "  - Dashboards: /admin, /medic, /patient (según rol del usuario)"
echo "  - API: /api/* (endpoints REST)"
echo


