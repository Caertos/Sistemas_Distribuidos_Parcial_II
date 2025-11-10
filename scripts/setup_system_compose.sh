#!/bin/bash

# ===============================================
# Sistema FHIR Distribuido - Docker Compose
# Autores: Carlos Cochero, Andrés Palacio
# Versión: 4.0 - FastAPI Refactorizado
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

print_header() {
    echo -e "${BOLD}${CYAN}════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}════════════════════════════════════════${NC}"
}

# Verificar prerrequisitos
check_prerequisites() {
    print_header "VERIFICACIÓN DE PRERREQUISITOS"
    
    # Docker
    if ! command -v docker &> /dev/null; then
        error "Docker no está instalado. Por favor instale Docker primero."
    fi
    log "✅ Docker encontrado: $(docker --version)"
    
    # Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose no está instalado. Por favor instale Docker Compose primero."
    fi
    
    if command -v docker-compose &> /dev/null; then
        log "✅ Docker Compose encontrado: $(docker-compose --version)"
    else
        log "✅ Docker Compose (plugin) encontrado: $(docker compose version)"
    fi
    
    # Verificar que Docker esté corriendo
    if ! docker info &> /dev/null; then
        error "Docker no está corriendo. Por favor inicie Docker."
    fi
    log "✅ Docker está corriendo correctamente"
    
    log "✅ Todos los prerrequisitos verificados"
}

# Esperar a que los servicios de Citus estén listos
wait_for_citus_services() {
    log "Esperando a que los servicios de Citus estén listos..."
    
    local max_attempts=60
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log "Intento $attempt/$max_attempts - Verificando servicios Citus..."
        
        # Verificar que el coordinator esté listo y pueda ejecutar consultas
        if docker compose exec -T citus-coordinator pg_isready -U postgres -d hce_distribuida >/dev/null 2>&1 && \
           docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "SELECT 1;" >/dev/null 2>&1; then
            log "✅ Coordinator está listo y funcional"
            
            # Verificar workers con pruebas de conexión
            if docker compose exec -T citus-worker1 pg_isready -U postgres -d hce_distribuida >/dev/null 2>&1 && \
               docker compose exec -T citus-worker1 psql -U postgres -d hce_distribuida -c "SELECT 1;" >/dev/null 2>&1 && \
               docker compose exec -T citus-worker2 pg_isready -U postgres -d hce_distribuida >/dev/null 2>&1 && \
               docker compose exec -T citus-worker2 psql -U postgres -d hce_distribuida -c "SELECT 1;" >/dev/null 2>&1; then
                log "✅ Workers están listos y funcionales"
                
                # Verificar que la extensión Citus esté cargada
                if docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "SELECT citus_version();" >/dev/null 2>&1; then
                    log "✅ Extensión Citus confirmada en coordinator"
                    return 0
                else
                    log "⚠️  Extensión Citus no está lista en coordinator, reintentando..."
                fi
            fi
        fi
        
        if [ $((attempt % 5)) -eq 0 ]; then
            log "Servicios aún no están completamente listos, esperando 10 segundos más..."
        fi
        sleep 10
        attempt=$((attempt + 1))
    done
    
    error "Los servicios de Citus tardaron demasiado en estar listos (timeout: 10 minutos)"
}

# Configurar cluster Citus correctamente
configure_citus_cluster() {
    log "Configurando cluster Citus con base de datos 'hce_distribuida'..."
    
    # Esperar un poco más para estabilización
    sleep 15
    
    # Configurar hostname del coordinator
    log "Estableciendo hostname del coordinator..."
    local max_attempts=5
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "SELECT citus_set_coordinator_host('citus-coordinator');" >/dev/null 2>&1; then
            log "✅ Hostname del coordinator establecido"
            break
        else
            if [ $attempt -eq $max_attempts ]; then
                warning "No se pudo establecer el hostname del coordinator después de $max_attempts intentos"
            else
                log "Reintentando configuración del coordinator... (intento $attempt/$max_attempts)"
                sleep 5
            fi
        fi
        attempt=$((attempt + 1))
    done
    
    # Registrar workers en el coordinator
    log "Registrando workers en el coordinator..."
    
    # Worker 1
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "SELECT citus_add_node('citus-worker1', 5432);" >/dev/null 2>&1; then
            log "✅ Worker 1 registrado"
            break
        else
            if [ $attempt -eq $max_attempts ]; then
                warning "Error registrando worker 1 después de $max_attempts intentos (puede ya estar registrado)"
            else
                log "Reintentando registro de worker 1... (intento $attempt/$max_attempts)"
                sleep 3
            fi
        fi
        attempt=$((attempt + 1))
    done
    
    # Worker 2
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "SELECT citus_add_node('citus-worker2', 5432);" >/dev/null 2>&1; then
            log "✅ Worker 2 registrado"
            break
        else
            if [ $attempt -eq $max_attempts ]; then
                warning "Error registrando worker 2 después de $max_attempts intentos (puede ya estar registrado)"
            else
                log "Reintentando registro de worker 2... (intento $attempt/$max_attempts)"
                sleep 3
            fi
        fi
        attempt=$((attempt + 1))
    done
    
    # Verificar configuración final
    log "Verificando configuración del cluster..."
    sleep 5
    
    local worker_count=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM citus_get_active_worker_nodes();" 2>/dev/null || echo "0")
    
    if [ "$worker_count" -ge "2" ]; then
        log "✅ Cluster Citus configurado correctamente con $worker_count workers"
        
        # Mostrar workers registrados
        log "Workers activos:"
        docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "SELECT * FROM citus_get_active_worker_nodes();" 2>/dev/null || true
    else
        warning "Solo $worker_count workers registrados, se esperaban 2"
        
        # Mostrar detalles para debugging
        log "Intentando mostrar workers disponibles:"
        docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "SELECT * FROM citus_get_active_worker_nodes();" 2>/dev/null || warning "No se pudo obtener información de workers"
    fi
    
    # Verificar usuarios de autenticación
    log "Verificando usuarios de autenticación..."
    local user_count=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM users WHERE username IN ('admin','medico','paciente','auditor');" 2>/dev/null || echo "0")
    
    if [ "$user_count" -ge "4" ]; then
        log "✅ Usuarios de demostración ya existen ($user_count usuarios)"
    else
        log "Usuarios encontrados: $user_count/4"
        if [ "$user_count" -eq "0" ]; then
            log "Los usuarios se crearán automáticamente al inicializar la base de datos"
        fi
    fi
}

# Verificar el estado del sistema
verify_system() {
    print_header "VERIFICACIÓN DEL SISTEMA"
    
    # Verificar contenedores
    log "Estado de contenedores:"
    docker compose ps
    
    # Verificar conectividad de la base de datos
    log "Verificando conectividad de base de datos..."
    local tables_count=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")
    log "Tablas en la base de datos: $tables_count"
    
    # Verificar cluster Citus
    log "Verificando cluster Citus..."
    docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "SELECT * FROM citus_get_active_worker_nodes();" 2>/dev/null || warning "Error verificando workers"
    
    # Verificar FastAPI
    log "Verificando servicio FastAPI..."
    sleep 10
    
    local health_check_attempts=0
    local max_health_attempts=30
    
    while [ $health_check_attempts -lt $max_health_attempts ]; do
        if curl -s http://localhost:8000/health | grep -q "healthy" 2>/dev/null; then
            log "✅ FastAPI responde correctamente"
            break
        fi
        
        health_check_attempts=$((health_check_attempts + 1))
        if [ $((health_check_attempts % 5)) -eq 0 ]; then
            log "Esperando FastAPI... (intento $health_check_attempts/$max_health_attempts)"
        fi
        sleep 2
    done
    
    if [ $health_check_attempts -eq $max_health_attempts ]; then
        warning "FastAPI no responde al endpoint de salud"
    fi
    
    # Verificar página de login
    if curl -s http://localhost:8000/login | grep -q "Sistema FHIR" 2>/dev/null; then
        log "✅ Página de login accesible"
    else
        warning "Página de login podría tener problemas"
    fi
    
    log "✅ Verificación del sistema completada"
}

# Mostrar información de usuarios
show_users() {
    echo ""
    echo -e "${BOLD}${YELLOW}🔑 CREDENCIALES DE ACCESO:${NC}"
    echo -e "  👤 Admin:     ${GREEN}admin${NC} / ${GREEN}secret${NC}"
    echo -e "  👨‍⚕️ Médico:    ${GREEN}medico${NC} / ${GREEN}secret${NC}"
    echo -e "  👩‍🦰 Paciente:  ${GREEN}paciente${NC} / ${GREEN}secret${NC}"
    echo -e "  👁️ Auditor:   ${GREEN}auditor${NC} / ${GREEN}secret${NC}"
}

# Docker Compose Setup
setup_docker_compose() {
    print_header "CONFIGURACIÓN CON DOCKER COMPOSE"
    
    # Limpiar instalaciones previas
    log "Limpiando instalaciones previas..."
    docker compose down -v 2>/dev/null || true
    docker system prune -f >/dev/null 2>&1 || true
    
    # Construir imágenes
    log "Construyendo imágenes Docker..."
    docker compose build --no-cache --parallel
    
    # Iniciar servicios de base de datos primero
    log "Iniciando servicios de base de datos..."
    docker compose up -d citus-coordinator citus-worker1 citus-worker2
    
    # Esperar que los servicios de BD estén listos
    wait_for_citus_services
    
    # Configurar cluster Citus
    configure_citus_cluster
    
    # Ahora iniciar FastAPI
    log "Iniciando servicio FastAPI..."
    docker compose up -d fastapi-app
    
    # Iniciar nginx
    log "Iniciando servicio Nginx..."
    docker compose up -d nginx-proxy
    
    # Verificar todos los servicios
    verify_system
    
    log "✅ Sistema Docker Compose configurado correctamente!"
}

# Mostrar información final
show_final_info() {
    print_header "🎉 ¡SISTEMA FHIR DESPLEGADO EXITOSAMENTE!"
    
    echo ""
    echo -e "${BOLD}${GREEN}📋 INFORMACIÓN DE ACCESO:${NC}"
    echo -e "  🌐 Sistema Web:           ${CYAN}http://localhost${NC}"
    echo -e "  🔐 Página de Login:       ${CYAN}http://localhost/login${NC}"
    echo -e "  📊 Dashboard:             ${CYAN}http://localhost/dashboard${NC}"
    echo -e "  📡 API Directa:           ${CYAN}http://localhost:8000${NC}"
    echo -e "  📖 Documentación API:     ${CYAN}http://localhost:8000/docs${NC}"
    echo -e "  🔍 API Interactiva:       ${CYAN}http://localhost:8000/redoc${NC}"
    
    show_users
    
    echo ""
    echo -e "${BOLD}${BLUE}🛠️ COMANDOS ÚTILES:${NC}"
    echo -e "  Ver logs FastAPI:         ${CYAN}docker compose logs -f fastapi-app${NC}"
    echo -e "  Ver logs Citus:           ${CYAN}docker compose logs -f citus-coordinator${NC}"
    echo -e "  Ver todos los logs:       ${CYAN}docker compose logs -f${NC}"
    echo -e "  Estado del sistema:       ${CYAN}docker compose ps${NC}"
    echo -e "  Reiniciar servicios:      ${CYAN}docker compose restart${NC}"
    echo ""
    echo -e "${BOLD}${RED}🧹 PARA LIMPIAR EL ENTORNO:${NC}"
    echo -e "  Detener servicios:        ${CYAN}docker compose down${NC}"
    echo -e "  Limpiar completamente:    ${CYAN}./cleanup.sh${NC}"
    echo ""
    log "🚀 Accede a http://localhost/login para comenzar"
}

# Función principal
main() {
    check_prerequisites
    setup_docker_compose
    show_final_info
}

# Manejar señales
trap 'echo -e "\n${RED}Instalación interrumpida por el usuario${NC}"; docker compose down 2>/dev/null || true; exit 1' INT TERM

# Ejecutar función principal
main "$@"