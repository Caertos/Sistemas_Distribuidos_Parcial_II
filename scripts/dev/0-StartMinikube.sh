#!/usr/bin/env bash
set -euo pipefail

TITLE="=== Iniciando Minikube ==="
echo
echo "$TITLE"
echo

# Valores por defecto: memoria en MiB y CPUs
MEMORY="${1:-4096}"
CPUS="${2:-2}"

echo "Usando: MEMORY=${MEMORY} MiB, CPUS=${CPUS}"

command_exists() {
	command -v "$1" >/dev/null 2>&1
}

if ! command_exists minikube; then
	echo "ERROR: 'minikube' no está instalado o no está en PATH" >&2
	exit 1
fi

if ! command_exists kubectl; then
	echo "ERROR: 'kubectl' no está instalado o no está en PATH" >&2
	exit 1
fi

echo "Comprobando si existe una instancia de minikube..."
if minikube status >/dev/null 2>&1; then
	echo "Minikube detectado: deteniendo para reiniciar con recursos solicitados..."
	minikube stop || true
fi

echo "Iniciando minikube con --memory=${MEMORY} --cpus=${CPUS}..."
if ! minikube start --memory="${MEMORY}" --cpus="${CPUS}"; then
	echo "ERROR: Falló minikube start" >&2
	exit 1
fi

echo "Esperando que el nodo Kubernetes esté Ready (timeout 120s)..."
timeout=120
interval=5
elapsed=0
while [ "$elapsed" -lt "$timeout" ]; do
	if kubectl get nodes --no-headers 2>/dev/null | awk '{print $2}' | grep -q "Ready"; then
		echo "Nodo Ready"
		break
	fi
	sleep "$interval"
	elapsed=$((elapsed + interval))
done

if [ "$elapsed" -ge "$timeout" ]; then
	echo "ERROR: Timeout esperando que el nodo esté listo" >&2
	kubectl get nodes || true
	exit 1
fi

echo "Esperando que los pods en 'kube-system' estén listos (timeout 180s)..."
ks_timeout=180
ks_interval=5
ks_elapsed=0
while [ "$ks_elapsed" -lt "$ks_timeout" ]; do
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
	done < <(kubectl get pods -n kube-system --no-headers 2>/dev/null || true)

	if [ "$problems" -eq 0 ]; then
		echo "Todos los pods de 'kube-system' parecen listos"
		break
	fi

	echo "Quedan ${problems} pods problemáticos en 'kube-system'; reintentando en ${ks_interval}s..."
	sleep "$ks_interval"
	ks_elapsed=$((ks_elapsed + ks_interval))
done

if [ "$ks_elapsed" -ge "$ks_timeout" ]; then
	echo "ERROR: Timeout esperando pods listos en 'kube-system'" >&2
	kubectl get pods -n kube-system || true
	exit 1
fi

echo
echo "--------------------------------------------------"
echo "TODO OK: Minikube arrancado y comprobaciones básicas OK"
echo "--------------------------------------------------"
echo

echo "Mostrando resumen: nodos y addons activos"
kubectl get nodes
minikube addons list || true

echo
echo "¡Todo salió bien! ✅"

