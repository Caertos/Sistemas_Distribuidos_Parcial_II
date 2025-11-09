#!/bin/bash

# =============================================================================
# Complete Kubernetes Setup Script
# Sets up the entire FHIR system including Citus cluster and FastAPI application
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="fhir-system"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Function to print colored output
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

# Function to check if command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is not installed or not in PATH"
        exit 1
    fi
}

# Function to check Kubernetes connectivity
check_k8s_connection() {
    print_status "Checking Kubernetes connection..."
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster"
        print_error "Please ensure kubectl is configured and cluster is accessible"
        exit 1
    fi
    print_success "Connected to Kubernetes cluster"
}

# Function to setup minikube if needed
setup_minikube() {
    if [[ "${USE_MINIKUBE:-}" == "true" ]]; then
        print_status "Setting up minikube..."
        
        if [[ -f "$SCRIPT_DIR/setup_minikube.sh" ]]; then
            if bash "$SCRIPT_DIR/setup_minikube.sh"; then
                print_success "Minikube setup completed"
            else
                print_error "Minikube setup failed"
                return 1
            fi
        else
            print_warning "Minikube setup script not found"
        fi
    fi
}

# Function to deploy Citus cluster
deploy_citus_cluster() {
    print_status "Deploying Citus cluster..."
    
    # Apply Citus secrets
    if [[ -f "$SCRIPT_DIR/secret-citus.yml" ]]; then
        if kubectl apply -f "$SCRIPT_DIR/secret-citus.yml"; then
            print_success "Citus secrets applied"
        else
            print_error "Failed to apply Citus secrets"
            return 1
        fi
    fi
    
    # Apply Citus coordinator
    if [[ -f "$SCRIPT_DIR/citus-coordinator.yml" ]]; then
        if kubectl apply -f "$SCRIPT_DIR/citus-coordinator.yml"; then
            print_success "Citus coordinator deployed"
        else
            print_error "Failed to deploy Citus coordinator"
            return 1
        fi
    fi
    
    # Apply Citus workers
    if [[ -f "$SCRIPT_DIR/citus-worker-statefulset.yml" ]]; then
        if kubectl apply -f "$SCRIPT_DIR/citus-worker-statefulset.yml"; then
            print_success "Citus workers deployed"
        else
            print_error "Failed to deploy Citus workers"
            return 1
        fi
    fi
    
    # Wait for Citus coordinator to be ready
    print_status "Waiting for Citus coordinator to be ready..."
    if kubectl wait --for=condition=Ready pod -l app=citus,component=coordinator -n "$NAMESPACE" --timeout=300s; then
        print_success "Citus coordinator is ready"
    else
        print_error "Citus coordinator failed to start"
        return 1
    fi
    
    # Wait for Citus workers to be ready
    print_status "Waiting for Citus workers to be ready..."
    if kubectl wait --for=condition=Ready pod -l app=citus,component=worker -n "$NAMESPACE" --timeout=300s; then
        print_success "Citus workers are ready"
    else
        print_error "Citus workers failed to start"
        return 1
    fi
}

# Function to register Citus cluster
register_citus_cluster() {
    print_status "Registering Citus cluster..."
    
    if [[ -f "$SCRIPT_DIR/register_citus_k8s.sh" ]]; then
        if bash "$SCRIPT_DIR/register_citus_k8s.sh"; then
            print_success "Citus cluster registered successfully"
        else
            print_warning "Citus cluster registration may have failed"
        fi
    else
        print_warning "Citus registration script not found"
    fi
}

# Function to deploy FastAPI application
deploy_fastapi() {
    print_status "Deploying FastAPI application..."
    
    if [[ -f "$SCRIPT_DIR/setup_fastapi_k8s.sh" ]]; then
        # Use the dedicated FastAPI setup script with specific options
        if bash "$SCRIPT_DIR/setup_fastapi_k8s.sh" deploy --skip-verify; then
            print_success "FastAPI application deployed"
        else
            print_error "FastAPI deployment failed"
            return 1
        fi
    else
        print_error "FastAPI setup script not found"
        return 1
    fi
}

# Function to verify complete deployment
verify_complete_deployment() {
    print_status "Verifying complete deployment..."
    
    # Check all pods are running
    print_status "Checking pod status..."
    kubectl get pods -n "$NAMESPACE" -o wide
    
    # Check services
    print_status "Checking services..."
    kubectl get services -n "$NAMESPACE"
    
    # Wait for all pods to be ready
    print_status "Waiting for all pods to be ready..."
    if kubectl wait --for=condition=Ready pod --all -n "$NAMESPACE" --timeout=300s; then
        print_success "All pods are ready"
    else
        print_warning "Some pods may not be ready"
    fi
    
    # Test API connectivity if FastAPI is deployed
    if kubectl get deployment fastapi-fhir -n "$NAMESPACE" &> /dev/null; then
        print_status "Testing API connectivity..."
        
        # Port-forward for testing
        kubectl port-forward service/fastapi-fhir-service 8080:80 -n "$NAMESPACE" &
        local port_forward_pid=$!
        
        sleep 5
        
        if curl -s http://localhost:8080/health > /dev/null; then
            print_success "API is accessible and healthy"
            
            # Show API info
            print_status "API Documentation available at:"
            print_status "  http://localhost:8080/docs (Swagger UI)"
            print_status "  http://localhost:8080/redoc (ReDoc)"
            
        else
            print_warning "API health check failed"
        fi
        
        # Clean up port-forward
        kill $port_forward_pid 2>/dev/null || true
    fi
}

# Function to run verification tests
run_verification_tests() {
    print_status "Running verification tests..."
    
    if [[ -f "$SCRIPT_DIR/verify_lab.sh" ]]; then
        if bash "$SCRIPT_DIR/verify_lab.sh"; then
            print_success "Verification tests passed"
        else
            print_warning "Some verification tests may have failed"
        fi
    else
        print_warning "Verification script not found"
    fi
}

# Function to show deployment summary
show_deployment_summary() {
    print_status "Deployment Summary"
    echo "=================="
    
    echo -e "\n${BLUE}Cluster Information:${NC}"
    kubectl cluster-info
    
    echo -e "\n${BLUE}Namespace: $NAMESPACE${NC}"
    kubectl get namespace "$NAMESPACE"
    
    echo -e "\n${BLUE}Pods:${NC}"
    kubectl get pods -n "$NAMESPACE" -o wide
    
    echo -e "\n${BLUE}Services:${NC}"
    kubectl get services -n "$NAMESPACE"
    
    echo -e "\n${BLUE}Persistent Volumes:${NC}"
    kubectl get pv | grep "$NAMESPACE" || echo "No persistent volumes found"
    
    echo -e "\n${BLUE}Persistent Volume Claims:${NC}"
    kubectl get pvc -n "$NAMESPACE" || echo "No PVCs found"
    
    # Show access information
    echo -e "\n${BLUE}Access Information:${NC}"
    echo "==================="
    
    # FastAPI Service
    local fastapi_ip=$(kubectl get service fastapi-fhir-service -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [[ -n "$fastapi_ip" ]]; then
        echo "FastAPI External Access: http://$fastapi_ip"
    else
        echo "FastAPI Local Access: kubectl port-forward service/fastapi-fhir-service 8080:80 -n $NAMESPACE"
        echo "Then visit: http://localhost:8080"
    fi
    
    # Citus Service
    local citus_ip=$(kubectl get service citus-coordinator-service -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [[ -n "$citus_ip" ]]; then
        echo "Citus External Access: $citus_ip:5432"
    else
        echo "Citus Local Access: kubectl port-forward service/citus-coordinator-service 5432:5432 -n $NAMESPACE"
    fi
    
    echo -e "\n${BLUE}Useful Commands:${NC}"
    echo "================="
    echo "View logs: kubectl logs -f deployment/fastapi-fhir -n $NAMESPACE"
    echo "Scale app: kubectl scale deployment/fastapi-fhir --replicas=5 -n $NAMESPACE"
    echo "Delete all: kubectl delete namespace $NAMESPACE"
    echo "Shell access: kubectl exec -it deployment/fastapi-fhir -n $NAMESPACE -- /bin/bash"
}

# Function to cleanup everything
cleanup_all() {
    print_warning "Cleaning up complete deployment..."
    
    # Use FastAPI cleanup if available
    if [[ -f "$SCRIPT_DIR/setup_fastapi_k8s.sh" ]]; then
        bash "$SCRIPT_DIR/setup_fastapi_k8s.sh" cleanup
    fi
    
    # Delete namespace (this removes everything)
    kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
    
    print_success "Complete cleanup finished"
}

# Function to show help
show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  full        - Complete deployment (Citus + FastAPI) [default]"
    echo "  citus       - Deploy only Citus cluster"
    echo "  fastapi     - Deploy only FastAPI application"
    echo "  verify      - Verify deployment and run tests"
    echo "  status      - Show deployment status"
    echo "  cleanup     - Remove all deployed resources"
    echo "  help        - Show this help message"
    echo ""
    echo "Options:"
    echo "  --use-minikube     - Setup and use minikube"
    echo "  --skip-tests       - Skip verification tests"
    echo "  --skip-build       - Skip Docker image build"
    echo ""
    echo "Environment Variables:"
    echo "  USE_MINIKUBE=true  - Use minikube for deployment"
    echo "  NAMESPACE          - Kubernetes namespace (default: fhir-system)"
    echo ""
    echo "Examples:"
    echo "  $0 full                      # Complete deployment"
    echo "  $0 full --use-minikube      # Deploy with minikube"
    echo "  $0 citus                    # Deploy only database"
    echo "  $0 fastapi --skip-build     # Deploy API without building"
    echo "  $0 verify                   # Run tests only"
    echo "  $0 cleanup                  # Remove everything"
}

# Main function for full deployment
main_full_deployment() {
    local use_minikube=false
    local skip_tests=false
    local skip_build=false
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --use-minikube)
                use_minikube=true
                export USE_MINIKUBE=true
                shift
                ;;
            --skip-tests)
                skip_tests=true
                shift
                ;;
            --skip-build)
                skip_build=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    print_status "Starting complete FHIR system deployment..."
    
    # Pre-flight checks
    check_command kubectl
    check_command docker
    
    # Setup minikube if requested
    if [[ "$use_minikube" == "true" ]]; then
        setup_minikube
    fi
    
    check_k8s_connection
    
    # Create namespace
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy components
    deploy_citus_cluster
    register_citus_cluster
    
    # Deploy FastAPI with appropriate options
    local fastapi_options=""
    if [[ "$skip_build" == "true" ]]; then
        fastapi_options="--skip-build"
    fi
    
    if [[ -f "$SCRIPT_DIR/setup_fastapi_k8s.sh" ]]; then
        bash "$SCRIPT_DIR/setup_fastapi_k8s.sh" deploy $fastapi_options
    else
        print_error "FastAPI setup script not found"
        exit 1
    fi
    
    # Verify deployment
    verify_complete_deployment
    
    # Run tests if not skipped
    if [[ "$skip_tests" == "false" ]]; then
        run_verification_tests
    fi
    
    # Show summary
    show_deployment_summary
    
    print_success "Complete FHIR system deployment finished!"
}

# Main script logic
case "${1:-full}" in
    full)
        shift
        main_full_deployment "$@"
        ;;
    citus)
        check_command kubectl
        check_k8s_connection
        kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
        deploy_citus_cluster
        register_citus_cluster
        ;;
    fastapi)
        shift
        check_command kubectl
        check_k8s_connection
        kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
        
        if [[ -f "$SCRIPT_DIR/setup_fastapi_k8s.sh" ]]; then
            bash "$SCRIPT_DIR/setup_fastapi_k8s.sh" deploy "$@"
        else
            print_error "FastAPI setup script not found"
            exit 1
        fi
        ;;
    verify)
        check_k8s_connection
        verify_complete_deployment
        run_verification_tests
        ;;
    status)
        check_k8s_connection
        show_deployment_summary
        ;;
    cleanup)
        check_k8s_connection
        cleanup_all
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac