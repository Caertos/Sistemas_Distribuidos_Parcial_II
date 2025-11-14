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
# Aplicar los manifests en el namespace objetivo; si los manifests contienen namespace propio, kubectl reportará y seguirá
kubectl apply -f "$K8S_DIR" -n "$NAMESPACE" || kubectl apply -f "$K8S_DIR" || true

echo "Esperando despliegues en namespace '$NAMESPACE'..."
deploys=$(kubectl get deployments -n "$NAMESPACE" --no-headers -o custom-columns=NAME:.metadata.name 2>/dev/null || true)
if [ -z "$deploys" ]; then
	echo "No se detectaron Deployments en namespace '$NAMESPACE'. Se verificarán Pods directamente."
else
	for d in $deploys; do
		echo " - Esperando rollout del deployment: $d"
		kubectl rollout status deployment/$d -n "$NAMESPACE" --timeout=${TIMEOUT_ROLLOUT}s || {
			echo "ERROR: Rollout failed o timeout para deployment $d" >&2
			kubectl describe deployment/$d -n "$NAMESPACE" || true
			kubectl get pods -n "$NAMESPACE" || true
			exit 1
		}
	done
fi

echo "Verificando pods en namespace '$NAMESPACE'..."
unready=0
while IFS= read -r line; do
	name=$(echo "$line" | awk '{print $1}')
	ready_field=$(echo "$line" | awk '{print $2}')
	status_field=$(echo "$line" | awk '{print $3}')
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
		read -r -p "El servicio '$svcname' es ClusterIP. ¿Deseas hacer port-forward local a su puerto $svcport? (s/n): " ans
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

