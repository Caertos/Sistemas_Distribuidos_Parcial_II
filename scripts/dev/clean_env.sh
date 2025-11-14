#!/usr/bin/env bash
# scripts/dev/clean_env.sh
# Script interactivo para limpiar Minikube y Docker en el host.
# Uso: ./scripts/dev/clean_env.sh [-y|--yes] [--dry-run]
set -euo pipefail
IFS=$'\\n\\t'

DRY_RUN=false
ASSUME_YES=false

print_help(){
  cat <<'HELP'
Uso: clean_env.sh [opciones]

Opciones:
  -y, --yes       Ejecutar sin interacción y aceptar todas las acciones destructivas
  --dry-run       Mostrar lo que se haría sin ejecutar comandos destructivos
  -h, --help      Mostrar esta ayuda y salir

Este script mostrará un menú interactivo para seleccionar qué recursos eliminar:
  - Clúster Minikube y ~/.minikube
  - Contexto 'minikube' en kubeconfig
  - Contenedores Docker
  - Imágenes Docker específicas (selección interactiva)
  - Caché del builder de Docker, system prune, redes y volúmenes

Esto es destructivo. Usa --dry-run para previsualizar las acciones.
HELP
}

confirm_or_exit(){
  local prompt="$1"
  if [ "$ASSUME_YES" = true ]; then
    echo "[SKIP PROMPT] $prompt -> yes"
    return 0
  fi
  read -r -p "$prompt [y/N]: " answer
  case "$answer" in
    [yY]|[yY][eE][sS]) return 0 ;;
    *) echo "Aborted."; exit 1 ;;
  esac
}

run_cmd(){
  if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] $*"
  else
    echo "+ $*"
    eval "$@"
  fi
}

choose_yes_no(){
  # $1 prompt
  local prompt="$1"
  if [ "$ASSUME_YES" = true ]; then
    echo "[SKIP PROMPT] $prompt -> yes"
    return 0
  fi
  while true; do
    read -r -p "$prompt [y/N]: " yn
      case "$yn" in
        [Yy]* ) return 0;;
        [Nn]*|"") return 1;;
        * ) echo "Responde sí o no.";;
      esac
  done
}

# Mostrar una lista de imágenes Docker y permitir al usuario seleccionar cuáles borrar
select_images_to_delete(){
  # imprime las imágenes seleccionadas (una por línea) a stdout
  if ! command -v docker >/dev/null 2>&1; then
    return 0
  fi
  echo
  echo "Imágenes locales (lista corta):"
  docker images --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' | nl -w2 -s'. '
  echo
  echo "Opciones:"
  echo "  - Introduce índices separados por comas (p.ej. 1,3,5) para borrar esas imágenes"
  echo "  - Escribe 'all' para borrar todas las imágenes listadas"
  echo "  - Deja vacío para omitir eliminación de imágenes"
  read -r -p "Qué imágenes borrar?: " choice

  if [ -z "$choice" ]; then
    return 0
  fi
  if [ "$choice" = "all" ]; then
    docker images --format '{{.Repository}}:{{.Tag}}' || true
    return 0
  fi

  # parse indices
  IFS=',' read -ra idxs <<< "$choice"
  selected=()
  mapfile -t lines < <(docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' )
  for idx in "${idxs[@]}"; do
    idx_trim=$(echo "$idx" | tr -d '[:space:]')
    if [[ "$idx_trim" =~ ^[0-9]+$ ]]; then
      line=${lines[$((idx_trim-1))]:-}
      if [ -n "$line" ]; then
        repo_tag=$(echo "$line" | awk '{print $1}')
        selected+=("$repo_tag")
      fi
    fi
  done

  for img in "${selected[@]}"; do
    echo "$img"
  done
}

# Parsear argumentos
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    -y|--yes) ASSUME_YES=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help) print_help; exit 0 ;;
    *) echo "Opción desconocida: $1"; print_help; exit 2 ;;
  esac
done

cat <<EOF
=== Script de limpieza (interactivo) ===
DRY_RUN=$DRY_RUN
ASSUME_YES=$ASSUME_YES
Este script te permitirá elegir qué categorías limpiar.
EOF

confirm_or_exit "¿Quieres continuar con la comprobación/interacción para limpiar recursos?"

# 1) Minikube
if command -v minikube >/dev/null 2>&1; then
  if choose_yes_no "¿Eliminar Minikube (stop + delete) y borrar ~/.minikube?"; then
    run_cmd "minikube stop || true"
    run_cmd "minikube delete || true"
    run_cmd "rm -rf \"$HOME/.minikube\" || true"
  else
    echo "Omitido: Minikube"
  fi
else
  echo "Minikube no encontrado, saltando..."
fi

# 2) Limpieza de contexto kubectl
if command -v kubectl >/dev/null 2>&1; then
  if choose_yes_no "¿Eliminar contexto/cluster/usuario 'minikube' de kubeconfig (kubectl)?"; then
    run_cmd "kubectl config delete-context minikube || true"
    run_cmd "kubectl config delete-cluster minikube || true"
    run_cmd "kubectl config unset users.minikube || true"
  else
    echo "Omitido: kubeconfig"
  fi
else
  echo "kubectl no disponible, saltando limpieza de kubeconfig."
fi

# 3) Detener y eliminar contenedores Docker
if command -v docker >/dev/null 2>&1; then
  if choose_yes_no "¿Detener y eliminar todos los contenedores Docker?"; then
    if [ "$DRY_RUN" = true ]; then
      docker ps -a --format 'table {{.ID}}\\t{{.Image}}\\t{{.Status}}' || true
    else
      docker ps -q | xargs -r docker stop || true
      docker ps -aq | xargs -r docker rm -f || true
    fi
  else
    echo "Omitido: detener/eliminar contenedores"
  fi

  # 4) Eliminación selectiva de imágenes Docker
  if choose_yes_no "¿Eliminar imágenes Docker específicas (interactivo)?"; then
    imgs_to_delete=$(select_images_to_delete)
    if [ -n "${imgs_to_delete:-}" ]; then
      while IFS= read -r img; do
        if [ -n "$img" ]; then
          run_cmd "docker rmi $img -f || true"
        fi
      done <<< "$imgs_to_delete"
    else
      echo "No se eliminarán imágenes (selección vacía)."
    fi
  else
    echo "Omitido: eliminación de imágenes"
  fi

  # 5) Limpiar caché del builder y sistema
  if choose_yes_no "¿Ejecutar docker builder prune y docker system prune --volumes -f?"; then
    run_cmd "docker builder prune -af || true"
    run_cmd "docker system prune -a --volumes -f || true"
  else
    echo "Omitido: system prune"
  fi

  # redes y volúmenes
  if choose_yes_no "¿Prune de redes y volúmenes Docker (network prune & volume prune)?"; then
    run_cmd "docker network prune -f || true"
    run_cmd "docker volume prune -f || true"
  else
    echo "Omitido: prune de redes/volúmenes"
  fi
else
  echo "Docker no disponible. Saltando pasos de Docker."
fi

# Verificación final
echo "--> Estado final (resumen):"
if command -v docker >/dev/null 2>&1; then
  if [ "$DRY_RUN" = true ]; then
    docker ps -a --format 'table {{.ID}}\\t{{.Image}}\\t{{.Status}}' || true
    docker images --format 'table {{.Repository}}\\t{{.Tag}}\\t{{.ID}}\\t{{.Size}}' || true
  else
    echo "Contenedores (docker ps -a):"
    docker ps -a || true
    echo "Imágenes (docker images):"
    docker images || true
  fi
else
  echo "Docker no disponible para verificación final."
fi

echo "Limpieza interactiva completada."
echo "Limpieza completada. Si necesitas conservar alguna imagen en futuras ejecuciones, no uses --yes con este script o modifica la lista de imágenes a eliminar."
