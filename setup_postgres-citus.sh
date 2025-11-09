#!/usr/bin/env bash
# setup_all.sh - Instalador Asistido del Sistema Citus Distribuido
# Versión: 2.0 - Instalación Interactiva
# Uso:
#   ./setup_all.sh           # Modo interactivo (recomendado)
#   ./setup_all.sh compose   # Instalación automática con Docker Compose
#   ./setup_all.sh minikube  # Instalación automática con Minikube

set -euo pipefail

# Colores para mejor visualización
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Funciones de logging
log_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_step() {
    echo -e "${CYAN}${BOLD}==>${NC} ${BOLD}$1${NC}"
}

log_substep() {
    echo -e "    ${BLUE}→${NC} $1"
}

# Función para preguntar confirmación al usuario
ask_confirmation() {
    local question="$1"
    local default="${2:-y}"
    
    if [ "$default" = "y" ]; then
        local prompt="[Y/n]"
    else
        local prompt="[y/N]"
    fi
    
    echo -e "${CYAN}${BOLD}?${NC} $question $prompt"
    read -r response
    
    response=${response:-$default}
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

# Función para mostrar título
show_banner() {
    clear
    echo -e "${CYAN}${BOLD}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║        Sistema Distribuido PostgreSQL + Citus                    ║
║           Instalador Asistido e Interactivo                      ║
║                                                                  ║
║                      Versión 2.0                                 ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

show_banner

# Detectar modo de operación
MODE="${1:-}"

if [ -z "$MODE" ]; then
    # Modo interactivo
    echo -e "${BOLD}Bienvenido al instalador del Sistema Citus Distribuido${NC}"
    echo ""
    echo "Este instalador te guiará paso a paso en la configuración del sistema."
    echo ""
    echo -e "${BOLD}Opciones disponibles:${NC}"
    echo "  1) Docker Compose  - Rápido y sencillo (recomendado para desarrollo)"
    echo "  2) Minikube/K8s    - Alta disponibilidad (recomendado para pruebas de HA)"
    echo "  3) Salir"
    echo ""
    read -p "Selecciona una opción (1-3): " option
    
    case "$option" in
        1) MODE="compose" ;;
        2) MODE="minikube" ;;
        3) echo "Instalación cancelada."; exit 0 ;;
        *) log_error "Opción inválida"; exit 1 ;;
    esac
    
    INTERACTIVE=true
else
    INTERACTIVE=false
fi

# Función para instalación con Docker Compose
install_docker_compose() {
    show_banner
    echo -e "${BOLD}=== Instalación con Docker Compose ===${NC}"
    echo ""
    
    # Paso 1: Verificar dependencias
    log_step "PASO 1: Verificación de dependencias"
    if ! command -v docker &> /dev/null; then
        log_error "Docker no está instalado o no está en PATH"
        echo "Instala Docker desde: https://docs.docker.com/get-docker/"
        exit 1
    fi
    log_info "Docker está instalado"
    log_substep "Versión: $(docker --version)"
    echo ""
    
    if [ "$INTERACTIVE" = true ]; then
        if ! ask_confirmation "¿Continuar con el despliegue?"; then
            log_warn "Instalación cancelada por el usuario"
            exit 0
        fi
        echo ""
    fi
    
    # Paso 2: Limpiar instalación anterior
    log_step "PASO 2: Limpieza de instalación anterior (si existe)"
    log_substep "Deteniendo contenedores existentes..."
    docker compose down 2>/dev/null || true
    log_info "Limpieza completada"
    echo ""
    
    if [ "$INTERACTIVE" = true ]; then
        if ! ask_confirmation "¿Continuar levantando los servicios?"; then
            log_warn "Instalación cancelada por el usuario"
            exit 0
        fi
        echo ""
    fi
    
    # Paso 3: Levantar servicios
    log_step "PASO 3: Levantando servicios con Docker Compose"
    log_substep "Esto tomará unos momentos..."
    if docker compose up -d; then
        log_info "Servicios levantados exitosamente"
    else
        log_error "Error al levantar los servicios"
        exit 1
    fi
    echo ""
    
    # Paso 4: Esperar inicialización
    log_step "PASO 4: Esperando inicialización de PostgreSQL"
    log_substep "Tiempo estimado: 15-20 segundos"
    sleep 15
    
    # Verificar que los contenedores están corriendo
    if ! docker compose ps | grep -q "Up"; then
        log_error "Los contenedores no están corriendo"
        echo ""
        echo "Logs del coordinator:"
        docker compose logs citus-coordinator --tail=20
        exit 1
    fi
    log_info "Contenedores en ejecución"
    echo ""
    
    # Paso 5: Verificar conectividad
    log_step "PASO 5: Verificando conectividad con el coordinator"
    CONNECTED=false
    for i in {1..10}; do
        if docker compose exec -T citus-coordinator psql -U postgres -c "SELECT 1;" &>/dev/null; then
            log_info "Conexión exitosa con el coordinator"
            CONNECTED=true
            break
        fi
        log_substep "Intento $i/10..."
        sleep 3
    done
    
    if [ "$CONNECTED" = false ]; then
        log_error "No se pudo conectar al coordinator después de 10 intentos"
        exit 1
    fi
    echo ""
    
    if [ "$INTERACTIVE" = true ]; then
        if ! ask_confirmation "¿Continuar con el registro de workers?"; then
            log_warn "Proceso detenido. Los contenedores están corriendo pero los workers no están registrados."
            echo "Para registrar manualmente: bash register_citus.sh --rebalance --drain"
            exit 0
        fi
        echo ""
    fi
    
    # Paso 6: Registrar workers
    log_step "PASO 6: Registrando workers en el cluster"
    log_substep "Ejecutando registro, rebalanceo y drain..."
    if bash register_citus.sh --rebalance --drain; then
        log_info "Workers registrados y configurados correctamente"
    else
        log_error "Error en el registro de workers"
        exit 1
    fi
    echo ""
    
    # Resumen final
    show_completion_compose
}

# Función para instalación con Minikube
install_minikube() {
    show_banner
    echo -e "${BOLD}=== Instalación con Minikube/Kubernetes ===${NC}"
    echo ""
    
    # Paso 1: Verificar dependencias
    log_step "PASO 1: Verificación de dependencias"
    local missing_deps=()
    
    for cmd in minikube kubectl docker; do
        if command -v "$cmd" &> /dev/null; then
            log_info "$cmd está instalado"
            log_substep "Versión: $($cmd version --short 2>/dev/null | head -1 || echo 'N/A')"
        else
            log_error "$cmd NO está instalado"
            missing_deps+=("$cmd")
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo ""
        log_error "Faltan las siguientes dependencias: ${missing_deps[*]}"
        echo ""
        echo "Instalación requerida:"
        echo "  - Docker:   https://docs.docker.com/get-docker/"
        echo "  - Minikube: https://minikube.sigs.k8s.io/docs/start/"
        echo "  - kubectl:  https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi
    echo ""
    
    if [ "$INTERACTIVE" = true ]; then
        if ! ask_confirmation "¿Continuar con el despliegue en Minikube?"; then
            log_warn "Instalación cancelada por el usuario"
            exit 0
        fi
        echo ""
    fi
    
    # Paso 2: Limpiar cluster anterior
    log_step "PASO 2: Verificando cluster de Minikube existente"
    if minikube status &>/dev/null; then
        log_warn "Existe un cluster de Minikube"
        if [ "$INTERACTIVE" = true ]; then
            if ask_confirmation "¿Deseas eliminar el cluster existente y crear uno nuevo?" "n"; then
                log_substep "Eliminando cluster existente..."
                minikube delete
                log_info "Cluster eliminado"
            else
                log_info "Reutilizando cluster existente"
            fi
        fi
    else
        log_info "No hay cluster existente"
    fi
    echo ""
    
    if [ "$INTERACTIVE" = true ]; then
        if ! ask_confirmation "¿Continuar con la configuración de Minikube?"; then
            log_warn "Instalación cancelada por el usuario"
            exit 0
        fi
        echo ""
    fi
    
    # Paso 3: Ejecutar setup de Minikube
    log_step "PASO 3: Configurando Minikube y desplegando Citus"
    log_substep "Este proceso puede tomar 3-5 minutos..."
    log_substep "Ejecutando k8s/setup_minikube.sh"
    echo ""
    
    if [ ! -x k8s/setup_minikube.sh ]; then
        chmod +x k8s/setup_minikube.sh
    fi
    
    # Ejecutar setup (sin modo interactivo interno)
    if ./k8s/setup_minikube.sh; then
        log_info "Despliegue en Minikube completado"
    else
        log_error "Error en el despliegue de Minikube"
        exit 1
    fi
    echo ""
    
    # Resumen final
    show_completion_minikube
}

# Función para mostrar resumen final - Docker Compose
show_completion_compose() {
    echo ""
    echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║                                                                  ║${NC}"
    echo -e "${GREEN}${BOLD}║           ✅ INSTALACIÓN COMPLETADA EXITOSAMENTE ✅             ║${NC}"
    echo -e "${GREEN}${BOLD}║                                                                  ║${NC}"
    echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BOLD}Sistema instalado:${NC} Docker Compose"
    echo -e "${BOLD}Coordinator:${NC} 1 contenedor"
    echo -e "${BOLD}Workers:${NC} 2 contenedores"
    echo ""
    echo -e "${BOLD}📋 Comandos útiles:${NC}"
    echo ""
    echo -e "  ${CYAN}Conectarse a la base de datos:${NC}"
    echo "    psql -h localhost -p 5432 -U postgres -d hce_distribuida"
    echo ""
    echo -e "  ${CYAN}Ver estado de contenedores:${NC}"
    echo "    docker compose ps"
    echo ""
    echo -e "  ${CYAN}Ver logs:${NC}"
    echo "    docker compose logs -f citus-coordinator"
    echo ""
    echo -e "  ${CYAN}Detener el sistema:${NC}"
    echo "    docker compose down"
    echo ""
    echo -e "  ${CYAN}Ejecutar pruebas:${NC}"
    echo "    ./test_cluster.sh"
    echo ""
}

# Función para mostrar resumen final - Minikube
show_completion_minikube() {
    echo ""
    echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║                                                                  ║${NC}"
    echo -e "${GREEN}${BOLD}║           ✅ INSTALACIÓN COMPLETADA EXITOSAMENTE ✅             ║${NC}"
    echo -e "${GREEN}${BOLD}║                                                                  ║${NC}"
    echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BOLD}Sistema instalado:${NC} Kubernetes (Minikube)"
    echo -e "${BOLD}Coordinator:${NC} 1 pod (StatefulSet)"
    echo -e "${BOLD}Workers:${NC} 2 pods (StatefulSet)"
    echo -e "${BOLD}Alta disponibilidad:${NC} Habilitada"
    echo ""
    echo -e "${BOLD}📋 Comandos útiles:${NC}"
    echo ""
    echo -e "  ${CYAN}Conectarse a la base de datos:${NC}"
    echo "    psql -h localhost -p 5432 -U postgres -d hce_distribuida"
    echo "    (El port-forward ya está activo en background)"
    echo ""
    echo -e "  ${CYAN}Ver estado de pods:${NC}"
    echo "    kubectl get pods -l 'app in (citus-coordinator,citus-worker)'"
    echo ""
    echo -e "  ${CYAN}Ver logs:${NC}"
    echo "    kubectl logs -f citus-coordinator-0"
    echo ""
    echo -e "  ${CYAN}Ejecutar pruebas:${NC}"
    echo "    ./test_cluster.sh"
    echo "    ./test_high_availability.sh"
    echo ""
    echo -e "  ${CYAN}Limpiar todo:${NC}"
    echo "    ./cleanup.sh"
    echo ""
}

# Main - Selección de modo
case "$MODE" in
    compose)
        install_docker_compose
        ;;
    minikube)
        install_minikube
        ;;
    *)
        log_error "Modo desconocido: $MODE"
        echo ""
        echo "Uso: $0 [compose|minikube]"
        echo ""
        echo "  compose   - Despliega con Docker Compose (desarrollo rápido)"
        echo "  minikube  - Despliega con Minikube/Kubernetes (alta disponibilidad)"
        echo "  (sin argumentos) - Modo interactivo"
        exit 1
        ;;
esac
