# Scripts del Sistema FHIR Distribuido

Esta carpeta contiene todos los scripts necesarios para el despliegue, mantenimiento y desarrollo del Sistema FHIR Distribuido.

## 📁 Estructura de Scripts

```
scripts/
├── setup_system_compose.sh    # Instalación con Docker Compose
├── setup_system_minikube.sh   # Instalación con Kubernetes/Minikube
├── cleanup.sh                 # Limpieza completa del sistema
├── run_tests.sh              # Ejecución de pruebas
├── register_citus_k8s.sh     # Registro de nodos Citus en K8s
├── verify_lab.sh             # Verificación de instalación K8s
└── dev/                      # Scripts de desarrollo
    ├── install.sh            # Instalación de entorno de desarrollo
    └── start_server.sh       # Inicio de servidor de desarrollo
```

## 🚀 Scripts Principales

### `setup_system_compose.sh`
**Instalación con Docker Compose (Recomendado)**
- ✅ Instalación rápida y confiable
- ✅ Ideal para desarrollo y demostración
- ✅ Menor consumo de recursos
- ⏱️ Tiempo: 5-10 minutos

```bash
./setup_system_compose.sh
```

### `setup_system_minikube.sh`
**Instalación con Kubernetes/Minikube**
- ✅ Simula entorno de producción
- ✅ Alta disponibilidad y escalabilidad
- ✅ Ideal para aprendizaje de Kubernetes
- ⏱️ Tiempo: 10-15 minutos

```bash
./setup_system_minikube.sh
```

## 🧪 Scripts de Pruebas

### `run_tests.sh`
**Ejecución de pruebas del sistema**
- ✅ Pruebas unitarias y de integración
- ✅ Verificación de endpoints API
- ✅ Validación de base de datos

```bash
./run_tests.sh
```

### `verify_lab.sh`
**Verificación de instalación Kubernetes**
- ✅ Estado de pods y servicios
- ✅ Conectividad de base de datos
- ✅ Verificación de endpoints

```bash
./verify_lab.sh
```

## 🧹 Scripts de Limpieza

### `cleanup.sh`
**Limpieza completa del sistema**
- ✅ Eliminación de contenedores Docker
- ✅ Limpieza de recursos Kubernetes
- ✅ Eliminación de volúmenes y redes

```bash
./cleanup.sh
```

## ⚙️ Scripts de Desarrollo

### `dev/install.sh`
**Instalación de entorno de desarrollo**
- ✅ Creación de entorno virtual Python
- ✅ Instalación de dependencias
- ✅ Configuración de variables de entorno

```bash
./dev/install.sh
```

### `dev/start_server.sh`
**Inicio de servidor de desarrollo**
- ✅ Servidor FastAPI con recarga automática
- ✅ Configuración de desarrollo
- ✅ Hot-reload de cambios

```bash
./dev/start_server.sh
```

## 🔧 Scripts Especializados

### `register_citus_k8s.sh`
**Registro de nodos Citus en Kubernetes**
- ✅ Configuración automática de cluster Citus
- ✅ Registro de workers
- ✅ Verificación de conectividad

```bash
./register_citus_k8s.sh
```

## 📋 Uso Recomendado

1. **Para desarrollo local:**
   ```bash
   ./setup_system_compose.sh
   ```

2. **Para pruebas de producción:**
   ```bash
   ./setup_system_minikube.sh
   ```

3. **Para desarrollo de código:**
   ```bash
   ./dev/install.sh
   ./dev/start_server.sh
   ```

4. **Para ejecutar pruebas:**
   ```bash
   ./run_tests.sh
   ```

5. **Para limpiar el sistema:**
   ```bash
   ./cleanup.sh
   ```

## ⚠️ Notas Importantes

- Todos los scripts deben ejecutarse desde el directorio raíz del proyecto
- Verificar permisos de ejecución con `chmod +x script.sh` si es necesario
- Los scripts de desarrollo requieren Python 3.8+ instalado
- Los scripts de Kubernetes requieren `kubectl` y `minikube` instalados

## 📞 Soporte

Si encuentras problemas con algún script:
1. Verifica que estés en el directorio correcto
2. Comprueba los permisos de ejecución
3. Revisa los logs de salida para errores específicos
4. Consulta la documentación principal en `../README.md`