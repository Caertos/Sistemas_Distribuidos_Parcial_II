#!/bin/bash

# ===============================================
# Sistema FHIR Distribuido - Instalador Principal
# Autores: Carlos Cochero, Andrés Palacio
# Versión: 3.0
# ===============================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Función para logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

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
    echo -e "${PURPLE}Versión: 3.0 | FastAPI + Flask + PostgreSQL/Citus${NC}"
    echo ""
}

# Verificar prerrequisitos
check_prerequisites() {
    log "Verificando prerrequisitos..."
    
    # Docker
    if ! command -v docker &> /dev/null; then
        error "Docker no está instalado. Por favor instale Docker primero."
    fi
    
    # Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose no está instalado. Por favor instale Docker Compose primero."
    fi
    
    # Git
    if ! command -v git &> /dev/null; then
        warning "Git no está instalado. Algunas funciones pueden no funcionar correctamente."
    fi
    
    log "✅ Prerrequisitos verificados correctamente"
}

# Docker Compose Setup
setup_docker_compose() {
    log "🐳 Configurando sistema con Docker Compose..."
    
    # Limpiar instalaciones previas
    log "Limpiando instalaciones previas..."
    docker compose down -v 2>/dev/null || true
    docker system prune -f
    
    # Construir imágenes
    log "Construyendo imágenes Docker..."
    docker compose build --no-cache
    
    # Iniciar servicios
    log "Iniciando servicios..."
    docker compose up -d
    
    # Esperar que los servicios estén listos
    log "Esperando que los servicios estén listos..."
    sleep 30
    
    # Registrar workers en Citus
    log "Configurando cluster Citus..."
    ./register_citus.sh || warning "Error al registrar workers - continuando..."
    
    # Verificar servicios
    log "Verificando servicios..."
    docker compose ps
    
    echo -e "\n${GREEN}✅ Sistema Docker Compose configurado correctamente!${NC}"
    echo -e "${BLUE}🌐 Frontend: http://localhost${NC}"
    echo -e "${BLUE}📡 API: http://localhost:8000${NC}"
    echo -e "${BLUE}📚 Docs: http://localhost:8000/docs${NC}"
}

# Minikube Setup
setup_minikube() {
    log "☸️  Configurando sistema con Minikube..."
    
    # Verificar minikube
    if ! command -v minikube &> /dev/null; then
        error "Minikube no está instalado. Por favor instale Minikube primero."
    fi
    
    if ! command -v kubectl &> /dev/null; then
        error "kubectl no está instalado. Por favor instale kubectl primero."
    fi
    
    # Ejecutar script de Minikube
    cd k8s
    ./setup_minikube.sh
    cd ..
    
    echo -e "\n${GREEN}✅ Sistema Minikube configurado correctamente!${NC}"
    echo -e "${BLUE}Use 'kubectl get pods' para ver el estado${NC}"
}

# Mostrar información de usuarios
show_users() {
    echo -e "\n${YELLOW}👥 USUARIOS DE PRUEBA:${NC}"
    echo -e "${BLUE}Usuario: admin     | Password: admin123     | Rol: Administrador${NC}"
    echo -e "${BLUE}Usuario: medico    | Password: medico123    | Rol: Practitioner${NC}"
    echo -e "${BLUE}Usuario: paciente  | Password: paciente123  | Rol: Patient${NC}"
    echo -e "${BLUE}Usuario: auditor   | Password: auditor123   | Rol: Auditor${NC}"
}

# Función de ayuda
show_help() {
    echo -e "${BLUE}USO:${NC}"
    echo "  ./setup_all.sh                    - Modo interactivo"
    echo "  ./setup_all.sh compose            - Docker Compose automático"
    echo "  ./setup_all.sh minikube           - Minikube automático"
    echo "  ./setup_all.sh help               - Mostrar esta ayuda"
    echo ""
    echo -e "${BLUE}COMANDOS ÚTILES POST-INSTALACIÓN:${NC}"
    echo "  docker compose ps                 - Ver estado de contenedores"
    echo "  docker compose logs -f            - Ver logs en tiempo real"
    echo "  ./cleanup.sh                      - Limpiar instalación"
    echo "  ./run_tests.sh                    - Ejecutar pruebas"
}

# Menú interactivo
interactive_menu() {
    echo -e "${YELLOW}🚀 OPCIONES DE INSTALACIÓN:${NC}"
    echo "1) Docker Compose (Recomendado)"
    echo "2) Minikube (Kubernetes)"
    echo "3) Mostrar ayuda"
    echo "4) Salir"
    echo ""
    read -p "Seleccione una opción [1-4]: " choice
    
    case $choice in
        1)
            setup_docker_compose
            show_users
            ;;
        2)
            setup_minikube
            ;;
        3)
            show_help
            ;;
        4)
            log "👋 ¡Hasta luego!"
            exit 0
            ;;
        *)
            error "Opción inválida. Use 1, 2, 3 o 4."
            ;;
    esac
}

# Función principal
main() {
    show_banner
    check_prerequisites
    
    case "${1:-}" in
        "compose")
            setup_docker_compose
            show_users
            ;;
        "minikube")
            setup_minikube
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        "")
            interactive_menu
            ;;
        *)
            error "Opción desconocida: $1. Use 'help' para ver opciones disponibles."
            ;;
    esac
}

# Manejar señales
trap 'echo -e "\n${RED}Instalación interrumpida por el usuario${NC}"; exit 1' INT TERM

# Ejecutar función principal
main "$@"