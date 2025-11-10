# Configuración del Sistema FHIR en Kubernetes
# =============================================

## 📋 Prerrequisitos

Antes de ejecutar el despliegue, asegúrate de tener instalado:

- Docker
- kubectl
- minikube
- curl (para verificaciones)

## 🚀 Despliegue Rápido

### Opción 1: Despliegue Completo Automático

```bash
cd k8s/
./setup_full_system.sh
```

Este script realiza automáticamente:
1. ✅ Verificación de dependencias
2. ✅ Configuración de Minikube
3. ✅ Construcción de imágenes Docker
4. ✅ Despliegue de base de datos Citus
5. ✅ Configuración de workers
6. ✅ Despliegue de FastAPI
7. ✅ Despliegue de Nginx
8. ✅ Población de datos de prueba
9. ✅ Configuración de acceso externo
10. ✅ Verificación del sistema

### Opción 2: Despliegue Manual Paso a Paso

```bash
# 1. Iniciar Minikube
minikube start --memory=6144 --cpus=3

# 2. Configurar docker para usar minikube
eval $(minikube docker-env)

# 3. Construir imágenes
docker build -t local/citus-custom:12.1 -f ../postgres-citus/Dockerfile ../postgres-citus/
docker build -t local/fastapi-fhir:latest -f ../fastapi-app/Dockerfile ../fastapi-app/
docker build -t local/nginx-fhir:latest -f ../nginx/Dockerfile ../nginx/

# 4. Desplegar Citus
kubectl apply -f secret-citus.yml
kubectl apply -f citus-coordinator.yml
kubectl apply -f citus-worker-statefulset.yml

# 5. Esperar y configurar workers
kubectl wait --for=condition=ready pod -l app=citus-coordinator --timeout=300s
./register_citus_k8s.sh --rebalance --drain

# 6. Desplegar aplicaciones
kubectl apply -f fastapi-deployment.yml
kubectl apply -f nginx-deployment.yml

# 7. Poblar datos
kubectl apply -f data-population-job.yml

# 8. Configurar acceso
kubectl port-forward svc/fastapi-app 8000:8000 &
minikube service fastapi-app-nodeport --url
```

## 🌐 Acceso a la Aplicación

### URLs de Acceso:
- **FastAPI (port-forward)**: http://localhost:8000
- **FastAPI (NodePort)**: `minikube service fastapi-app-nodeport --url`
- **Nginx (NodePort)**: `minikube service nginx-proxy --url`
- **Documentación API**: http://localhost:8000/docs
- **Login**: http://localhost:8000/login

### Credenciales:
| Usuario | Contraseña | Rol |
|---------|------------|-----|
| paciente | paciente123 | Paciente |
| medico | medico123 | Médico |
| admin | admin123 | Administrador |
| auditor | auditor123 | Auditor |

## 📊 Monitoreo y Diagnóstico

### Verificar Estado de Pods:
```bash
kubectl get pods -o wide
kubectl get services
```

### Ver Logs:
```bash
# Logs de FastAPI
kubectl logs -l app=fastapi-app -f

# Logs de Citus
kubectl logs -l app=citus-coordinator -f

# Logs del job de población
kubectl logs job/data-population-job
```

### Verificar Salud:
```bash
# Salud de FastAPI
curl http://localhost:8000/health

# Verificar base de datos
kubectl exec -it deployment/citus-coordinator -- psql -U postgres -d hce -c "SELECT COUNT(*) FROM paciente;"
```

## 🧹 Limpieza

### Limpieza Rápida (mantener cluster):
```bash
./cleanup_system.sh
```

### Limpieza Completa (eliminar cluster):
```bash
kubectl delete -f .
minikube delete
```

## 🔧 Configuración Avanzada

### Escalar FastAPI:
```bash
kubectl scale deployment fastapi-app --replicas=3
```

### Recursos Configurados:
- **FastAPI**: 2 réplicas, 256Mi-512Mi RAM, 250m-500m CPU
- **Citus Coordinator**: 1 réplica, 512Mi-1Gi RAM
- **Citus Workers**: 2 réplicas, 256Mi-512Mi RAM cada uno
- **Nginx**: 1 réplica, 64Mi-128Mi RAM

### Puertos:
- **FastAPI**: 30800 (NodePort)
- **Nginx**: 30080 (NodePort)
- **Citus**: 5432 (ClusterIP)

## 🐛 Troubleshooting

### Problemas Comunes:

1. **Pods en estado Pending**: Verificar recursos de Minikube
   ```bash
   minikube status
   kubectl describe node
   ```

2. **Imágenes no encontradas**: Asegurarse de usar el docker de minikube
   ```bash
   eval $(minikube docker-env)
   docker images | grep local/
   ```

3. **Base de datos no conecta**: Verificar que Citus esté running
   ```bash
   kubectl logs -l app=citus-coordinator
   kubectl exec -it deployment/citus-coordinator -- pg_isready
   ```

4. **FastAPI no responde**: Verificar variables de entorno
   ```bash
   kubectl describe pod -l app=fastapi-app
   kubectl logs -l app=fastapi-app
   ```

## 📈 Funcionalidades Incluidas

- ✅ Dashboard de pacientes profesional
- ✅ Sistema de autenticación JWT
- ✅ Agendamiento de citas médicas
- ✅ Descarga de historias clínicas en PDF
- ✅ API RESTful completa
- ✅ Base de datos distribuida (Citus)
- ✅ Escalabilidad horizontal
- ✅ Monitoreo y logs
- ✅ Datos de prueba pre-cargados