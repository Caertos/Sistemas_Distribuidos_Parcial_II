# Análisis, diseño y despliegue del repositorio: Sistema FHIR distribuido

**Autor:** Carlos Cochero Ramos  
**Ciudad, país:** Sincelejo, Colombia  
**Correo electrónico:** [cocheroc@gmail.com](mailto:cocheroc@gmail.com)

## Introducción

Este documento presenta un análisis técnico y académico del repositorio de trabajo del proyecto "Sistema FHIR distribuido". El objetivo es sintetizar la estructura del código, las decisiones tecnológicas, los procedimientos de despliegue en un entorno local con Kubernetes (Minikube), las pruebas realizadas y las implicaciones de seguridad de red relevantes para un laboratorio o un entorno de preproducción. 

## Elementos y conceptos para desarrollar la propuesta

### Resumen del repositorio

El repositorio contiene los componentes necesarios para el desarrollo, prueba y despliegue de un prototipo de sistema clínico basado en estándares FHIR. Su organización principal incluye carpetas para:

- `backend/`: código fuente de la API (FastAPI), rutas, middleware, modelos y pruebas unitarias y de integración.
- `frontend/`: plantillas Jinja2 y recursos estáticos (JS, CSS) para las vistas y dashboards.
- `k8s/`: manifiestos y scripts para despliegue en Kubernetes/Minikube (incluye ejemplos para Citus/Postgres y despliegue del backend y frontend).
- `postgres-citus/`: recursos e inicializadores para la base de datos distribuida (migraciones y scripts de inicialización).
- `scripts/`: utilidades y scripts de soporte (por ejemplo `bootup-clinical.sh`, `port-forward-backend.sh`).
- `tests/`, `tests_e2e/`, `tests_patient/`: suites de pruebas unitarias, de integración y E2E que cubren autenticación, flujo de admisión y endpoints de paciente/practitioner.
- `doc/`: documentación del proyecto y resultados de pruebas.
- `nginx/`, `nginx/Dockerfile`: recursos para servir frontends y ajustar proxy reverso en contenedores.

### Tecnologías y patrones observados

- Backend: FastAPI (Python), Jinja2 para templates, SQLAlchemy o consultas directas a la base de datos; middleware de autenticación y auditoría.
- Frontend: plantillas Jinja2 con JavaScript (vanilla) y Bootstrap 5 para layout y componentes UI.
- Persistencia: PostgreSQL con configuración para Citus (distribución horizontal) en `postgres-citus/` y scripts de migración e inicialización.
- Contenerización y orquestación: Docker, Minikube y Kubernetes (Deployments, Services, ConfigMaps, Secrets). Uso de `eval $(minikube docker-env)` para construir imágenes dentro del daemon de Minikube.
- Integración y pruebas: tests unitarios y E2E que ejercitan flujos de autenticación, admisión y comportamiento de endpoints críticos.
- Automatización local: scripts para poblar la base de datos (`k8s/1-CitusSql/populate_db_k8s.sh`) y scripts de arranque/redeploy (`scripts/bootup-clinical.sh`).

## Desarrollo

Este apartado describe la preparación de los entornos de hardware y software, los pasos de despliegue local observados, la configuración de red sugerida para entornos más complejos y las integraciones implementadas en el código.

### Preparación de hardware y software

- Requisitos mínimos recomendados: equipo con Linux, Docker instalado, Minikube y kubectl; aproximadamente 8 GB de RAM y CPU multicore para ejecutar Minikube con una base de datos y el backend sin contención severa.
- Entorno de desarrollo: uso de un entorno virtual Python para el backend (archivo de entorno sugerido en la raíz `.venv/` en sesiones previas) y dependencias listadas en `backend/requirements.txt`.
- Construcción de imagen para pruebas locales: se utiliza el Dockerfile en `backend/Dockerfile` y la práctica de apuntar el cliente Docker al daemon de Minikube mediante `eval $(minikube docker-env)`.

### Despliegue en Minikube (procedimiento usado en las pruebas)

Los pasos ejecutados para validar cambios en el repositorio y desplegar localmente incluyen:

1. Iniciar o preparar Minikube y apuntar el cliente Docker al demonio de Minikube:

```bash
minikube start --wait=all
eval $(minikube docker-env)
```

2. Construir la imagen local del backend y etiquetarla para uso en el cluster:

```bash
docker build -t backend-api:local -f backend/Dockerfile .
```

3. Aplicar manifiestos Kubernetes o reiniciar/forzar rollout del Deployment correspondiente:

```bash
kubectl -n clinical-database rollout restart deployment backend-deployment
kubectl -n clinical-database rollout status deployment backend-deployment --timeout=120s
```

4. Para pruebas rápidas en el equipo de desarrollo se usa `kubectl port-forward` hacia el servicio del backend y se accede via `http://localhost:<puerto>/` (ejemplo: `/medic`, `/health`).

### Configuración de la base de datos y poblamiento de datos

- El repositorio incluye un script de poblamiento para Kubernetes: `k8s/1-CitusSql/populate_db_k8s.sh`. El script inserta usuarios de prueba (administradores, personal de admisión, médicos y pacientes), encuentros, observaciones, signos vitales, alergias y citas, además de crear registros médicos y de profesionales. El script resulta útil para pruebas E2E en un cluster Minikube que contenga la imagen de Postgres/Citus.

### Ajustes en el código y compatibilidad

- Manejo de plantillas Jinja2: se agregó una plantilla base para evitar errores de `TemplateNotFound` y se revisaron las rutas de búsqueda de templates en el arranque del servidor.
- Contexto de usuario: se actualizó el paso de renderizado de algunas rutas frontend para pasar `user` (con campos mínimos) al contexto de Jinja2 y evitar errores por variables no definidas en las plantillas.
- Autenticación y token handling: el frontend se adaptó para tolerar distintos formatos de token (JWT estándar, envoltorios FHIR-<base64json> y base64 JSON). El middleware de autenticación del backend mantiene identidad mínima en `request.state.user` (user_id, role); si se requiere `full_name` u otros atributos, es necesario enriquecer el middleware o exponer un endpoint `/api/auth/me`.

### Seguridad de red, pfSense, firewall, NAT e IPsec (recomendaciones y consideraciones)

Para un laboratorio o despliegue distribuido, se recomiendan las siguientes prácticas, sin asumir configuraciones concretas no presentes en el repositorio:

- Segmentación de redes: separar la base de datos, backend y servicios públicos en zonas (por ejemplo DMZ y red interna) y aplicar reglas de acceso mínimas.
- pfSense / Firewall: ubicar un firewall en el borde para controlar NAT, reglas de entrada y salida y registros de auditoría. Limitar puertos expuestos y aplicar inspección estatal.
- NAT: aplicar NAT sólo cuando se requiera traducción entre redes; preferir load balancers y proxies inversos gestionados para exposición controlada de servicios.
- IPsec / VPN: usar túneles cifrados para interconexión entre sedes o para accesos remotos administrativos. En la configuración IPsec se debe establecer cifrados robustos, autenticación mutua y rotación de claves.
- Gestión de secretos: utilizar `Secrets` de Kubernetes o soluciones de vault para almacenar credenciales y evitar incrustar secretos en manifiestos.

> Nota: no se añadieron configuraciones de pfSense ni reglas de firewall exactas al repositorio; las recomendaciones anteriores sirven como guía para un despliegue seguro.

## Resultados

A partir de la implementación y las pruebas realizadas en entorno local, se obtuvieron los siguientes resultados observables:

- Rutas y templates: se resolvieron errores de renderizado causados por plantillas faltantes y por variables de contexto no definidas, permitiendo que la vista del dashboard médico (`/medic`) cargue correctamente tras los ajustes.
- Frontend: se implementó y/o ajustó la lógica para la cola de atención, con funcionalidades para listar citas del día, iniciar consultas (prellenado de modal) y cerrar citas desde la interfaz (con mecanismo optimista si el backend no persiste aún).
- Despliegue local: la construcción de la imagen usando el daemon de Minikube y el reinicio del deployment permitieron validar los cambios mediante `kubectl port-forward` y peticiones HTTP locales.
- Pruebas y datos: el script de poblamiento (`populate_db_k8s.sh`) facilita disponer de datos realistas (usuarios, pacientes, citas, encuentros, observaciones) para pruebas de integración.

Limitaciones detectadas:

- Algunos endpoints del backend para persistencia de recursos clínicos pueden estar sin implementar o servir como stubs (retornando 501), lo que impide una validación E2E completa sin mocks o implementación adicional.
- La variable `full_name` y otros atributos de usuario no siempre están disponibles en `request.state.user`; esto obliga a soluciones complementarias para mostrar nombres en templates.

## Conclusiones

El repositorio proporciona un punto de partida completo para el desarrollo de un sistema clínico basado en FHIR con componentes de backend, frontend, base de datos distribuida y manifiestos de orquestación. Las acciones realizadas permitieron validar la integración básica entre frontend y backend en un entorno local con Minikube, identificar puntos de fricción (plantillas, contexto de usuario, endpoints no implementados) y proponer mitigaciones.

Para avanzar hacia una solución de integración y validación continua se recomiendan las siguientes tareas prioritarias:

1. Implementar o mockear de forma robusta los endpoints del backend responsables de la creación y cierre de encuentros, observaciones y medicamentos para permitir pruebas E2E reproducibles.
2. Enriquecer el middleware de autenticación o exponer un endpoint `/api/auth/me` que devuelva atributos de usuario (p. ej. `full_name`) para mejorar la experiencia de la UI.
3. Incorporar pipelines de CI que ejecuten las pruebas unitarias e integración que ya existen en las carpetas `tests/` y `tests_e2e/`.
4. Documentar la configuración de red para entornos distribuidos (pfSense, reglas de firewall, NAT e IPsec) en archivos adicionales cuando se disponga del entorno y las políticas concretas.

## Anexos

### Anexo A — Ficheros y scripts relevantes

- `backend/` — servidor FastAPI, rutas y middleware.
- `frontend/` — plantillas y recursos estáticos (JS y CSS). Contiene implementaciones antiguas en `OLD/`.
- `k8s/` — manifiestos y scripts para Minikube/Kubernetes.
- `postgres-citus/` — configuración y scripts para Postgres + Citus.
- `k8s/1-CitusSql/populate_db_k8s.sh` — script para poblar la base de datos en un cluster Kubernetes (inserciones de usuarios, pacientes, encuentros, observaciones, signos vitales, alergias, medicamentos y citas).
- `scripts/bootup-clinical.sh` — script de utilidad para arrancar Minikube, reconstruir imágenes y reiniciar deployments.
- `tests/`, `tests_e2e/`, `tests_patient/` — suites de pruebas presentes en el repositorio.

### Anexo B — Comandos de referencia para despliegue y verificación local

```bash
# Preparar Minikube y apuntar Docker al daemon de Minikube
minikube start --wait=all
eval $(minikube docker-env)

# Construir imagen local
docker build -t backend-api:local -f backend/Dockerfile .

# Reiniciar deployment para que use la nueva imagen
kubectl -n clinical-database rollout restart deployment backend-deployment
kubectl -n clinical-database rollout status deployment backend-deployment --timeout=120s

# Abrir puerto local para pruebas
kubectl -n clinical-database port-forward svc/backend-service-nodeport 8000:8000
# Abrir en el navegador: http://localhost:8000/medic
```

## Referencias (formato APA 7)

Docker. (s.f.). Docker documentation. Recuperado de https://docs.docker.com/

Kubernetes. (s.f.). Kubernetes documentation. Recuperado de https://kubernetes.io/docs/

Minikube. (s.f.). Minikube — Run Kubernetes locally. Recuperado de https://minikube.sigs.k8s.io/

FastAPI. (s.f.). FastAPI — The modern, fast web framework for building APIs with Python. Recuperado de https://fastapi.tiangolo.com/

PostgreSQL Global Development Group. (s.f.). PostgreSQL documentation. Recuperado de https://www.postgresql.org/docs/

pfSense. (s.f.). pfSense documentation. Recuperado de https://docs.netgate.com/pfsense/

---

*Documento generado a partir del análisis del contenido del repositorio y de las acciones de prueba y despliegue realizadas en el entorno de desarrollo local.*