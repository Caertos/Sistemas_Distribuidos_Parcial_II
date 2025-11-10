#!/usr/bin/env bash
# Script de verificación completa del Sistema FHIR en Kubernetes

set -euo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✅ SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[❌ ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠️  WARNING]${NC} $1"
}

FAILED_TESTS=0

test_component() {
    local test_name="$1"
    local test_command="$2"
    
    print_status "Verificando: $test_name"
    
    if eval "$test_command" >/dev/null 2>&1; then
        print_success "$test_name"
        return 0
    else
        print_error "$test_name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

print_status "🔍 Iniciando verificación completa del Sistema FHIR"
echo ""

# 1. Verificar cluster Kubernetes
print_status "📋 1. Verificando cluster Kubernetes..."
test_component "Minikube está corriendo" "minikube status | grep -q 'Running'"
test_component "kubectl funciona" "kubectl cluster-info"
test_component "Nodos están listos" "kubectl get nodes | grep -q 'Ready'"

# 2. Verificar pods
print_status "📋 2. Verificando pods..."
test_component "Citus coordinator está listo" "kubectl get pod -l app=citus-coordinator | grep -q 'Running'"
test_component "Citus workers están listos" "kubectl get pod -l app=citus-worker | grep -q 'Running'"
test_component "FastAPI está listo" "kubectl get pod -l app=fastapi-app | grep -q 'Running'"
test_component "Nginx está listo" "kubectl get pod -l app=nginx-proxy | grep -q 'Running'"

# 3. Verificar servicios
print_status "📋 3. Verificando servicios..."
test_component "Servicio Citus coordinator existe" "kubectl get svc citus-coordinator"
test_component "Servicio FastAPI existe" "kubectl get svc fastapi-app"
test_component "Servicio FastAPI NodePort existe" "kubectl get svc fastapi-app-nodeport"
test_component "Servicio Nginx existe" "kubectl get svc nginx-proxy"

# 4. Verificar conectividad de base de datos
print_status "📋 4. Verificando base de datos..."
test_component "Base de datos acepta conexiones" "kubectl exec deployment/citus-coordinator -- pg_isready -U postgres"
test_component "Base de datos hce existe" "kubectl exec deployment/citus-coordinator -- psql -U postgres -lqt | cut -d \| -f 1 | grep -qw hce"

# 5. Verificar datos poblados
print_status "📋 5. Verificando datos poblados..."
test_component "Tabla paciente tiene datos" "kubectl exec deployment/citus-coordinator -- psql -U postgres -d hce -tAc 'SELECT COUNT(*) FROM paciente;' | grep -q '[1-9]'"
test_component "Tabla profesional tiene datos" "kubectl exec deployment/citus-coordinator -- psql -U postgres -d hce -tAc 'SELECT COUNT(*) FROM profesional;' | grep -q '[1-9]'"
test_component "Tabla users tiene datos" "kubectl exec deployment/citus-coordinator -- psql -U postgres -d hce -tAc 'SELECT COUNT(*) FROM users;' | grep -q '[1-9]'"

# 6. Verificar endpoints FastAPI (requiere port-forward activo)
FASTAPI_URL="http://localhost:8000"
if curl -s "$FASTAPI_URL/health" >/dev/null 2>&1; then
    print_status "📋 6. Verificando endpoints FastAPI (port-forward detectado)..."
    test_component "Health endpoint responde" "curl -s '$FASTAPI_URL/health' | grep -q 'healthy'"
    test_component "Login endpoint existe" "curl -s -o /dev/null -w '%{http_code}' '$FASTAPI_URL/login' | grep -q '200'"
    test_component "API docs accesible" "curl -s -o /dev/null -w '%{http_code}' '$FASTAPI_URL/docs' | grep -q '200'"
    
    # Test de autenticación
    TOKEN_RESPONSE=$(curl -s -X POST "$FASTAPI_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username": "paciente", "password": "paciente123"}' || echo "")
    
    if echo "$TOKEN_RESPONSE" | grep -q "success.*true"; then
        print_success "Autenticación funciona correctamente"
        
        # Extraer token para más pruebas
        TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])" 2>/dev/null || echo "")
        
        if [ -n "$TOKEN" ]; then
            test_component "Dashboard endpoint responde" "curl -s -H 'Authorization: Bearer $TOKEN' '$FASTAPI_URL/api/patient/dashboard' | grep -q 'patient_info'"
            test_component "Médicos disponibles endpoint responde" "curl -s -H 'Authorization: Bearer $TOKEN' '$FASTAPI_URL/api/patient/available-doctors' | grep -q 'doctors'"
        fi
    else
        print_error "Autenticación falló"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    print_warning "No se detectó port-forward para FastAPI. Omitiendo pruebas de endpoints."
    print_status "Para habilitar estas pruebas, ejecuta: kubectl port-forward svc/fastapi-app 8000:8000"
fi

# 7. Verificar recursos y salud general
print_status "📋 7. Verificando recursos del sistema..."
test_component "Pods sin reinicios excesivos" "! kubectl get pods | awk 'NR>1 {if(\$4>5) exit 1}'"
test_component "No hay pods en estado Error" "! kubectl get pods | grep -q 'Error'"
test_component "No hay pods en estado CrashLoopBackOff" "! kubectl get pods | grep -q 'CrashLoopBackOff'"

# 8. Verificar logs por errores críticos
print_status "📋 8. Verificando logs por errores..."
test_component "Logs FastAPI sin errores críticos" "! kubectl logs -l app=fastapi-app --tail=50 | grep -i 'critical\\|fatal'"
test_component "Logs Citus sin errores críticos" "! kubectl logs -l app=citus-coordinator --tail=50 | grep -i 'fatal\\|panic'"

# Resumen final
echo ""
print_status "📊 Resumen de verificación:"

if [ $FAILED_TESTS -eq 0 ]; then
    print_success "🎉 Todas las verificaciones pasaron correctamente!"
    print_status "El Sistema FHIR está funcionando perfectamente en Kubernetes"
    
    echo ""
    print_status "🌐 URLs de acceso:"
    FASTAPI_NODEPORT_URL=$(minikube service fastapi-app-nodeport --url 2>/dev/null || echo "No disponible")
    NGINX_NODEPORT_URL=$(minikube service nginx-proxy --url 2>/dev/null || echo "No disponible")
    
    echo "  📌 FastAPI (NodePort): $FASTAPI_NODEPORT_URL"
    echo "  📌 Nginx (NodePort): $NGINX_NODEPORT_URL"
    echo "  📌 FastAPI (port-forward): http://localhost:8000 (si está activo)"
    echo ""
    print_status "🔑 Credenciales:"
    echo "  👤 paciente/paciente123  👩‍⚕️ medico/medico123  👨‍💼 admin/admin123  🔍 auditor/auditor123"
    
    exit 0
else
    print_error "❌ $FAILED_TESTS verificación(es) fallaron"
    print_status "Revisa los componentes que fallaron y verifica los logs:"
    echo "  kubectl get pods -o wide"
    echo "  kubectl logs -l app=fastapi-app"
    echo "  kubectl logs -l app=citus-coordinator"
    echo "  kubectl describe pods"
    
    exit 1
fi