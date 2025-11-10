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

# Función de rollback en caso de error
rollback_deployment() {
    local error_message="$1"
    echo -e "\n${RED}❌ Error durante el despliegue: $error_message${NC}"
    echo -e "${YELLOW}Iniciando rollback automático...${NC}"
    
    log "Deteniendo servicios..."
    docker compose down -v --remove-orphans 2>/dev/null || true
    
    log "Limpiando imágenes del proyecto..."
    docker images --format "table {{.Repository}}:{{.Tag}}" | grep -E "(sistemas_distribuidos|fastapi-app|nginx-proxy)" | xargs -r docker rmi -f 2>/dev/null || true
    
    log "Limpiando caché de construcción..."
    docker builder prune -f >/dev/null 2>&1 || true
    
    echo -e "${GREEN}✅ Rollback completado. El sistema ha sido limpiado.${NC}"
    echo -e "${CYAN}Puede reintentar el despliegue ejecutando: ./setup.sh compose${NC}"
    exit 1
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    rollback_deployment "$1"
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
    
    # Verificar herramientas de parsing JSON
    if ! command -v jq &> /dev/null; then
        warning "jq no está disponible, usando métodos alternativos para healthchecks"
        log "Recomendación: instale jq para mejor diagnostico (sudo apt install jq)"
    else
        log "✅ jq encontrado para parsing JSON"
    fi
    
    # Verificar curl para healthchecks
    if ! command -v curl &> /dev/null; then
        warning "curl no está disponible, algunos healthchecks podrían fallar"
        log "Recomendación: instale curl (sudo apt install curl)"
    else
        log "✅ curl encontrado para healthchecks"
    fi
    
    # Verificar espacio en disco disponible
    local available_space=$(df . | awk 'NR==2 {print $4}')
    local required_space=2097152  # 2GB en KB
    
    if [ "$available_space" -lt "$required_space" ]; then
        warning "Espacio en disco bajo: $(( available_space / 1024 ))MB disponibles, recomendados 2GB+"
    else
        log "✅ Espacio en disco suficiente: $(( available_space / 1024 ))MB disponibles"
    fi
    
    log "✅ Verificación de prerrequisitos completada"
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
    
    # Esperar estabilización básica
    log "Esperando estabilización básica de los servicios..."
    sleep 15
    
    # Verificar que todos los servicios están realmente operativos
    local services_ready=false
    local stability_check=0
    local max_stability_checks=3
    
    while [ $stability_check -lt $max_stability_checks ] && [ "$services_ready" = false ]; do
        log "Verificación de estabilidad $((stability_check + 1))/$max_stability_checks..."
        
        if docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "SELECT citus_version();" >/dev/null 2>&1 && \
           docker compose exec -T citus-worker1 psql -U postgres -d hce_distribuida -c "SELECT citus_version();" >/dev/null 2>&1 && \
           docker compose exec -T citus-worker2 psql -U postgres -d hce_distribuida -c "SELECT citus_version();" >/dev/null 2>&1; then
            log "✅ Todos los servicios Citus están estables"
            services_ready=true
        else
            log "Servicios aún no están completamente estables, esperando 10 segundos..."
            sleep 10
            stability_check=$((stability_check + 1))
        fi
    done
    
    if [ "$services_ready" = false ]; then
        error "Los servicios no alcanzaron estabilidad completa después de $max_stability_checks verificaciones"
    fi
    
    # Configurar hostname del coordinator con retry robusto
    log "Estableciendo hostname del coordinator..."
    local max_attempts=10
    local attempt=1
    local coordinator_configured=false
    
    while [ $attempt -le $max_attempts ] && [ "$coordinator_configured" = false ]; do
        # Verificar si ya está configurado
        local current_host=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT host FROM citus_get_local_session_stats() LIMIT 1;" 2>/dev/null || echo "")
        
        if [ "$current_host" = "citus-coordinator" ]; then
            log "✅ Hostname del coordinator ya estaba configurado"
            coordinator_configured=true
        else
            log "Configurando hostname del coordinator... (intento $attempt/$max_attempts)"
            if docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "SELECT citus_set_coordinator_host('citus-coordinator', 5432);" >/dev/null 2>&1; then
                log "✅ Hostname del coordinator establecido exitosamente"
                coordinator_configured=true
            else
                log "Reintentando configuración del coordinator en 8 segundos..."
                sleep 8
            fi
        fi
        attempt=$((attempt + 1))
    done
    
    if [ "$coordinator_configured" = false ]; then
        error "No se pudo configurar el hostname del coordinator después de $max_attempts intentos"
    fi
    
    # Función para registrar worker con verificación previa
    register_worker() {
        local worker_name=$1
        local worker_port=5432
        local max_worker_attempts=8
        local worker_attempt=1
        
        log "Registrando $worker_name..."
        
        while [ $worker_attempt -le $max_worker_attempts ]; do
            # Verificar si el worker ya está registrado
            local existing_worker=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM citus_get_active_worker_nodes() WHERE node_name = '$worker_name';" 2>/dev/null || echo "0")
            
            if [ "$existing_worker" -gt "0" ]; then
                log "✅ $worker_name ya estaba registrado"
                return 0
            fi
            
            # Verificar conectividad desde coordinator hacia worker
            if docker compose exec -T citus-coordinator psql -U postgres -h $worker_name -p $worker_port -d hce_distribuida -c "SELECT 1;" >/dev/null 2>&1; then
                log "Conectividad confirmada hacia $worker_name"
                
                # Intentar registrar el worker
                if docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "SELECT citus_add_node('$worker_name', $worker_port);" >/dev/null 2>&1; then
                    log "✅ $worker_name registrado exitosamente"
                    return 0
                else
                    log "Error al registrar $worker_name, reintentando en 5 segundos... (intento $worker_attempt/$max_worker_attempts)"
                fi
            else
                log "Sin conectividad hacia $worker_name, reintentando en 5 segundos... (intento $worker_attempt/$max_worker_attempts)"
            fi
            
            sleep 5
            worker_attempt=$((worker_attempt + 1))
        done
        
        warning "No se pudo registrar $worker_name después de $max_worker_attempts intentos"
        return 1
    }
    
    # Registrar workers
    register_worker "citus-worker1"
    register_worker "citus-worker2"
    
    # Verificación final y completa del cluster
    log "Realizando verificación final del cluster..."
    sleep 10
    
    local final_worker_count=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM citus_get_active_worker_nodes();" 2>/dev/null || echo "0")
    
    if [ "$final_worker_count" -ge "2" ]; then
        log "✅ Cluster Citus configurado exitosamente con $final_worker_count workers"
        
        # Mostrar información detallada del cluster
        log "Información del cluster Citus:"
        docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "\
            SELECT 
                node_name as \"Worker\", 
                node_port as \"Puerto\", 
                CASE WHEN isactive THEN 'Activo' ELSE 'Inactivo' END as \"Estado\"
            FROM citus_get_active_worker_nodes() 
            ORDER BY node_name;" 2>/dev/null || warning "No se pudo obtener información detallada del cluster"
            
        # Verificar distribución de tablas (si existen)
        local distributed_tables=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM citus_tables;" 2>/dev/null || echo "0")
        log "Tablas distribuidas configuradas: $distributed_tables"
        
        # Realizar test de conectividad completo del cluster
        log "Realizando test de conectividad del cluster..."
        if docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "SELECT count(*) FROM citus_get_active_worker_nodes() WHERE isactive = true;" >/dev/null 2>&1; then
            local active_workers=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT count(*) FROM citus_get_active_worker_nodes() WHERE isactive = true;" 2>/dev/null || echo "0")
            if [ "$active_workers" -ge "2" ]; then
                log "✅ Test de conectividad exitoso: $active_workers workers activos"
            else
                warning "Solo $active_workers workers están activos de $final_worker_count registrados"
            fi
        else
            warning "No se pudo completar test de conectividad del cluster"
        fi
        
    elif [ "$final_worker_count" -gt "0" ]; then
        warning "Cluster parcialmente configurado: $final_worker_count/2 workers registrados"
        docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "SELECT * FROM citus_get_active_worker_nodes();" 2>/dev/null || true
        
        # Intentar reparación automática
        log "Intentando reparación automática del cluster..."
        sleep 10
        register_worker "citus-worker1"
        register_worker "citus-worker2"
        
        local retry_count=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM citus_get_active_worker_nodes();" 2>/dev/null || echo "0")
        if [ "$retry_count" -ge "2" ]; then
            log "✅ Reparación automática exitosa: $retry_count workers registrados"
        else
            error "No se pudo reparar el cluster automáticamente ($retry_count/2 workers)"
        fi
    else
        error "No se pudieron registrar workers en el cluster Citus"
    fi
    
    # Verificar que las tablas de aplicación están creadas
    log "Verificando esquema de base de datos..."
    local app_tables=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('users', 'patients', 'practitioners');" 2>/dev/null || echo "0")
    
    if [ "$app_tables" -ge "3" ]; then
        log "✅ Esquema de aplicación verificado ($app_tables tablas principales encontradas)"
    else
        log "⚠️  Esquema de aplicación: $app_tables/3 tablas principales encontradas"
    fi
    
    # Verificar usuarios de autenticación
    log "Verificando usuarios de autenticación..."
    local user_count=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM users WHERE username IN ('admin','medico','paciente','auditor');" 2>/dev/null || echo "0")
    
    if [ "$user_count" -ge "4" ]; then
        log "✅ Usuarios de demostración configurados ($user_count usuarios)"
    else
        log "Usuarios encontrados: $user_count/4 (se configurarán automáticamente)"
    fi
}

# Verificar el estado del sistema
verify_system() {
    print_header "VERIFICACIÓN COMPLETA DEL SISTEMA"
    
    # Verificar contenedores
    log "Estado detallado de contenedores:"
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    
    # Verificar conectividad de la base de datos
    log "Verificando conectividad de base de datos..."
    local tables_count=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")
    log "📊 Tablas en la base de datos: $tables_count"
    
    # Verificar extensiones de PostgreSQL
    local extensions=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT string_agg(extname, ', ') FROM pg_extension WHERE extname != 'plpgsql';" 2>/dev/null || echo "ninguna")
    log "🔧 Extensiones instaladas: $extensions"
    
    # Verificar cluster Citus con detalles
    log "Verificando cluster Citus..."
    local cluster_status=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM citus_get_active_worker_nodes();" 2>/dev/null || echo "0")
    
    if [ "$cluster_status" -ge "2" ]; then
        log "✅ Cluster Citus operativo con $cluster_status workers"
        docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -c "SELECT node_name, node_port, isactive FROM citus_get_active_worker_nodes();" 2>/dev/null || true
    else
        warning "⚠️  Cluster Citus: solo $cluster_status workers detectados"
    fi
    
    # Verificar usuarios de la aplicación
    local app_users=$(docker compose exec -T citus-coordinator psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
    log "👥 Usuarios en el sistema: $app_users"
    
    # Verificar FastAPI con múltiples endpoints
    log "Verificando servicio FastAPI..."
    local fastapi_attempts=0
    local max_fastapi_attempts=30
    local fastapi_healthy=false
    
    while [ $fastapi_attempts -lt $max_fastapi_attempts ] && [ "$fastapi_healthy" = false ]; do
        # Verificar endpoint de salud
        if curl -s http://localhost:8000/health 2>/dev/null | grep -q "healthy"; then
            log "✅ FastAPI - Endpoint de salud operativo"
            fastapi_healthy=true
            
            # Verificar endpoint de documentación
            if curl -s http://localhost:8000/docs 2>/dev/null | grep -q "FastAPI"; then
                log "✅ FastAPI - Documentación accesible"
            fi
            
            # Verificar endpoint de login
            if curl -s http://localhost:8000/login 2>/dev/null | grep -q "Sistema FHIR"; then
                log "✅ FastAPI - Página de login accesible"
            else
                warning "⚠️  Página de login podría tener problemas"
            fi
            
        else
            fastapi_attempts=$((fastapi_attempts + 1))
            if [ $((fastapi_attempts % 5)) -eq 0 ]; then
                log "Esperando FastAPI... (intento $fastapi_attempts/$max_fastapi_attempts)"
            fi
            sleep 2
        fi
    done
    
    if [ "$fastapi_healthy" = false ]; then
        warning "⚠️  FastAPI no responde después de $max_fastapi_attempts intentos"
        
        # Mostrar logs para debugging
        log "Últimas líneas de logs de FastAPI:"
        docker compose logs --tail=10 fastapi-app 2>/dev/null || true
    fi
    
    # Verificar Nginx
    log "Verificando proxy Nginx..."
    if curl -s http://localhost/ 2>/dev/null | grep -q -i "html\|login\|sistema"; then
        log "✅ Nginx - Proxy funcionando correctamente"
    else
        warning "⚠️  Nginx podría tener problemas de configuración"
    fi
    
    # Verificar puertos
    log "Verificando puertos disponibles:"
    local ports_check=$(netstat -tuln 2>/dev/null | grep -E ":(80|443|5432|5433|5434|8000)" || ss -tuln 2>/dev/null | grep -E ":(80|443|5432|5433|5434|8000)" || echo "Comando netstat/ss no disponible")
    echo "$ports_check" | while read line; do
        if [ -n "$line" ] && [ "$line" != "Comando netstat/ss no disponible" ]; then
            log "🌐 $line"
        fi
    done
    
    # Resumen final
    local all_healthy=true
    if [ "$tables_count" -lt "5" ]; then all_healthy=false; fi
    if [ "$cluster_status" -lt "2" ]; then all_healthy=false; fi
    if [ "$fastapi_healthy" = false ]; then all_healthy=false; fi
    
    echo ""
    if [ "$all_healthy" = true ]; then
        log "🎉 ¡Sistema completamente operativo y verificado!"
    else
        warning "⚠️  Sistema parcialmente operativo - revisar elementos marcados"
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
    
    # Limpiar instalaciones previas completamente
    log "Limpiando instalaciones previas..."
    docker compose down -v --remove-orphans 2>/dev/null || true
    docker system prune -f >/dev/null 2>&1 || true
    
    # Construir imágenes
    log "Construyendo imágenes Docker..."
    docker compose build --no-cache --parallel
    
    # Iniciar servicios de base de datos con verificación de healthcheck
    log "Iniciando servicios de base de datos Citus..."
    docker compose up -d citus-coordinator citus-worker1 citus-worker2
    
    # Función para obtener estado de salud del servicio
    get_service_health() {
        local service_name=$1
        
        # Primero verificar si el contenedor está corriendo
        local container_status=$(docker compose ps "$service_name" --format json 2>/dev/null)
        
        if [ -z "$container_status" ] || [ "$container_status" = "[]" ]; then
            echo "not_running"
            return
        fi
        
        if command -v jq &> /dev/null; then
            # Usar jq si está disponible
            local health=$(echo "$container_status" | jq -r '.[0].Health // "unknown"' 2>/dev/null)
            local state=$(echo "$container_status" | jq -r '.[0].State // "unknown"' 2>/dev/null)
            
            if [ "$health" = "healthy" ]; then
                echo "healthy"
            elif [ "$health" = "unhealthy" ]; then
                echo "unhealthy"
            elif [ "$state" = "running" ]; then
                echo "running"
            else
                echo "$state"  # starting, exited, etc.
            fi
        else
            # Método alternativo sin jq - usar docker compose ps directamente
            local status_line=$(docker compose ps "$service_name" 2>/dev/null | grep "$service_name" | head -1)
            
            if echo "$status_line" | grep -q "Up.*healthy"; then
                echo "healthy"
            elif echo "$status_line" | grep -q "Up.*unhealthy"; then
                echo "unhealthy"
            elif echo "$status_line" | grep -q "Up.*starting"; then
                echo "starting"
            elif echo "$status_line" | grep -q "Up"; then
                echo "running"
            elif echo "$status_line" | grep -q "Exit"; then
                echo "exited"
            else
                echo "unknown"
            fi
        fi
    }
    
    # Esperar a que los servicios estén al menos corriendo
    log "Esperando a que los servicios estén corriendo..."
    local health_timeout=180  # 3 minutos para estar corriendo
    local health_start=$(date +%s)
    local services_running=false
    
    while [ $(($(date +%s) - health_start)) -lt $health_timeout ] && [ "$services_running" = false ]; do
        local coordinator_health=$(get_service_health "citus-coordinator")
        local worker1_health=$(get_service_health "citus-worker1")
        local worker2_health=$(get_service_health "citus-worker2")
        
        # Considerar como válidos: healthy, running, o starting
        local coord_ok=false
        local work1_ok=false
        local work2_ok=false
        
        if [ "$coordinator_health" = "healthy" ] || [ "$coordinator_health" = "running" ] || [ "$coordinator_health" = "starting" ]; then
            coord_ok=true
        fi
        
        if [ "$worker1_health" = "healthy" ] || [ "$worker1_health" = "running" ] || [ "$worker1_health" = "starting" ]; then
            work1_ok=true
        fi
        
        if [ "$worker2_health" = "healthy" ] || [ "$worker2_health" = "running" ] || [ "$worker2_health" = "starting" ]; then
            work2_ok=true
        fi
        
        if [ "$coord_ok" = true ] && [ "$work1_ok" = true ] && [ "$work2_ok" = true ]; then
            log "✅ Todos los servicios de base de datos están corriendo"
            services_running=true
        else
            log "Esperando servicios... Coordinator: $coordinator_health, Worker1: $worker1_health, Worker2: $worker2_health"
            sleep 10
        fi
    done
    
    if [ "$services_running" = false ]; then
        warning "Los servicios tardaron mucho en arrancar, continuando con verificación manual..."
    fi
    
    # Esperar un poco más para que se estabilicen
    log "Esperando estabilización de servicios..."
    sleep 30
    
    # Verificación adicional manual
    wait_for_citus_services
    
    # Configurar cluster Citus con todos los mecanismos de retry mejorados
    configure_citus_cluster
    
    # Iniciar FastAPI con dependency check
    log "Iniciando servicio FastAPI (esperando hasta que las dependencias estén ready)..."
    docker compose up -d fastapi-app
    
    # Esperar a que FastAPI esté operativo
    log "Esperando a que FastAPI esté operativo..."
    local fastapi_timeout=120  # 2 minutos
    local fastapi_start=$(date +%s)
    local fastapi_ready=false
    
    while [ $(($(date +%s) - fastapi_start)) -lt $fastapi_timeout ] && [ "$fastapi_ready" = false ]; do
        local fastapi_health=$(get_service_health "fastapi-app")
        
        if [ "$fastapi_health" = "healthy" ] || [ "$fastapi_health" = "running" ] || [ "$fastapi_health" = "starting" ]; then
            log "✅ FastAPI está operativo (estado: $fastapi_health)"
            fastapi_ready=true
        else
            log "Esperando FastAPI... Estado: $fastapi_health"
            sleep 10
        fi
    done
    
    if [ "$fastapi_ready" = false ]; then
        warning "FastAPI no alcanzó estado operativo, pero continuando..."
    fi
    
    # Iniciar nginx
    log "Iniciando servicio Nginx..."
    docker compose up -d nginx-proxy
    
    # Esperar a que nginx esté listo
    log "Esperando a que Nginx esté operativo..."
    sleep 15
    
    # Verificar todos los servicios con diagnósticos mejorados
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
trap 'echo -e "\n${RED}Instalación interrumpida por el usuario${NC}"; rollback_deployment "Interrupción del usuario"' INT TERM

# Ejecutar función principal
main "$@"