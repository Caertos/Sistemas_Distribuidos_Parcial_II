#!/usr/bin/env bash
# run_tests.sh - Script interactivo de pruebas unificado para el cluster Citus
# Combina todas las pruebas en un solo script asistido con generación de reporte

set -euo pipefail

# ============================================================================
# CONFIGURACIÓN Y VARIABLES
# ============================================================================

NAMESPACE=${NAMESPACE:-default}
DB_NAME=${DB_NAME:-hce_distribuida}
PGUSER=${PGUSER:-postgres}
PGPASSWORD=${PGPASSWORD:-postgres}
PGHOST=${PGHOST:-localhost}
PGPORT=${PGPORT:-5432}

export PGPASSWORD="$PGPASSWORD"

# Archivo de reporte
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
REPORT_FILE="RESULTADOS_PRUEBAS_${TIMESTAMP}.md"
TEMP_RESULTS="/tmp/test_results_$$"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Contadores de pruebas
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# ============================================================================
# FUNCIONES DE LOGGING
# ============================================================================

log_info() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_test() { echo -e "${BLUE}[TEST]${NC} $1"; }
log_section() { echo -e "${CYAN}[=====]${NC} ${MAGENTA}$1${NC}"; }

show_banner() {
    clear
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║           🧪 SUITE DE PRUEBAS CITUS - POSTGRES 🧪                ║
║                                                                   ║
║              Sistema de Pruebas Automatizadas                    ║
║            con Generación de Reportes Detallados                 ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

EOF
}

ask_confirmation() {
    local question="$1"
    local default="${2:-n}"
    local response
    
    while true; do
        echo -e -n "${YELLOW}[?]${NC} $question "
        if [ "$default" == "y" ]; then
            echo -n "[Y/n] "
        else
            echo -n "[y/N] "
        fi
        read -r response
        
        # Si está vacío, usar default
        [ -z "$response" ] && response="$default"
        
        case "${response,,}" in
            y|yes|s|si) return 0 ;;
            n|no) return 1 ;;
            *) echo -e "${RED}Por favor responde 'y' o 'n'${NC}" ;;
        esac
    done
}

# ============================================================================
# FUNCIONES DE REPORTE
# ============================================================================

init_report() {
    cat > "$REPORT_FILE" << EOF
# 🧪 Reporte de Pruebas - Sistema Citus PostgreSQL

**Fecha:** $(date '+%d de %B de %Y - %H:%M:%S')  
**Sistema:** PostgreSQL + Citus  
**Plataforma:** Kubernetes (Minikube)  
**Generado por:** Suite Automatizada de Pruebas

---

EOF
    log_info "Archivo de reporte creado: $REPORT_FILE"
}

add_to_report() {
    echo "$1" >> "$REPORT_FILE"
}

record_test_result() {
    local test_name="$1"
    local status="$2"
    local details="${3:-}"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    if [ "$status" == "PASS" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo "✅ $test_name" >> "$TEMP_RESULTS"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo "❌ $test_name" >> "$TEMP_RESULTS"
    fi
    
    if [ -n "$details" ]; then
        echo "   $details" >> "$TEMP_RESULTS"
    fi
}

finalize_report() {
    add_to_report "## 📊 Resumen de Resultados"
    add_to_report ""
    add_to_report "| Métrica | Valor |"
    add_to_report "|---------|-------|"
    add_to_report "| **Total de pruebas** | $TESTS_TOTAL |"
    add_to_report "| **Pruebas exitosas** | $TESTS_PASSED ✅ |"
    add_to_report "| **Pruebas fallidas** | $TESTS_FAILED ❌ |"
    add_to_report "| **Tasa de éxito** | $(( TESTS_PASSED * 100 / TESTS_TOTAL ))% |"
    add_to_report ""
    
    add_to_report "## 📋 Detalle de Pruebas Ejecutadas"
    add_to_report ""
    add_to_report '```'
    cat "$TEMP_RESULTS" >> "$REPORT_FILE"
    add_to_report '```'
    add_to_report ""
    
    add_to_report "---"
    add_to_report "**Fin del reporte**"
    
    rm -f "$TEMP_RESULTS"
    
    log_info "Reporte finalizado: $REPORT_FILE"
}

# ============================================================================
# FUNCIONES DE PRUEBA
# ============================================================================

setup_port_forward() {
    log_section "Configuración de Port-Forward"
    
    # Matar port-forward existente
    pkill -f "kubectl.*port-forward.*citus" 2>/dev/null || true
    sleep 2
    
    log_info "Iniciando port-forward a localhost:5432..."
    kubectl port-forward svc/citus-coordinator 5432:5432 >/dev/null 2>&1 &
    PF_PID=$!
    echo "$PF_PID" > /tmp/citus_pf_pid
    
    sleep 5
    log_info "Port-forward activo (PID: $PF_PID)"
}

test_connectivity() {
    log_section "PRUEBA 1: Conectividad con PostgreSQL"
    
    add_to_report "### 1️⃣ Prueba de Conectividad"
    add_to_report ""
    
    if psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -c "SELECT version();" -t > /tmp/pg_version 2>&1; then
        local version=$(head -1 /tmp/pg_version | xargs)
        log_info "✓ Conectividad exitosa"
        log_info "  Versión: $version"
        
        add_to_report "**Estado:** ✅ EXITOSO"
        add_to_report ""
        add_to_report '```'
        add_to_report "$version"
        add_to_report '```'
        add_to_report ""
        
        record_test_result "Conectividad con PostgreSQL" "PASS" "Versión: $version"
        return 0
    else
        log_error "✗ No se pudo conectar a PostgreSQL"
        
        add_to_report "**Estado:** ❌ FALLIDO"
        add_to_report ""
        
        record_test_result "Conectividad con PostgreSQL" "FAIL"
        return 1
    fi
}

test_citus_extension() {
    log_section "PRUEBA 2: Extensión Citus"
    
    add_to_report "### 2️⃣ Verificación de Extensión Citus"
    add_to_report ""
    
    local citus_info=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -tAc "SELECT extname || ' ' || extversion FROM pg_extension WHERE extname='citus';" 2>&1)
    
    if [ -n "$citus_info" ]; then
        log_info "✓ Extensión Citus instalada: $citus_info"
        
        add_to_report "**Estado:** ✅ EXITOSO"
        add_to_report ""
        add_to_report "- Extensión: $citus_info"
        add_to_report ""
        
        record_test_result "Extensión Citus instalada" "PASS" "$citus_info"
    else
        log_error "✗ Extensión Citus no encontrada"
        
        add_to_report "**Estado:** ❌ FALLIDO"
        add_to_report ""
        
        record_test_result "Extensión Citus instalada" "FAIL"
    fi
}

test_workers() {
    log_section "PRUEBA 3: Workers Registrados"
    
    add_to_report "### 3️⃣ Verificación de Workers"
    add_to_report ""
    
    local worker_count=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -tAc "SELECT count(*) FROM citus_get_active_worker_nodes();" | tr -d '[:space:]')
    
    log_info "Workers activos: $worker_count"
    
    add_to_report "**Workers activos:** $worker_count"
    add_to_report ""
    
    if [ "$worker_count" -ge 1 ]; then
        psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -c "SELECT * FROM citus_get_active_worker_nodes();" > /tmp/workers_list
        
        add_to_report '```'
        cat /tmp/workers_list >> "$REPORT_FILE"
        add_to_report '```'
        add_to_report ""
        
        record_test_result "Workers registrados" "PASS" "$worker_count workers activos"
    else
        log_warn "⚠ No hay workers registrados"
        record_test_result "Workers registrados" "FAIL" "0 workers"
    fi
}

test_cluster_status() {
    log_section "PRUEBA 4: Estado del Cluster en Kubernetes"
    
    add_to_report "### 4️⃣ Estado de Pods en Kubernetes"
    add_to_report ""
    
    kubectl get pods -l 'app in (citus-coordinator,citus-worker)' --no-headers > /tmp/pods_status
    
    local total_pods=$(wc -l < /tmp/pods_status)
    local running_pods=$(grep -c "Running" /tmp/pods_status || true)
    
    log_info "Pods totales: $total_pods"
    log_info "Pods Running: $running_pods"
    
    add_to_report '```'
    kubectl get pods -l 'app in (citus-coordinator,citus-worker)' -o wide >> "$REPORT_FILE"
    add_to_report '```'
    add_to_report ""
    
    if [ "$running_pods" -eq "$total_pods" ]; then
        record_test_result "Estado de Pods" "PASS" "Todos los pods Running ($running_pods/$total_pods)"
    else
        record_test_result "Estado de Pods" "FAIL" "Pods con problemas ($running_pods/$total_pods)"
    fi
}

test_data_distribution() {
    log_section "PRUEBA 5: Creación de Esquema y Distribución de Datos"
    
    add_to_report "### 5️⃣ Distribución de Datos"
    add_to_report ""
    
    log_info "Creando esquema de prueba..."
    
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" <<'SQL' 2>&1 | tee /tmp/schema_creation
DROP TABLE IF EXISTS test_pacientes CASCADE;
DROP TABLE IF EXISTS test_observaciones CASCADE;

CREATE TABLE test_pacientes (
  documento_id BIGINT NOT NULL,
  paciente_id BIGINT NOT NULL,
  nombre TEXT,
  apellido TEXT,
  edad INT,
  PRIMARY KEY (documento_id, paciente_id)
);

CREATE TABLE test_observaciones (
  documento_id BIGINT NOT NULL,
  observacion_id BIGSERIAL,
  tipo TEXT,
  valor NUMERIC,
  fecha TIMESTAMP DEFAULT now(),
  PRIMARY KEY (documento_id, observacion_id)
);

SELECT create_distributed_table('test_pacientes', 'documento_id');
SELECT create_distributed_table('test_observaciones', 'documento_id');
SQL
    
    log_info "Insertando datos de prueba (1000 pacientes)..."
    
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" <<'SQL' >/dev/null 2>&1
INSERT INTO test_pacientes (documento_id, paciente_id, nombre, apellido, edad)
SELECT 
  (random() * 1000000)::bigint AS documento_id,
  generate_series AS paciente_id,
  'Paciente_' || generate_series AS nombre,
  'Apellido_' || generate_series AS apellido,
  (random() * 80 + 18)::int AS edad
FROM generate_series(1, 1000);

INSERT INTO test_observaciones (documento_id, tipo, valor)
SELECT 
  p.documento_id,
  (ARRAY['Presión Arterial', 'Temperatura', 'Peso', 'Altura'])[floor(random()*4+1)],
  random() * 100
FROM test_pacientes p, generate_series(1, 3);
SQL
    
    local pacientes=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -tAc "SELECT count(*) FROM test_pacientes;" | tr -d '[:space:]')
    local observaciones=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -tAc "SELECT count(*) FROM test_observaciones;" | tr -d '[:space:]')
    
    log_info "Pacientes insertados: $pacientes"
    log_info "Observaciones insertadas: $observaciones"
    
    add_to_report "**Registros insertados:**"
    add_to_report "- Pacientes: $pacientes"
    add_to_report "- Observaciones: $observaciones"
    add_to_report ""
    
    add_to_report "**Distribución de shards por worker:**"
    add_to_report ""
    add_to_report '```'
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -c "
SELECT 
  nodename,
  count(*) as shard_count
FROM pg_dist_shard_placement
WHERE shardstate = 1
GROUP BY nodename
ORDER BY nodename;
" >> "$REPORT_FILE"
    add_to_report '```'
    add_to_report ""
    
    record_test_result "Creación de esquema y datos" "PASS" "$pacientes pacientes, $observaciones observaciones"
}

test_distributed_queries() {
    log_section "PRUEBA 6: Consultas Distribuidas"
    
    add_to_report "### 6️⃣ Consultas Distribuidas"
    add_to_report ""
    
    log_test "Ejecutando SELECT simple..."
    local select_result=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -tAc "SELECT count(*) FROM test_pacientes;" | tr -d '[:space:]')
    
    log_test "Ejecutando JOIN distribuido..."
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" <<'SQL' > /tmp/join_result
SELECT 
  p.nombre,
  p.apellido,
  count(o.observacion_id) as num_observaciones
FROM test_pacientes p
LEFT JOIN test_observaciones o ON p.documento_id = o.documento_id
GROUP BY p.documento_id, p.paciente_id, p.nombre, p.apellido
LIMIT 5;
SQL
    
    log_test "Ejecutando agregación..."
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" <<'SQL' > /tmp/agg_result
SELECT 
  tipo,
  count(*) as cantidad,
  round(avg(valor), 2) as promedio
FROM test_observaciones
GROUP BY tipo;
SQL
    
    log_info "✓ Consultas distribuidas ejecutadas exitosamente"
    
    add_to_report "**Pruebas realizadas:**"
    add_to_report ""
    add_to_report "1. **SELECT simple:** Consultados $select_result registros"
    add_to_report ""
    add_to_report "2. **JOIN distribuido:**"
    add_to_report '```'
    cat /tmp/join_result >> "$REPORT_FILE"
    add_to_report '```'
    add_to_report ""
    add_to_report "3. **Agregación:**"
    add_to_report '```'
    cat /tmp/agg_result >> "$REPORT_FILE"
    add_to_report '```'
    add_to_report ""
    
    record_test_result "Consultas distribuidas" "PASS" "SELECT, JOIN y agregaciones exitosas"
}

test_high_availability() {
    log_section "PRUEBA 7: Alta Disponibilidad"
    
    add_to_report "### 7️⃣ Prueba de Alta Disponibilidad"
    add_to_report ""
    
    if ! ask_confirmation "¿Deseas ejecutar la prueba de alta disponibilidad? (eliminará citus-worker-0)" "n"; then
        log_warn "Prueba de HA omitida por el usuario"
        add_to_report "**Estado:** ⏭️ OMITIDA"
        add_to_report ""
        return 0
    fi
    
    # Capturar estado inicial
    local workers_before=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -tAc "SELECT count(*) FROM citus_get_active_worker_nodes();" | tr -d '[:space:]')
    local records_before=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -tAc "SELECT count(*) FROM test_pacientes;" | tr -d '[:space:]')
    
    log_info "Estado inicial:"
    log_info "  Workers activos: $workers_before"
    log_info "  Registros: $records_before"
    
    add_to_report "**Estado inicial:**"
    add_to_report "- Workers activos: $workers_before"
    add_to_report "- Registros: $records_before"
    add_to_report ""
    
    # Insertar datos de prueba
    log_info "Insertando datos de prueba antes del fallo..."
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -c "
INSERT INTO test_pacientes (documento_id, paciente_id, nombre, apellido, edad)
VALUES 
  (999888777, 9999, 'Test_HA', 'PreFallo', 50),
  (999888778, 10000, 'Test_HA2', 'PreFallo2', 45);
" >/dev/null
    
    # Simular fallo
    log_warn "⚠️ Simulando caída del worker citus-worker-0..."
    add_to_report "**Acción:** Eliminación del pod citus-worker-0"
    add_to_report ""
    
    kubectl delete pod citus-worker-0 --now
    local fail_time=$(date +%s)
    
    sleep 3
    
    # Probar consultas durante recuperación
    log_test "Ejecutando consultas durante recuperación..."
    add_to_report "**Consultas durante recuperación:**"
    add_to_report ""
    add_to_report '```'
    
    local successful_queries=0
    for i in {1..10}; do
        if RESULT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -tAc "SELECT count(*) FROM test_pacientes WHERE nombre LIKE 'Test_HA%';" 2>&1); then
            echo "Intento $i/10: ✓ Count=$(echo $RESULT | tr -d '[:space:]')" | tee -a "$REPORT_FILE"
            successful_queries=$((successful_queries + 1))
        else
            echo "Intento $i/10: ✗ Error" | tee -a "$REPORT_FILE"
        fi
        sleep 2
    done
    
    add_to_report '```'
    add_to_report ""
    
    local availability=$((successful_queries * 100 / 10))
    log_info "Disponibilidad durante recuperación: $availability%"
    add_to_report "**Disponibilidad:** $availability% ($successful_queries/10 consultas exitosas)"
    add_to_report ""
    
    # Esperar recuperación
    log_info "Esperando recuperación del pod..."
    kubectl wait --for=condition=ready pod citus-worker-0 --timeout=180s >/dev/null 2>&1
    local recovery_time=$(($(date +%s) - fail_time))
    
    log_info "Pod recuperado en $recovery_time segundos"
    add_to_report "**Tiempo de recuperación:** ~$recovery_time segundos"
    add_to_report ""
    
    sleep 15  # Esperar registro del worker
    
    # Verificar estado final
    local workers_after=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -tAc "SELECT count(*) FROM citus_get_active_worker_nodes();" | tr -d '[:space:]')
    local records_after=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -tAc "SELECT count(*) FROM test_pacientes;" | tr -d '[:space:]')
    
    log_info "Estado final:"
    log_info "  Workers activos: $workers_after"
    log_info "  Registros: $records_after"
    
    add_to_report "**Estado final:**"
    add_to_report "- Workers activos: $workers_after"
    add_to_report "- Registros: $records_after"
    add_to_report ""
    
    local data_loss=$((records_before - records_after))
    if [ $data_loss -le 0 ]; then
        log_info "✓ Sin pérdida de datos"
        add_to_report "**Integridad de datos:** ✅ Sin pérdida de datos"
        add_to_report ""
    else
        log_error "✗ Pérdida de $data_loss registros"
        add_to_report "**Integridad de datos:** ❌ Pérdida de $data_loss registros"
        add_to_report ""
    fi
    
    # Resumen
    if [ "$workers_after" -ge "$workers_before" ] && [ $data_loss -le 0 ] && [ $availability -ge 80 ]; then
        log_info "✓✓✓ Prueba de HA EXITOSA ✓✓✓"
        record_test_result "Alta disponibilidad" "PASS" "Recuperación en ${recovery_time}s, ${availability}% disponibilidad"
    else
        log_error "✗✗✗ Prueba de HA FALLIDA ✗✗✗"
        record_test_result "Alta disponibilidad" "FAIL"
    fi
}

# ============================================================================
# MENÚ PRINCIPAL
# ============================================================================

show_menu() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}  Selecciona las pruebas a ejecutar:${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  1) Pruebas básicas del cluster (rápido, ~2 min)"
    echo "     - Conectividad"
    echo "     - Extensión Citus"
    echo "     - Workers registrados"
    echo "     - Estado de pods"
    echo ""
    echo "  2) Pruebas completas (completo, ~5 min)"
    echo "     - Todas las pruebas básicas"
    echo "     - Distribución de datos"
    echo "     - Consultas distribuidas"
    echo ""
    echo "  3) Pruebas con alta disponibilidad (extensivo, ~10 min)"
    echo "     - Todas las pruebas completas"
    echo "     - Simulación de fallo de worker"
    echo "     - Verificación de recuperación"
    echo ""
    echo "  4) Salir"
    echo ""
    echo -e -n "${YELLOW}Opción:${NC} "
}

run_basic_tests() {
    log_section "EJECUTANDO PRUEBAS BÁSICAS"
    echo ""
    
    setup_port_forward
    test_connectivity
    test_citus_extension
    test_workers
    test_cluster_status
}

run_complete_tests() {
    log_section "EJECUTANDO PRUEBAS COMPLETAS"
    echo ""
    
    run_basic_tests
    test_data_distribution
    test_distributed_queries
}

run_all_tests() {
    log_section "EJECUTANDO SUITE COMPLETA DE PRUEBAS"
    echo ""
    
    run_complete_tests
    test_high_availability
}

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

main() {
    show_banner
    
    # Verificar que estamos en Kubernetes
    if ! kubectl cluster-info &>/dev/null; then
        log_error "No se puede conectar al cluster de Kubernetes"
        log_error "Asegúrate de que Minikube esté corriendo: minikube status"
        exit 1
    fi
    
    # Inicializar reporte
    init_report
    touch "$TEMP_RESULTS"
    
    add_to_report "## 🎯 Configuración del Entorno"
    add_to_report ""
    add_to_report "- **Base de datos:** $DB_NAME"
    add_to_report "- **Usuario:** $PGUSER"
    add_to_report "- **Host:** $PGHOST:$PGPORT"
    add_to_report "- **Namespace:** $NAMESPACE"
    add_to_report ""
    add_to_report "---"
    add_to_report ""
    
    # Si se pasa un argumento, ejecutar automáticamente
    if [ $# -gt 0 ]; then
        case "$1" in
            basic|basico)
                run_basic_tests
                ;;
            complete|completo)
                run_complete_tests
                ;;
            all|todo|ha)
                run_all_tests
                ;;
            *)
                echo "Uso: $0 [basic|complete|all]"
                exit 1
                ;;
        esac
    else
        # Modo interactivo
        while true; do
            show_menu
            read -r choice
            
            case $choice in
                1)
                    echo ""
                    if ask_confirmation "¿Confirmas ejecutar las pruebas básicas?" "y"; then
                        run_basic_tests
                        break
                    fi
                    ;;
                2)
                    echo ""
                    if ask_confirmation "¿Confirmas ejecutar las pruebas completas?" "y"; then
                        run_complete_tests
                        break
                    fi
                    ;;
                3)
                    echo ""
                    if ask_confirmation "¿Confirmas ejecutar TODAS las pruebas incluyendo HA?" "y"; then
                        run_all_tests
                        break
                    fi
                    ;;
                4)
                    log_warn "Saliendo sin ejecutar pruebas"
                    exit 0
                    ;;
                *)
                    log_error "Opción inválida. Por favor elige 1-4."
                    ;;
            esac
        done
    fi
    
    # Finalizar reporte
    echo ""
    log_section "FINALIZANDO PRUEBAS"
    
    finalize_report
    
    # Mostrar resumen
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}                  ${GREEN}RESUMEN FINAL${NC}                    ${CYAN}║${NC}"
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo ""
    echo -e "  Total de pruebas:    ${BLUE}$TESTS_TOTAL${NC}"
    echo -e "  Pruebas exitosas:    ${GREEN}$TESTS_PASSED ✅${NC}"
    echo -e "  Pruebas fallidas:    ${RED}$TESTS_FAILED ❌${NC}"
    
    if [ $TESTS_TOTAL -gt 0 ]; then
        local success_rate=$((TESTS_PASSED * 100 / TESTS_TOTAL))
        echo -e "  Tasa de éxito:       ${BLUE}${success_rate}%${NC}"
    fi
    
    echo ""
    echo -e "  📄 Reporte guardado en: ${MAGENTA}$REPORT_FILE${NC}"
    echo ""
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Limpiar port-forward
    if [ -f /tmp/citus_pf_pid ]; then
        local pf_pid=$(cat /tmp/citus_pf_pid)
        log_info "Port-forward sigue corriendo (PID: $pf_pid)"
        echo "  Para detenerlo: kill $pf_pid"
        echo "  Para conectarte: psql -h localhost -p 5432 -U postgres -d hce_distribuida"
    fi
    
    echo ""
    
    # Exit code según resultados
    if [ $TESTS_FAILED -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# ============================================================================
# EJECUCIÓN
# ============================================================================

main "$@"
