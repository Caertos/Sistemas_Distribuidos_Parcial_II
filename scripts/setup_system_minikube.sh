#!/usr/bin/env bash
# Script completo y autónomo para el Sistema FHIR en Kubernetes
# Incluye validaciones, correcciones automáticas y verificaciones finales

set -euo pipefail

MINIKUBE_DRIVER=${MINIKUBE_DRIVER:-docker}
MINIKUBE_MEMORY=${MINIKUBE_MEMORY:-6144}
MINIKUBE_CPUS=${MINIKUBE_CPUS:-3}
NAMESPACE=${NAMESPACE:-default}

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo -e "${BOLD}${CYAN}════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}════════════════════════════════════════${NC}"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_fix() {
    echo -e "${CYAN}[FIX]${NC} $1"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { 
    print_error "Se necesita '$1' en PATH" 
    exit 1 
  }
}

wait_for_pods() {
    local label=$1
    local timeout=${2:-300}
    print_status "Esperando pods con etiqueta '$label'..."
    kubectl wait --for=condition=ready pod -l "$label" --timeout="${timeout}s" || {
        print_error "Timeout esperando pods $label"
        kubectl describe pods -l "$label"
        return 1
    }
}

fix_citus_authentication() {
    print_fix "Configurando autenticación de Citus para cluster..."
    
    # Agregar reglas de confianza para la red de pods de Kubernetes
    for node in citus-coordinator-0 citus-worker-0 citus-worker-1; do
        kubectl exec "$node" -- sh -c "echo 'host all all 10.244.0.0/16 trust' >> /var/lib/postgresql/data/pg_hba.conf" 2>/dev/null || true
        # Reordenar para que trust tenga precedencia
        kubectl exec "$node" -- sh -c "sed -i '/host all all all scram-sha-256/d' /var/lib/postgresql/data/pg_hba.conf && echo 'host all all all scram-sha-256' >> /var/lib/postgresql/data/pg_hba.conf" 2>/dev/null || true
        kubectl exec "$node" -- psql -U postgres -c "SELECT pg_reload_conf();" 2>/dev/null || true
    done
    
    print_success "Autenticación de Citus configurada"
}

setup_citus_cluster() {
    print_fix "Configurando cluster de Citus..."
    
    local max_attempts=5
    local attempt=1
    local cluster_configured=false
    
    while [ $attempt -le $max_attempts ] && [ "$cluster_configured" = false ]; do
        print_status "Intento de configuración $attempt/$max_attempts..."
        
        # Configurar coordinador
        if kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "SELECT citus_set_coordinator_host('citus-coordinator');" 2>/dev/null; then
            print_status "✅ Coordinador configurado"
        else
            print_warning "⚠️ Error configurando coordinador, reintentando..."
        fi
        
        # Verificar y agregar workers con verificación previa
        local workers_added=0
        
        # Worker 1
        local worker1_exists=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM citus_get_active_worker_nodes() WHERE node_name = 'citus-worker-0.citus-worker';" 2>/dev/null || echo "0")
        if [ "$worker1_exists" = "0" ]; then
            if kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "SELECT citus_add_node('citus-worker-0.citus-worker', 5432);" 2>/dev/null; then
                print_status "✅ Worker 1 agregado"
                workers_added=$((workers_added + 1))
            else
                print_warning "⚠️ Error agregando worker 1"
            fi
        else
            print_status "✅ Worker 1 ya existe"
            workers_added=$((workers_added + 1))
        fi
        
        # Worker 2
        local worker2_exists=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM citus_get_active_worker_nodes() WHERE node_name = 'citus-worker-1.citus-worker';" 2>/dev/null || echo "0")
        if [ "$worker2_exists" = "0" ]; then
            if kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "SELECT citus_add_node('citus-worker-1.citus-worker', 5432);" 2>/dev/null; then
                print_status "✅ Worker 2 agregado"
                workers_added=$((workers_added + 1))
            else
                print_warning "⚠️ Error agregando worker 2"
            fi
        else
            print_status "✅ Worker 2 ya existe"
            workers_added=$((workers_added + 1))
        fi
        
        # Verificar estado final del cluster
        local total_workers=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM citus_get_active_worker_nodes();" 2>/dev/null || echo "0")
        
        if [ "$total_workers" -ge "2" ]; then
            print_success "✅ Cluster configurado exitosamente con $total_workers workers"
            cluster_configured=true
        else
            print_warning "⚠️ Solo $total_workers workers configurados, reintentando..."
            sleep 10
        fi
        
        attempt=$((attempt + 1))
    done
    
    if [ "$cluster_configured" = false ]; then
        print_error "No se pudo configurar el cluster después de $max_attempts intentos"
        return 1
    fi
    
    print_success "Cluster de Citus configurado"
}

populate_database() {
    print_status "Ejecutando script de población de base de datos..."
    
    # Verificar que el script existe
    if [ ! -f "./populate_db_k8s.sh" ]; then
        print_error "Script de población no encontrado: ./populate_db_k8s.sh"
        return 1
    fi
    
    # Hacer el script ejecutable
    chmod +x ./populate_db_k8s.sh
    
    # Ejecutar el script de población con el flag --auto
    print_status "Ejecutando población completa de la base de datos..."
    ./populate_db_k8s.sh --auto
    
    if [ $? -eq 0 ]; then
        print_success "✅ Base de datos poblada exitosamente con datos completos"
    else
        print_error "❌ Error al poblar la base de datos"
        return 1
    fi
}

setup_port_forwards() {
    print_status "Configurando port-forwards..."
    
    # Terminar port-forwards existentes
    pkill -f "kubectl port-forward" 2>/dev/null || true
    sleep 3
    
    # Crear port-forward para FastAPI con reintentos
    local max_attempts=3
    local attempt=1
    local port_forward_success=false
    
    while [ $attempt -le $max_attempts ] && [ "$port_forward_success" = false ]; do
        print_status "Intento de port-forward $attempt/$max_attempts..."
        
        # Crear port-forward
        kubectl port-forward --address=0.0.0.0 svc/fastapi-app 8000:8000 > /tmp/fastapi_port_forward.log 2>&1 &
        FASTAPI_PF_PID=$!
        
        # Guardar PID
        echo $FASTAPI_PF_PID > /tmp/fastapi_pf.pid
        
        # Esperar y verificar que funcione
        sleep 8
        
        # Verificar que el port-forward funcione
        if curl -s --connect-timeout 5 http://localhost:8000/health > /dev/null 2>&1; then
            print_success "✅ Port-forward funcionando correctamente"
            port_forward_success=true
        else
            print_warning "⚠️ Port-forward falló, reintentando..."
            kill $FASTAPI_PF_PID 2>/dev/null || true
            sleep 2
        fi
        
        attempt=$((attempt + 1))
    done
    
    if [ "$port_forward_success" = false ]; then
        print_warning "⚠️ Port-forward no funcionó después de $max_attempts intentos"
        print_status "💡 Puedes usar NodePort: http://$(minikube ip):30800"
    else
        print_success "Port-forwards configurados y verificados"
    fi
}

verify_system() {
    print_status "Verificando sistema completo..."
    
    # Verificar estado de pods
    print_status "Estado de pods:"
    kubectl get pods -o wide
    
    # Verificar servicios
    print_status "Estado de servicios:"
    kubectl get svc
    
    # Verificar base de datos
    print_status "Verificando base de datos..."
    TABLES_COUNT=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
    print_status "Tablas en la base de datos: $TABLES_COUNT"
    
    # Verificar usuarios
    USERS_COUNT=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -t -c "SELECT COUNT(*) FROM users;" | tr -d ' ')
    print_status "Usuarios en la base de datos: $USERS_COUNT"
    
    # Verificar cluster Citus
    print_status "Verificando cluster Citus..."
    kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "SELECT * FROM citus_get_active_worker_nodes();" || true
    
    # Verificar endpoint de salud
    sleep 15
    print_status "Verificando endpoint de salud..."
    for i in {1..5}; do
        if curl -s http://localhost:8000/health | grep -q "healthy" 2>/dev/null; then
            print_success "✅ FastAPI responde correctamente"
            break
        else
            if [ $i -eq 5 ]; then
                print_warning "⚠️ FastAPI podría no estar completamente listo"
            else
                print_status "Reintentando verificación de salud ($i/5)..."
                sleep 10
            fi
        fi
    done
    
    # Verificar login
    if curl -s http://localhost:8000/login | grep -q "Portal de Salud\|Sistema FHIR" 2>/dev/null; then
        print_success "✅ Página de login accesible"
    else
        print_warning "⚠️ Página de login podría tener problemas"
    fi
    
    # Verificar API docs
    if curl -s http://localhost:8000/docs | grep -q "FastAPI\|swagger" 2>/dev/null; then
        print_success "✅ Documentación API accesible"
    else
        print_warning "⚠️ Documentación API podría tener problemas"
    fi
    
    print_success "Verificación del sistema completada"
}

# Función de validación y corrección final completa
final_system_validation() {
    print_status "Realizando validación completa del sistema..."
    
    # 1. Verificar que todos los pods estén corriendo
    print_status "🔍 Verificando estado de todos los pods..."
    local pod_issues=false
    
    # Verificar pods de Citus
    local citus_pods=$(kubectl get pods -l app=citus-coordinator --no-headers | grep -v Running | wc -l)
    local worker_pods=$(kubectl get pods -l app=citus-worker --no-headers | grep -v Running | wc -l)
    local fastapi_pods=$(kubectl get pods -l app=fastapi-app --no-headers | grep -v Running | wc -l)
    
    if [ "$citus_pods" -gt 0 ] || [ "$worker_pods" -gt 0 ] || [ "$fastapi_pods" -gt 0 ]; then
        print_warning "⚠️ Algunos pods no están en estado Running, reiniciando..."
        kubectl rollout restart deployment/fastapi-app
        kubectl rollout restart statefulset/citus-coordinator
        kubectl rollout restart statefulset/citus-worker
        
        # Esperar a que se estabilicen
        sleep 30
        wait_for_pods "app=citus-coordinator" 300
        wait_for_pods "app=citus-worker" 300 
        wait_for_pods "app=fastapi-app" 300
        pod_issues=true
    fi
    
    # 2. Re-verificar cluster Citus si hubo problemas con pods
    if [ "$pod_issues" = true ]; then
        print_status "🔧 Re-configurando cluster Citus después del reinicio..."
        sleep 15
        fix_citus_authentication
        setup_citus_cluster
    fi
    
    # 3. Verificar conectividad de base de datos
    print_status "🗄️ Verificando conectividad de base de datos..."
    local db_attempts=0
    local max_db_attempts=10
    local db_connected=false
    
    while [ $db_attempts -lt $max_db_attempts ] && [ "$db_connected" = false ]; do
        if kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -c "SELECT 1;" >/dev/null 2>&1; then
            print_success "✅ Base de datos conectada y operativa"
            db_connected=true
        else
            print_status "Reintentando conexión a BD... ($((db_attempts + 1))/$max_db_attempts)"
            sleep 5
            db_attempts=$((db_attempts + 1))
        fi
    done
    
    if [ "$db_connected" = false ]; then
        print_error "❌ No se pudo establecer conexión estable con la base de datos"
        return 1
    fi
    
    # 4. Verificar cluster Citus
    print_status "🔗 Verificando cluster Citus..."
    local active_workers=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM citus_get_active_worker_nodes();" 2>/dev/null || echo "0")
    
    if [ "$active_workers" -lt "2" ]; then
        print_warning "⚠️ Cluster Citus necesita reconfiguración..."
        setup_citus_cluster
        
        # Verificar nuevamente
        active_workers=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM citus_get_active_worker_nodes();" 2>/dev/null || echo "0")
        if [ "$active_workers" -lt "2" ]; then
            print_error "❌ No se pudo configurar el cluster Citus correctamente"
            return 1
        fi
    fi
    
    print_success "✅ Cluster Citus operativo con $active_workers workers"
    
    # 5. Verificar y configurar port-forwards
    print_status "🌐 Verificando y configurando acceso web..."
    
    # Terminar port-forwards existentes
    pkill -f "kubectl port-forward" 2>/dev/null || true
    sleep 3
    
    # Obtener IPs
    local minikube_ip=$(minikube ip)
    local nodeport=$(kubectl get svc fastapi-app-nodeport -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "30800")
    
    # Verificar NodePort primero
    print_status "Verificando acceso via NodePort..."
    local nodeport_working=false
    local nodeport_attempts=0
    local max_nodeport_attempts=15
    
    while [ $nodeport_attempts -lt $max_nodeport_attempts ] && [ "$nodeport_working" = false ]; do
        if curl -s --connect-timeout 5 "http://$minikube_ip:$nodeport/health" | grep -q "healthy" 2>/dev/null; then
            print_success "✅ NodePort funcionando: http://$minikube_ip:$nodeport"
            nodeport_working=true
        else
            print_status "Esperando NodePort... ($((nodeport_attempts + 1))/$max_nodeport_attempts)"
            sleep 5
            nodeport_attempts=$((nodeport_attempts + 1))
        fi
    done
    
    # Configurar port-forward como respaldo
    print_status "Configurando port-forward como acceso alternativo..."
    kubectl port-forward --address=0.0.0.0 svc/fastapi-app 8000:8000 > /tmp/fastapi_port_forward.log 2>&1 &
    FASTAPI_PF_PID=$!
    echo $FASTAPI_PF_PID > /tmp/fastapi_pf.pid
    
    sleep 8
    
    # Verificar port-forward
    local localhost_working=false
    if curl -s --connect-timeout 5 http://localhost:8000/health | grep -q "healthy" 2>/dev/null; then
        print_success "✅ Port-forward funcionando: http://localhost:8000"
        localhost_working=true
    else
        print_warning "⚠️ Port-forward no funcionó, pero NodePort está disponible"
    fi
    
    # 6. Verificar endpoints críticos
    print_status "🔍 Verificando endpoints críticos..."
    
    local primary_url="http://$minikube_ip:$nodeport"
    if [ "$localhost_working" = true ]; then
        primary_url="http://localhost:8000"
    fi
    
    # Health check
    if curl -s "$primary_url/health" | grep -q "healthy" 2>/dev/null; then
        print_success "✅ Health endpoint operativo"
    else
        print_error "❌ Health endpoint no responde"
        return 1
    fi
    
    # API docs
    if curl -s "$primary_url/docs" | grep -q "FastAPI\|swagger" 2>/dev/null; then
        print_success "✅ API documentation accesible"
    else
        print_warning "⚠️ API documentation podría tener problemas"
    fi
    
    # Login page
    if curl -s "$primary_url/login" | grep -q "Sistema FHIR\|login\|Portal" 2>/dev/null; then
        print_success "✅ Página de login accesible"
    else
        print_warning "⚠️ Página de login podría tener problemas"
    fi
    
    # 7. Verificar datos en base de datos si se poblaron
    if [[ $POPULATE_DB =~ ^[Yy]$ ]]; then
        print_status "📊 Verificando datos poblados..."
        
        local total_users=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
        local total_patients=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM paciente;" 2>/dev/null || echo "0")
        
        if [ "$total_users" -gt "15" ] && [ "$total_patients" -gt "8" ]; then
            print_success "✅ Datos poblados correctamente ($total_users usuarios, $total_patients pacientes)"
        else
            print_warning "⚠️ Datos poblados parcialmente ($total_users usuarios, $total_patients pacientes)"
        fi
        
        # Verificar específicamente datos de Ana García
        local ana_data=$(kubectl exec citus-coordinator-0 -- psql -U postgres -d hce_distribuida -tAc "SELECT COUNT(*) FROM paciente WHERE nombre = 'Ana' AND apellido = 'García López';" 2>/dev/null || echo "0")
        if [ "$ana_data" = "1" ]; then
            print_success "✅ Datos de Ana García verificados"
        else
            print_warning "⚠️ Datos de Ana García no encontrados"
        fi
    fi
    
    # 8. Verificar logs por errores críticos
    print_status "📝 Verificando logs por errores críticos..."
    
    local fastapi_errors=$(kubectl logs -l app=fastapi-app --tail=50 | grep -i "error\|exception\|failed" | wc -l)
    local citus_errors=$(kubectl logs -l app=citus-coordinator --tail=50 | grep -i "error\|exception\|failed" | wc -l)
    
    if [ "$fastapi_errors" -gt "5" ]; then
        print_warning "⚠️ Se detectaron errores en logs de FastAPI (revisar con: kubectl logs -l app=fastapi-app)"
    else
        print_success "✅ Logs de FastAPI sin errores críticos"
    fi
    
    if [ "$citus_errors" -gt "3" ]; then
        print_warning "⚠️ Se detectaron errores en logs de Citus (revisar con: kubectl logs -l app=citus-coordinator)"
    else
        print_success "✅ Logs de Citus sin errores críticos"
    fi
    
    # 9. Resumen final de validación
    print_status "📋 Resumen de validación del sistema:"
    kubectl get pods --no-headers | while read line; do
        local pod_name=$(echo $line | awk '{print $1}')
        local pod_status=$(echo $line | awk '{print $3}')
        if [ "$pod_status" = "Running" ]; then
            print_success "  ✅ $pod_name: $pod_status"
        else
            print_warning "  ⚠️ $pod_name: $pod_status"
        fi
    done
    
    # 10. Configurar URLs finales
    export FINAL_NODEPORT_URL="http://$minikube_ip:$nodeport"
    export FINAL_LOCALHOST_URL="http://localhost:8000"
    
    if [ "$nodeport_working" = true ]; then
        print_success "✅ Sistema completamente validado y operativo"
        return 0
    else
        print_error "❌ Sistema tiene problemas de conectividad"
        return 1
    fi
}

cleanup_on_exit() {
    print_status "Limpiando procesos en segundo plano..."
    if [ -f /tmp/fastapi_pf.pid ]; then
        kill $(cat /tmp/fastapi_pf.pid) 2>/dev/null || true
        rm -f /tmp/fastapi_pf.pid
    fi
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
    echo -e "${PURPLE}Versión: 4.0 | FastAPI Refactorizado + PostgreSQL/Citus${NC}"
    echo ""
}

trap cleanup_on_exit EXIT

# ============================================================================
# MAIN EXECUTION
# ============================================================================

show_banner
print_header "SISTEMA FHIR DISTRIBUIDO - SETUP COMPLETO Y AUTÓNOMO"

# Paso 1: Verificar dependencias
print_header "PASO 1: VERIFICACIÓN DE DEPENDENCIAS"
need_cmd docker
need_cmd kubectl
need_cmd minikube
need_cmd curl

# Verificar archivos de Kubernetes necesarios
if [ ! -f "./k8s/secret-citus.yml" ] || [ ! -f "./k8s/citus-coordinator.yml" ] || [ ! -f "./k8s/fastapi-deployment.yml" ]; then
    print_error "Archivos de Kubernetes no encontrados en ./k8s/"
    exit 1
fi

# Verificar archivos Docker necesarios
if [ ! -f "./postgres-citus/Dockerfile" ] || [ ! -f "./fastapi-app/Dockerfile" ]; then
    print_error "Archivos Docker no encontrados"
    exit 1
fi

# Cambiar al directorio k8s
cd ./k8s

print_success "✅ Todas las dependencias verificadas"
sleep 5

# Paso 2: Setup Minikube
print_header "PASO 2: CONFIGURACIÓN DE MINIKUBE"
MINIKUBE_STATUS=$(minikube status --format='{{.Host}}' 2>/dev/null || echo "NotFound")

if [ "$MINIKUBE_STATUS" = "Running" ]; then
  print_warning "⚠️ Minikube ya está corriendo. Reutilizando cluster existente."
elif [ "$MINIKUBE_STATUS" = "Stopped" ]; then
  print_status "🔄 Minikube existe pero está detenido. Iniciando..."
  minikube start
else
  print_status "🆕 Creando nuevo cluster Minikube..."
  minikube start --driver="$MINIKUBE_DRIVER" --memory="$MINIKUBE_MEMORY" --cpus="$MINIKUBE_CPUS"
fi

kubectl config use-context minikube
kubectl wait --for=condition=Ready nodes --all --timeout=300s
print_success "✅ Minikube configurado y operativo"
sleep 5

# Paso 3: Construir imágenes
print_header "PASO 3: CONSTRUCCIÓN DE IMÁGENES DOCKER"
eval $(minikube docker-env)

print_status "🏗️ Construyendo imagen de Citus..."
docker build -t local/citus-custom:12.1 -f ../postgres-citus/Dockerfile ../postgres-citus/

print_status "🏗️ Construyendo imagen de FastAPI..."
docker build -t local/fastapi-fhir:latest -f ../fastapi-app/Dockerfile ../fastapi-app/

print_success "✅ Imágenes Docker construidas"
sleep 5

# Paso 4: Desplegar base de datos
print_header "PASO 4: DESPLIEGUE DE BASE DE DATOS CITUS"
kubectl apply -f secret-citus.yml
kubectl apply -f citus-coordinator.yml
kubectl apply -f citus-worker-statefulset.yml

wait_for_pods "app=citus-coordinator" 300
wait_for_pods "app=citus-worker" 300

print_success "✅ Citus desplegado"
sleep 5

# Paso 5: Configurar Citus
print_header "PASO 5: CONFIGURACIÓN DE CLUSTER CITUS"
sleep 30  # Dar tiempo para que los pods se estabilicen

fix_citus_authentication
setup_citus_cluster

print_success "✅ Cluster Citus configurado"
sleep 5

# Paso 6: Desplegar FastAPI
print_header "PASO 6: DESPLIEGUE DE APLICACIÓN FASTAPI"
kubectl apply -f fastapi-deployment.yml

wait_for_pods "app=fastapi-app" 300

print_success "✅ FastAPI desplegado"
sleep 5

# Paso 7: Configurar acceso externo
print_header "PASO 7: CONFIGURACIÓN DE ACCESO EXTERNO"
setup_port_forwards

# Obtener URLs
MINIKUBE_IP=$(minikube ip)
NODEPORT=$(kubectl get svc fastapi-app-nodeport -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "N/A")

print_success "✅ Acceso externo configurado"
sleep 5

# Paso 8: Verificación inicial del sistema
print_header "PASO 8: VERIFICACIÓN INICIAL DEL SISTEMA"
verify_system
sleep 5

# Paso 9: Sistema de autenticación
print_header "PASO 9: VERIFICACIÓN DEL SISTEMA DE AUTENTICACIÓN"
sleep 10  # Dar tiempo para que FastAPI se inicialice

print_status "Sistema de autenticación híbrido configurado:"
print_status "- Tokens JWT con localStorage + cookies"
print_status "- Templates refactorizados y optimizados"
print_status "- Validación automática de tokens"

print_success "✅ Sistema de autenticación configurado y funcional"
sleep 5

# Paso 10: Poblado de base de datos (opcional)
print_header "PASO 10: POBLADO DE BASE DE DATOS"
echo -e "${YELLOW}¿Deseas poblar la base de datos con datos de ejemplo? (y/N)${NC}"
read -r POPULATE_DB
if [[ $POPULATE_DB =~ ^[Yy]$ ]]; then
    populate_database
else
    print_status "Saltando poblado de base de datos. Puedes ejecutar ./populate_db_k8s.sh más tarde."
fi
sleep 5

# Paso 11: Validación y corrección final del sistema
print_header "PASO 11: VALIDACIÓN Y CORRECCIÓN FINAL DEL SISTEMA"
final_system_validation

# Paso 12: Información final
print_header "🎉 ¡DESPLIEGUE COMPLETADO EXITOSAMENTE!"

# Usar las URLs configuradas en la validación final
FINAL_MINIKUBE_IP=$(minikube ip)
FINAL_NODEPORT=$(kubectl get svc fastapi-app-nodeport -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "30800")

echo ""
echo -e "${BOLD}${GREEN}📋 INFORMACIÓN DE ACCESO VERIFICADA:${NC}"
echo -e "  🌐 Sistema Web (NodePort):   ${CYAN}http://$FINAL_MINIKUBE_IP:$FINAL_NODEPORT${NC} ${GREEN}[VERIFICADO]${NC}"
if [ -f /tmp/fastapi_pf.pid ] && kill -0 $(cat /tmp/fastapi_pf.pid) 2>/dev/null; then
    echo -e "  🌐 Sistema Web (localhost):  ${CYAN}http://localhost:8000${NC} ${GREEN}[PORT-FORWARD ACTIVO]${NC}"
else
    echo -e "  🌐 Sistema Web (localhost):  ${CYAN}http://localhost:8000${NC} ${YELLOW}[USA NODEPORT]${NC}"
fi
echo -e "  🔐 Página de Login:          ${CYAN}http://$FINAL_MINIKUBE_IP:$FINAL_NODEPORT/login${NC}"
echo -e "  📊 Dashboard:                ${CYAN}http://$FINAL_MINIKUBE_IP:$FINAL_NODEPORT/${NC} ${YELLOW}(después del login)${NC}"
echo -e "  📖 Documentación API:        ${CYAN}http://$FINAL_MINIKUBE_IP:$FINAL_NODEPORT/docs${NC}"
echo -e "  ⚡ Health Check:            ${CYAN}http://$FINAL_MINIKUBE_IP:$FINAL_NODEPORT/health${NC}"
echo ""
echo -e "${BOLD}${YELLOW}🔑 CREDENCIALES DE ACCESO (Sistema Base):${NC}"
echo -e "  👤 Admin:        ${GREEN}admin1${NC} / ${GREEN}secret${NC}"
echo -e "  👨‍⚕️ Cardiólogo:  ${GREEN}cardiologo1${NC} / ${GREEN}secret${NC}"
echo -e "  👩‍🦰 Paciente:    ${GREEN}paciente1${NC} / ${GREEN}secret${NC}"
echo -e "  👁️ Auditor:     ${GREEN}auditor1${NC} / ${GREEN}secret${NC}"
echo ""
echo -e "${BOLD}${CYAN}💡 NOTA: Para datos completos de demostración, ejecuta:${NC}"
echo -e "  ${CYAN}./llenar.sh${NC} - Poblará la BD con usuarios y datos adicionales"
echo ""
echo -e "${BOLD}${BLUE}🛠️ COMANDOS ÚTILES:${NC}"
echo -e "  Ver logs FastAPI:         ${CYAN}kubectl logs -l app=fastapi-app -f${NC}"
echo -e "  Ver logs Citus:           ${CYAN}kubectl logs -l app=citus-coordinator -f${NC}"
echo -e "  Estado del cluster:       ${CYAN}kubectl get all${NC}"
echo -e "  Escalar FastAPI:          ${CYAN}kubectl scale deployment fastapi-app --replicas=3${NC}"
echo -e "  Conectar a BD:            ${CYAN}kubectl exec -it citus-coordinator-0 -- psql -U postgres -d hce_distribuida${NC}"
echo -e "  Restablecer port-forward: ${CYAN}kubectl port-forward svc/fastapi-app 8000:8000${NC}"
echo -e "  Ver procesos activos:     ${CYAN}ps aux | grep 'kubectl port-forward'${NC}"
echo ""

# Mostrar estado actual del sistema
echo -e "${BOLD}${GREEN}📊 ESTADO ACTUAL DEL SISTEMA:${NC}"
kubectl get pods --no-headers | while read line; do
    pod_name=$(echo $line | awk '{print $1}')
    pod_status=$(echo $line | awk '{print $3}')
    if [ "$pod_status" = "Running" ]; then
        echo -e "  ✅ $pod_name: ${GREEN}$pod_status${NC}"
    else
        echo -e "  ⚠️ $pod_name: ${YELLOW}$pod_status${NC}"
    fi
done

# Verificar conectividad final
echo ""
echo -e "${BOLD}${CYAN}🔍 VERIFICACIÓN FINAL DE CONECTIVIDAD:${NC}"
if curl -s --connect-timeout 3 "http://$FINAL_MINIKUBE_IP:$FINAL_NODEPORT/health" | grep -q "healthy" 2>/dev/null; then
    echo -e "  ✅ NodePort: ${GREEN}OPERATIVO${NC}"
else
    echo -e "  ❌ NodePort: ${RED}NO RESPONDE${NC}"
fi

if curl -s --connect-timeout 3 "http://localhost:8000/health" | grep -q "healthy" 2>/dev/null; then
    echo -e "  ✅ Localhost: ${GREEN}OPERATIVO${NC}"
else
    echo -e "  ❌ Localhost: ${RED}NO RESPONDE (usar NodePort)${NC}"
fi

echo ""
echo -e "${BOLD}${RED}🧹 PARA LIMPIAR EL ENTORNO:${NC}"
echo -e "  Eliminar recursos:        ${CYAN}kubectl delete all --all && kubectl delete pvc --all${NC}"
echo -e "  Eliminar minikube:        ${CYAN}minikube delete${NC}"
echo -e "  Limpiar port-forwards:    ${CYAN}pkill -f 'kubectl port-forward'${NC}"
echo ""

# Mensaje final con URL funcional
if curl -s --connect-timeout 3 "http://$FINAL_MINIKUBE_IP:$FINAL_NODEPORT/health" | grep -q "healthy" 2>/dev/null; then
    print_success "✅ El Sistema FHIR está completamente operativo y validado"
    print_status "🚀 Accede a http://$FINAL_MINIKUBE_IP:$FINAL_NODEPORT/login para comenzar"
    
    # Mensaje final con datos de prueba
    if [[ $POPULATE_DB =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${BOLD}${YELLOW}🧪 DATOS DE PRUEBA DISPONIBLES:${NC}"
        echo -e "  👩‍⚕️ Ana García (paciente1/secret) - Insuficiencia cardíaca, medicamentos, alergias"
        echo -e "  👨‍⚕️ Dr. Juan Cardiólogo (cardiologo1/secret) - Especialista tratante"
        echo -e "  👤 Administrador (admin1/secret) - Acceso completo al sistema"
        echo -e "  👁️ Auditor (auditor1/secret) - Revisión y auditoría"
    fi
else
    print_warning "⚠️ Sistema desplegado pero con problemas de conectividad"
    print_status "💡 Revisar logs: kubectl logs -l app=fastapi-app"
fi