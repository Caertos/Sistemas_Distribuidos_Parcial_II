#!/bin/bash

# =============================================================================
# Setup FastAPI Application in Kubernetes
# Complete deployment script with namespace, secrets, and verification
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
APP_NAME="fastapi-fhir"
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

# Function to wait for pods to be ready
wait_for_pods() {
    local label_selector="$1"
    local timeout="${2:-300}"
    
    print_status "Waiting for pods with selector '$label_selector' to be ready..."
    
    if kubectl wait --for=condition=Ready pod \
        -l "$label_selector" \
        -n "$NAMESPACE" \
        --timeout="${timeout}s"; then
        print_success "All pods are ready"
    else
        print_error "Timeout waiting for pods to be ready"
        return 1
    fi
}

# Function to check service endpoints
check_service_endpoints() {
    local service_name="$1"
    
    print_status "Checking endpoints for service '$service_name'..."
    
    local endpoints=$(kubectl get endpoints "$service_name" -n "$NAMESPACE" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || echo "")
    
    if [[ -n "$endpoints" ]]; then
        print_success "Service '$service_name' has endpoints: $endpoints"
        return 0
    else
        print_warning "Service '$service_name' has no endpoints"
        return 1
    fi
}

# Function to build Docker image
build_docker_image() {
    print_status "Building Docker image for FastAPI application..."
    
    cd "$PROJECT_ROOT"
    if [[ -f "fastapi-app/Dockerfile" ]]; then
        if docker build -t fastapi-fhir:latest fastapi-app/; then
            print_success "Docker image built successfully"
        else
            print_error "Failed to build Docker image"
            exit 1
        fi
    else
        print_error "Dockerfile not found at fastapi-app/Dockerfile"
        exit 1
    fi
}

# Function to load image to minikube (if using minikube)
load_image_to_minikube() {
    if command -v minikube &> /dev/null && minikube status &> /dev/null; then
        print_status "Loading Docker image to minikube..."
        if minikube image load fastapi-fhir:latest; then
            print_success "Image loaded to minikube"
        else
            print_warning "Failed to load image to minikube"
        fi
    fi
}

# Function to create namespace
create_namespace() {
    print_status "Creating namespace '$NAMESPACE'..."
    
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        print_warning "Namespace '$NAMESPACE' already exists"
    else
        if kubectl create namespace "$NAMESPACE"; then
            print_success "Namespace '$NAMESPACE' created"
        else
            print_error "Failed to create namespace '$NAMESPACE'"
            exit 1
        fi
    fi
}

# Function to apply Kubernetes manifests
apply_manifests() {
    print_status "Applying Kubernetes manifests..."
    
    cd "$SCRIPT_DIR"
    
    # Apply FastAPI deployment
    if [[ -f "fastapi-deployment.yml" ]]; then
        if kubectl apply -f fastapi-deployment.yml; then
            print_success "FastAPI deployment applied"
        else
            print_error "Failed to apply FastAPI deployment"
            exit 1
        fi
    else
        print_error "FastAPI deployment manifest not found"
        exit 1
    fi
    
    # Apply Citus coordinator if exists
    if [[ -f "citus-coordinator.yml" ]]; then
        if kubectl apply -f citus-coordinator.yml; then
            print_success "Citus coordinator applied"
        else
            print_warning "Failed to apply Citus coordinator"
        fi
    fi
    
    # Apply Citus workers if exists
    if [[ -f "citus-worker-statefulset.yml" ]]; then
        if kubectl apply -f citus-worker-statefulset.yml; then
            print_success "Citus workers applied"
        else
            print_warning "Failed to apply Citus workers"
        fi
    fi
    
    # Apply secrets if exists
    if [[ -f "secret-citus.yml" ]]; then
        if kubectl apply -f secret-citus.yml; then
            print_success "Citus secrets applied"
        else
            print_warning "Failed to apply Citus secrets"
        fi
    fi
}

# Function to verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Wait for FastAPI pods
    if wait_for_pods "app=fastapi-fhir,component=api" 300; then
        print_success "FastAPI pods are ready"
    else
        print_error "FastAPI pods failed to start"
        return 1
    fi
    
    # Check FastAPI service
    if check_service_endpoints "fastapi-fhir-service"; then
        print_success "FastAPI service has endpoints"
    else
        print_warning "FastAPI service has no endpoints"
    fi
    
    # Check if Citus coordinator is running
    if kubectl get pods -n "$NAMESPACE" -l app=citus,component=coordinator &> /dev/null; then
        if wait_for_pods "app=citus,component=coordinator" 300; then
            print_success "Citus coordinator is ready"
        else
            print_warning "Citus coordinator failed to start"
        fi
    fi
    
    # Check if Citus workers are running
    if kubectl get pods -n "$NAMESPACE" -l app=citus,component=worker &> /dev/null; then
        if wait_for_pods "app=citus,component=worker" 300; then
            print_success "Citus workers are ready"
        else
            print_warning "Citus workers failed to start"
        fi
    fi
}

# Function to test API connectivity
test_api_connectivity() {
    print_status "Testing API connectivity..."
    
    # Get service external IP or use port-forward
    local service_ip=$(kubectl get service fastapi-fhir-service -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    
    if [[ -z "$service_ip" ]]; then
        print_warning "LoadBalancer IP not available, using port-forward for testing..."
        
        # Start port-forward in background
        kubectl port-forward service/fastapi-fhir-service 8080:80 -n "$NAMESPACE" &
        local port_forward_pid=$!
        
        # Wait a moment for port-forward to establish
        sleep 5
        
        # Test local connection
        if curl -s http://localhost:8080/health > /dev/null; then
            print_success "API is accessible via port-forward on http://localhost:8080"
            
            # Test specific endpoints
            print_status "Testing API endpoints..."
            curl -s http://localhost:8080/ | head -20
            echo ""
            
            print_status "API health check:"
            curl -s http://localhost:8080/health | jq . || curl -s http://localhost:8080/health
            echo ""
            
        else
            print_error "API is not accessible"
        fi
        
        # Clean up port-forward
        kill $port_forward_pid 2>/dev/null || true
        
    else
        print_success "LoadBalancer IP: $service_ip"
        
        # Test external connection
        if curl -s "http://$service_ip/health" > /dev/null; then
            print_success "API is accessible externally at http://$service_ip"
        else
            print_warning "API may not be ready yet at external IP"
        fi
    fi
}

# Function to show deployment status
show_status() {
    print_status "Deployment Status Summary:"
    echo "=========================="
    
    echo -e "\n${BLUE}Namespace:${NC}"
    kubectl get namespace "$NAMESPACE"
    
    echo -e "\n${BLUE}Pods:${NC}"
    kubectl get pods -n "$NAMESPACE" -o wide
    
    echo -e "\n${BLUE}Services:${NC}"
    kubectl get services -n "$NAMESPACE"
    
    echo -e "\n${BLUE}Deployments:${NC}"
    kubectl get deployments -n "$NAMESPACE"
    
    echo -e "\n${BLUE}ConfigMaps:${NC}"
    kubectl get configmaps -n "$NAMESPACE"
    
    echo -e "\n${BLUE}Secrets:${NC}"
    kubectl get secrets -n "$NAMESPACE"
    
    if kubectl get hpa -n "$NAMESPACE" &> /dev/null; then
        echo -e "\n${BLUE}Horizontal Pod Autoscalers:${NC}"
        kubectl get hpa -n "$NAMESPACE"
    fi
}

# Function to cleanup deployment
cleanup() {
    print_warning "Cleaning up deployment..."
    
    cd "$SCRIPT_DIR"
    
    # Delete all resources
    if [[ -f "fastapi-deployment.yml" ]]; then
        kubectl delete -f fastapi-deployment.yml --ignore-not-found=true
    fi
    
    if [[ -f "citus-coordinator.yml" ]]; then
        kubectl delete -f citus-coordinator.yml --ignore-not-found=true
    fi
    
    if [[ -f "citus-worker-statefulset.yml" ]]; then
        kubectl delete -f citus-worker-statefulset.yml --ignore-not-found=true
    fi
    
    if [[ -f "secret-citus.yml" ]]; then
        kubectl delete -f secret-citus.yml --ignore-not-found=true
    fi
    
    # Delete namespace (this will delete all resources in the namespace)
    kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
    
    print_success "Cleanup completed"
}

# Function to show help
show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy     - Deploy FastAPI application to Kubernetes (default)"
    echo "  build      - Build Docker image only"
    echo "  status     - Show deployment status"
    echo "  test       - Test API connectivity"
    echo "  cleanup    - Remove all deployed resources"
    echo "  help       - Show this help message"
    echo ""
    echo "Options:"
    echo "  --skip-build    - Skip Docker image build"
    echo "  --skip-verify   - Skip deployment verification"
    echo ""
    echo "Examples:"
    echo "  $0 deploy                    # Full deployment"
    echo "  $0 deploy --skip-build      # Deploy without building image"
    echo "  $0 status                   # Show current status"
    echo "  $0 cleanup                  # Remove everything"
}

# Main deployment function
main_deploy() {
    local skip_build=false
    local skip_verify=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-build)
                skip_build=true
                shift
                ;;
            --skip-verify)
                skip_verify=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    print_status "Starting FastAPI deployment to Kubernetes..."
    
    # Pre-flight checks
    check_command kubectl
    check_command docker
    check_k8s_connection
    
    # Build Docker image (unless skipped)
    if [[ "$skip_build" == "false" ]]; then
        build_docker_image
        load_image_to_minikube
    else
        print_warning "Skipping Docker image build"
    fi
    
    # Deploy to Kubernetes
    create_namespace
    apply_manifests
    
    # Verify deployment (unless skipped)
    if [[ "$skip_verify" == "false" ]]; then
        sleep 10  # Give pods time to start
        verify_deployment
        test_api_connectivity
    else
        print_warning "Skipping deployment verification"
    fi
    
    # Show final status
    show_status
    
    print_success "FastAPI deployment completed!"
    print_status "Access the API:"
    print_status "  - Locally: kubectl port-forward service/fastapi-fhir-service 8080:80 -n $NAMESPACE"
    print_status "  - Then visit: http://localhost:8080"
}

# Main script logic
case "${1:-deploy}" in
    deploy)
        shift
        main_deploy "$@"
        ;;
    build)
        check_command docker
        build_docker_image
        load_image_to_minikube
        ;;
    status)
        check_command kubectl
        check_k8s_connection
        show_status
        ;;
    test)
        check_command kubectl
        check_k8s_connection
        test_api_connectivity
        ;;
    cleanup)
        check_command kubectl
        check_k8s_connection
        cleanup
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