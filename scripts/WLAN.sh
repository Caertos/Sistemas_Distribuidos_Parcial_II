#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST_REL="k8s/2-Backend/frontend-nginx-deployment.yaml"
MANIFEST_PATH="$REPO_ROOT/$MANIFEST_REL"

echo "== Publicar WebApp en la LAN =="

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl no está en PATH. Instala/configura kubectl e inténtalo de nuevo." >&2
  exit 1
fi

if [ ! -f "$MANIFEST_PATH" ]; then
  echo "Manifiesto no encontrado: $MANIFEST_PATH" >&2
  exit 1
fi

echo "Aplicando manifiesto NodePort: $MANIFEST_REL"
kubectl apply -f "$MANIFEST_PATH"

echo "Abriendo puerto en el firewall 30080/tcp (requiere sudo)"
sudo ufw allow 30080/tcp || true
sudo ufw reload || true

MINIKUBE_IP="$(minikube -p minikube ip 2>/dev/null || true)"
if [ -z "$MINIKUBE_IP" ]; then
  echo "Atención: no se pudo detectar la IP de Minikube. Puede que necesite establecer MINIKUBE_IP manualmente." >&2
  exit 1
fi

echo "IP de Minikube detectada: $MINIKUBE_IP"

echo "Comprobando que socat esté instalado (para reenvío TCP)"
if ! command -v socat >/dev/null 2>&1; then
  echo "Instalando socat (requiere sudo)"
  sudo apt-get update
  sudo apt-get install -y socat
fi

UNIT_NAME="socat-frontend.service"
UNIT_PATH="/etc/systemd/system/$UNIT_NAME"

echo "Creando unidad systemd en $UNIT_PATH"
sudo tee "$UNIT_PATH" > /dev/null <<EOF
[Unit]
Description=Socat forward for frontend NodePort
After=network.target

[Service]
Type=simple
Restart=always
RestartSec=5
ExecStart=/usr/bin/socat TCP-LISTEN:30080,fork,reuseaddr TCP:${MINIKUBE_IP}:30080
User=root

[Install]
WantedBy=multi-user.target
EOF

echo "Recargando systemd y habilitando el servicio"
sudo systemctl daemon-reload
sudo systemctl enable --now "$UNIT_NAME"

echo "Estado del servicio:"
sudo systemctl status --no-pager "$UNIT_NAME" || true

echo "Publicación completada. La aplicación debería ser accesible en http://<ip-del-host>:30080/admission/ desde dispositivos en la LAN."
echo "Para quitar el servicio de reenvío: sudo systemctl disable --now $UNIT_NAME; sudo rm -f $UNIT_PATH; sudo systemctl daemon-reload"
