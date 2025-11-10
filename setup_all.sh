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

# Esperar a que los servicios de Citus estén listos
wait_for_citus_services() {
    log "Esperando a que los servicios de Citus estén listos..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log "Intento $attempt/$max_attempts - Verificando servicios Citus..."
        
        # Verificar que el coordinator esté listo
        if docker compose exec citus-coordinator pg_isready -U postgres -d hce >/dev/null 2>&1; then
            log "✅ Coordinator está listo"
            
            # Verificar workers
            if docker compose exec citus-worker1 pg_isready -U postgres >/dev/null 2>&1 && \
               docker compose exec citus-worker2 pg_isready -U postgres >/dev/null 2>&1; then
                log "✅ Workers están listos"
                return 0
            fi
        fi
        
        log "Servicios aún no están listos, esperando 5 segundos..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    warning "Los servicios de Citus tardaron demasiado en estar listos"
    return 1
}

# Configurar cluster Citus correctamente
configure_citus_cluster() {
    log "Configurando cluster Citus con base de datos 'hce'..."
    
    # Configurar hostname del coordinator
    log "Estableciendo hostname del coordinator..."
    if docker compose exec citus-coordinator psql -U postgres -d hce -c "SELECT citus_set_coordinator_host('citus-coordinator');" >/dev/null 2>&1; then
        log "✅ Hostname del coordinator establecido"
    else
        warning "No se pudo establecer el hostname del coordinator"
    fi
    
    # Crear base de datos hce en workers si no existe
    log "Asegurando que la base de datos 'hce' existe en workers..."
    docker compose exec citus-worker1 psql -U postgres -c "SELECT 1 FROM pg_database WHERE datname='hce';" | grep -q 1 || \
        docker compose exec citus-worker1 psql -U postgres -c "CREATE DATABASE hce;" >/dev/null 2>&1
    docker compose exec citus-worker2 psql -U postgres -c "SELECT 1 FROM pg_database WHERE datname='hce';" | grep -q 1 || \
        docker compose exec citus-worker2 psql -U postgres -c "CREATE DATABASE hce;" >/dev/null 2>&1
    
    # Crear extensiones Citus en workers
    log "Creando extensiones Citus en workers..."
    docker compose exec citus-worker1 psql -U postgres -d hce -c "CREATE EXTENSION IF NOT EXISTS citus;" >/dev/null 2>&1 || true
    docker compose exec citus-worker2 psql -U postgres -d hce -c "CREATE EXTENSION IF NOT EXISTS citus;" >/dev/null 2>&1 || true
    
    # Registrar workers en el coordinator
    log "Registrando workers en el coordinator..."
    if docker compose exec citus-coordinator psql -U postgres -d hce -c "SELECT citus_add_node('citus-worker1', 5432);" >/dev/null 2>&1; then
        log "✅ Worker 1 registrado"
    else
        warning "Error registrando worker 1 (puede ya estar registrado)"
    fi
    
    if docker compose exec citus-coordinator psql -U postgres -d hce -c "SELECT citus_add_node('citus-worker2', 5432);" >/dev/null 2>&1; then
        log "✅ Worker 2 registrado"
    else
        warning "Error registrando worker 2 (puede ya estar registrado)"
    fi
    
    # Verificar configuración
    log "Verificando configuración del cluster..."
    local worker_count=$(docker compose exec citus-coordinator psql -U postgres -d hce -tAc "SELECT COUNT(*) FROM citus_get_active_worker_nodes();" 2>/dev/null || echo "0")
    
    if [ "$worker_count" -ge "2" ]; then
        log "✅ Cluster Citus configurado correctamente con $worker_count workers"
    else
        warning "Solo $worker_count workers registrados, se esperaban 2"
    fi
    
    # Ejecutar script de creación de usuarios si es necesario
    log "Verificando usuarios de autenticación..."
    local user_count=$(docker compose exec citus-coordinator psql -U postgres -d hce -tAc "SELECT COUNT(*) FROM users WHERE username IN ('admin','medico','paciente','auditor');" 2>/dev/null || echo "0")
    
    if [ "$user_count" -lt "4" ]; then
        log "Creando usuarios de demostración..."
        docker compose exec citus-coordinator psql -U postgres -d hce -f /docker-entrypoint-initdb.d/05-auth-tables.sql >/dev/null 2>&1 || warning "Error creando usuarios"
    else
        log "✅ Usuarios de demostración ya existen"
    fi
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
    
    # Configurar cluster Citus con la base de datos correcta
    log "Configurando cluster Citus..."
    wait_for_citus_services
    configure_citus_cluster
    
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