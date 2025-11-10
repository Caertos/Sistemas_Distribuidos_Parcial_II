#!/bin/bash

# ===============================================
# Sistema FHIR Distribuido - Script Principal
# Autores: Carlos Cochero, Andrés Palacio
# Versión: 4.0 - Organizado y Refactorizado
# ===============================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Banner del sistema
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

# Función de ayuda
show_help() {
    echo -e "${BOLD}${CYAN}SISTEMA FHIR DISTRIBUIDO - COMANDOS DISPONIBLES${NC}"
    echo ""
    echo -e "${BOLD}${GREEN}📦 INSTALACIÓN Y DESPLIEGUE:${NC}"
    echo -e "  ${CYAN}./setup.sh compose${NC}     - Instalar con Docker Compose (Recomendado)"
    echo -e "  ${CYAN}./setup.sh minikube${NC}    - Instalar con Kubernetes/Minikube"
    echo ""
    echo -e "${BOLD}${YELLOW}🧪 PRUEBAS Y VERIFICACIÓN:${NC}"
    echo -e "  ${CYAN}./setup.sh test${NC}        - Ejecutar pruebas del sistema"
    echo -e "  ${CYAN}./setup.sh verify${NC}      - Verificar instalación de Kubernetes"
    echo ""
    echo -e "${BOLD}${RED}🧹 LIMPIEZA Y MANTENIMIENTO:${NC}"
    echo -e "  ${CYAN}./setup.sh cleanup${NC}     - Limpiar instalación completa"
    echo ""
    echo -e "${BOLD}${BLUE}⚙️ DESARROLLO:${NC}"
    echo -e "  ${CYAN}./setup.sh dev-install${NC} - Instalar entorno de desarrollo FastAPI"
    echo -e "  ${CYAN}./setup.sh dev-start${NC}   - Iniciar servidor de desarrollo"
    echo ""
    echo -e "${BOLD}${GREEN}🗃️ BASE DE DATOS:${NC}"
    echo -e "  ${CYAN}./llenar.sh${NC}           - Poblar base de datos con datos de ejemplo"
    echo ""
    echo -e "${BOLD}${PURPLE}ℹ️ INFORMACIÓN:${NC}"
    echo -e "  ${CYAN}./setup.sh help${NC}        - Mostrar esta ayuda"
    echo -e "  ${CYAN}./setup.sh status${NC}      - Ver estado del sistema"
    echo ""
    echo -e "${BOLD}${GREEN}🚀 INICIO RÁPIDO:${NC}"
    echo -e "  ${YELLOW}Para desarrollo local:${NC}    ./setup.sh compose"
    echo -e "  ${YELLOW}Para producción:${NC}         ./setup.sh minikube"
}

# Función para preguntar sobre poblado de datos
ask_populate_database() {
    echo ""
    echo -e "${BOLD}${YELLOW}🗃️ POBLADO DE BASE DE DATOS${NC}"
    echo "=============================================="
    echo -e "${CYAN}El sistema puede poblarse automáticamente con datos de ejemplo usando ${BOLD}llenar.sh${NC}${CYAN}:${NC}"
    echo "• 2 administradores + 1 auditor"
    echo "• 5 médicos especialistas (cardiología, neurología, pediatría, oncología, dermatología)"
    echo "• 10 pacientes con historias clínicas completas"
    echo "• Condiciones médicas, medicamentos y encuentros médicos"
    echo ""
    echo -e "${GREEN}Esto facilita las pruebas y demostración del sistema.${NC}"
    echo -e "${YELLOW}⚠️ NOTA: El archivo 03-sample-data.sql está DEPRECADO, usar llenar.sh${NC}"
    echo ""
    
    while true; do
        echo -n "¿Deseas poblar la base de datos con datos de ejemplo? (s/N): "
        read -r response
        case $response in
            [Ss]* ) 
                echo -e "${GREEN}✅ Se poblará la base de datos después de la instalación${NC}"
                return 0
                ;;
            [Nn]* | "" ) 
                echo -e "${YELLOW}⚠️ La base de datos quedará vacía (solo usuarios básicos: admin/secret, medico/secret, paciente/secret, auditor/secret)${NC}"
                return 1
                ;;
            * ) 
                echo -e "${RED}Por favor responde 's' para sí o 'n' para no.${NC}"
                ;;
        esac
    done
}

# Función para ejecutar el poblado de datos
populate_database() {
    echo ""
    echo -e "${GREEN}🗃️ Poblando base de datos con datos de ejemplo...${NC}"
    
    # Esperar a que el sistema esté listo
    echo -e "${YELLOW}⏳ Esperando que el sistema esté completamente inicializado...${NC}"
    sleep 10
    
    # Ejecutar script de poblado
    if [ -f "./llenar.sh" ]; then
        ./llenar.sh --auto
        echo -e "${GREEN}✅ Base de datos poblada exitosamente${NC}"
    else
        echo -e "${RED}❌ Error: No se encontró el script llenar.sh${NC}"
        echo -e "${YELLOW}La base de datos solo tendrá los usuarios básicos${NC}"
    fi
}

# Verificar estado del sistema
show_status() {
    echo -e "${BOLD}${CYAN}ESTADO DEL SISTEMA FHIR${NC}"
    echo ""
    
    # Verificar Docker Compose
    if docker compose ps &>/dev/null; then
        echo -e "${GREEN}✅ Docker Compose:${NC} Activo"
        docker compose ps
    else
        echo -e "${RED}❌ Docker Compose:${NC} No activo"
    fi
    
    echo ""
    
    # Verificar Kubernetes
    if kubectl get pods &>/dev/null; then
        echo -e "${GREEN}✅ Kubernetes:${NC} Conectado"
        kubectl get pods
    else
        echo -e "${RED}❌ Kubernetes:${NC} No conectado"
    fi
    
    echo ""
    
    # Verificar conectividad
    if curl -s http://localhost:8000/health | grep -q "healthy" 2>/dev/null; then
        echo -e "${GREEN}✅ FastAPI:${NC} Respondiendo en http://localhost:8000"
    else
        echo -e "${RED}❌ FastAPI:${NC} No responde en http://localhost:8000"
    fi
}

# Función principal
main() {
    show_banner
    
    case "${1:-help}" in
        "compose")
            echo -e "${GREEN}🐳 Ejecutando instalación con Docker Compose...${NC}"
            
            # Preguntar sobre poblado de datos
            if ask_populate_database; then
                POPULATE_DB=true
            else
                POPULATE_DB=false
            fi
            
            # Ejecutar instalación
            ./scripts/setup_system_compose.sh
            
            # Poblar base de datos si se solicitó
            if [ "$POPULATE_DB" = true ]; then
                populate_database
            fi
            ;;
        "minikube")
            echo -e "${GREEN}☸️ Ejecutando instalación con Kubernetes/Minikube...${NC}"
            
            # Preguntar sobre poblado de datos
            if ask_populate_database; then
                POPULATE_DB=true
            else
                POPULATE_DB=false
            fi
            
            # Ejecutar instalación
            ./scripts/setup_system_minikube.sh
            
            # Poblar base de datos si se solicitó
            if [ "$POPULATE_DB" = true ]; then
                populate_database
            fi
            ;;
        "test")
            echo -e "${GREEN}🧪 Ejecutando pruebas del sistema...${NC}"
            ./scripts/run_tests.sh
            ;;
        "verify")
            echo -e "${GREEN}🔍 Verificando instalación de Kubernetes...${NC}"
            ./scripts/verify_lab.sh
            ;;
        "cleanup")
            echo -e "${GREEN}🧹 Limpiando sistema...${NC}"
            ./scripts/cleanup.sh
            ;;
        "dev-install")
            echo -e "${GREEN}⚙️ Instalando entorno de desarrollo...${NC}"
            ./scripts/dev/install.sh
            ;;
        "dev-start")
            echo -e "${GREEN}🚀 Iniciando servidor de desarrollo...${NC}"
            ./scripts/dev/start_server.sh
            ;;
        "status")
            show_status
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            if [ -n "$1" ]; then
                echo -e "${RED}❌ Comando desconocido: $1${NC}"
                echo ""
            fi
            show_help
            ;;
    esac
}

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.yml" ] || [ ! -d "scripts" ]; then
    echo -e "${RED}❌ Error: Ejecuta este script desde el directorio raíz del proyecto${NC}"
    echo -e "${YELLOW}Directorio actual: $(pwd)${NC}"
    exit 1
fi

# Ejecutar función principal
main "$@"