#!/bin/bash

# ===============================================
# Sistema FHIR Distribuido - Script Simplificado
# Mantiene sólo el banner y el paso 1 (ejecutar deploy local)
# ===============================================

set -e

# Colores para output (permiten que el banner mantenga su formato)
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

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

    echo "Paso 1: Ejecutando script de despliegue local (scripts/dev/1-DeployCitusSql.sh)"
    if [ -x "./scripts/dev/1-DeployCitusSql.sh" ]; then
        ./scripts/dev/1-DeployCitusSql.sh
    else
        # intentar ejecutar con bash si no es ejecutable
        bash ./scripts/dev/1-DeployCitusSql.sh
    fi

    echo "Esperando 5 segundos después del paso 1..."
    sleep 5

    echo "Paso 1 completado (temporal). El script está reducido a este único paso por ahora."
}

main "$@"