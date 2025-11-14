#!/bin/bash

# ===============================================
# Sistema FHIR Distribuido - Script Simplificado
# Mantiene sólo el banner y el paso 1 (ejecutar deploy local)
# ===============================================

set -euo pipefail

# Ruta raíz del repositorio (asegura que las llamadas a scripts funcionen desde cualquier CWD)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colores para output (permiten que el banner mantenga su formato)
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'
GREEN='\033[0;32m'

# Banner del sistema (se mantiene tal cual)
show_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
    ██╗   ██╗ █████╗      ██╗███████╗
    ██║   ██║██╔══██╗     ██║██╔════╝
    ██║   ██║███████║     ██║███████╗
    ██║   ██║██╔══██║██   ██║╚════██║
    ╚██████╔╝██║  ██║╚█████╔╝███████║
     ╚═════╝ ╚═╝  ╚═╝ ╚════╝ ╚══════╝
     Sistema Distribuido con PostgreSQL + Citus
EOF
    echo -e "${NC}"
    echo -e "${PURPLE}Autores: Carlos Cochero, Andrés Palacio${NC}"
    echo -e "${PURPLE}Versión: 4.0 | FastAPI Refactorizado + PostgreSQL/Citus${NC}"
    echo ""
}

main() {
    show_banner

    echo "Paso 0: Iniciando Minikube (${REPO_ROOT}/scripts/dev/0-StartMinikube.sh)"
    if [ -x "${REPO_ROOT}/scripts/dev/0-StartMinikube.sh" ]; then
        "${REPO_ROOT}/scripts/dev/0-StartMinikube.sh"
    else
        bash "${REPO_ROOT}/scripts/dev/0-StartMinikube.sh"
    fi

    echo "Esperando 5 segundos después del paso 0..."
    sleep 5

    echo "Paso 1: Ejecutando despliegue Citus (${REPO_ROOT}/scripts/dev/1-DeployCitusSql.sh)"
    if [ -x "${REPO_ROOT}/scripts/dev/1-DeployCitusSql.sh" ]; then
        "${REPO_ROOT}/scripts/dev/1-DeployCitusSql.sh"
    else
        bash "${REPO_ROOT}/scripts/dev/1-DeployCitusSql.sh"
    fi

    echo "Esperando 5 segundos después del paso 1..."
    sleep 5

    echo -e "${GREEN}Paso 1 completado. Procediendo al paso 2: despliegue del backend${NC}"
    echo "Paso 2: Ejecutando despliegue del backend (${REPO_ROOT}/scripts/dev/2-DeployBackend.sh)"
    if [ -x "${REPO_ROOT}/scripts/dev/2-DeployBackend.sh" ]; then
        "${REPO_ROOT}/scripts/dev/2-DeployBackend.sh" clinical-database
    else
        bash "${REPO_ROOT}/scripts/dev/2-DeployBackend.sh" clinical-database
    fi

    echo "Esperando 5 segundos después del paso 2..."
    sleep 5

    echo -e "${GREEN}Despliegue completo. Puedes usar './scripts/dev/2-DeployBackend.sh' para verificar servicios o limpiar recursos.${NC}"
}

# Invocar main con los argumentos del script
main "$@"