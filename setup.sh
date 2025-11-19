#!/bin/bash

# ===============================================
# Sistema FHIR Distribuido - Script Simplificado
# Mantiene sólo el banner y el paso 1 (ejecutar deploy local)
# ===============================================

set -euo pipefail

# Ruta raíz del repositorio (asegura que las llamadas a scripts funcionen desde cualquier CWD)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Archivo de reporte de instalación (se crea con timestamp)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOGFILE="$REPO_ROOT/setup_report_$TIMESTAMP.log"

# Logging helpers: escribe a stdout y al logfile
log() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") [INFO] $*" | tee -a "$LOGFILE"
}

log_err() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") [ERROR] $*" | tee -a "$LOGFILE" >&2
}

# Ejecuta un paso (label) y registra éxito/fallo en el logfile.
# Uso: run_step "Descripción" comando [args...]
run_step() {
    label="$1"; shift
    log "INICIO: $label"
    set +e
    "$@"
    status=$?
    set -e
    if [ $status -eq 0 ]; then
        log "OK: $label"
    else
        log_err "FALLO: $label (exit=$status)"
        log_err "Se aborta la instalación. Ver $LOGFILE para más detalles."
        exit $status
    fi
}

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

    log "Paso 0: Iniciando Minikube (${REPO_ROOT}/scripts/dev/0-StartMinikube.sh)"
    if [ -x "${REPO_ROOT}/scripts/dev/0-StartMinikube.sh" ]; then
        run_step "Iniciar Minikube" bash "${REPO_ROOT}/scripts/dev/0-StartMinikube.sh"
    else
        run_step "Iniciar Minikube" bash "${REPO_ROOT}/scripts/dev/0-StartMinikube.sh"
    fi

    echo "Esperando 5 segundos después del paso 0..."
    sleep 5

    echo "Paso 1: Ejecutando despliegue Citus (${REPO_ROOT}/scripts/dev/1-DeployCitusSql.sh)"
    if [ -x "${REPO_ROOT}/scripts/dev/1-DeployCitusSql.sh" ]; then
           run_step "Deploy Citus" bash "${REPO_ROOT}/scripts/dev/1-DeployCitusSql.sh"
    else
        bash "${REPO_ROOT}/scripts/dev/1-DeployCitusSql.sh"
    fi

    echo "Esperando 5 segundos después del paso 1..."
    sleep 5

    echo -e "${GREEN}Paso 1 completado. Procediendo al paso 2: despliegue del backend${NC}"
    echo "Paso 2: Ejecutando despliegue del backend (${REPO_ROOT}/scripts/dev/2-DeployBackend.sh)"
    if [ -x "${REPO_ROOT}/scripts/dev/2-DeployBackend.sh" ]; then
           run_step "Deploy Backend" bash "${REPO_ROOT}/scripts/dev/2-DeployBackend.sh" clinical-database
    else
        bash "${REPO_ROOT}/scripts/dev/2-DeployBackend.sh" clinical-database
    fi

    echo "Esperando 5 segundos después del paso 2..."
    sleep 5

    echo -e "${GREEN}Paso 2 completado. Procediendo al paso 3: despliegue del frontend${NC}"
    echo "Paso 3: Ejecutando despliegue del frontend (${REPO_ROOT}/scripts/dev/3-DeployFrontend.sh)"
    if [ -x "${REPO_ROOT}/scripts/dev/3-DeployFrontend.sh" ]; then
           run_step "Deploy Frontend" bash "${REPO_ROOT}/scripts/dev/3-DeployFrontend.sh" clinical-database
    else
        bash "${REPO_ROOT}/scripts/dev/3-DeployFrontend.sh" clinical-database
    fi

    echo "Esperando 5 segundos después del paso 3..."
    sleep 5

    echo -e "${GREEN}Despliegue completo. El sistema está listo.${NC}"
    echo -e "${GREEN}Puedes acceder al frontend en la URL del servicio NodePort o via port-forward.${NC}"
    echo -e "${GREEN}Usa './scripts/dev/clean_env.sh' para limpiar recursos si es necesario.${NC}"
}

# Invocar main con los argumentos del script
main "$@"