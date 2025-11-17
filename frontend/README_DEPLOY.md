# Despliegue del Frontend Integrado en Kubernetes

## Arquitectura

El frontend está completamente integrado con el backend FastAPI:
- **Backend**: FastAPI sirve tanto la API REST (`/api/*`) como las páginas HTML del frontend
- **Frontend**: Templates Jinja2 + CSS + JavaScript vanilla (sin frameworks)
- **Despliegue**: Única imagen Docker que contiene backend + frontend

## Estructura de Archivos

```
backend/
  Dockerfile          → Construye imagen con backend + frontend
  src/
    main.py          → Configuración de rutas HTML y API
frontend/
  templates/         → Templates base (login.html, base.html)
  css/              → Estilos globales
  js/               → Lógica compartida (auth.js, dashboard.js)
  dashboards/       → Dashboards por rol
    admin/
      templates/    → admin.html
      css/          → Estilos específicos
      js/           → Lógica específica (admin.js)
    medic/
      templates/    → medic.html
      css/js/       → Estilos y lógica
    patient/
      templates/    → patient.html
      css/js/       → Estilos y lógica
```

## Rutas del Sistema

### Frontend (HTML)
- `/` → Redirección según rol o a `/login`
- `/login` → Página de login
- `/admin` → Dashboard de administrador
- `/medic` → Dashboard de médico/practitioner
- `/patient` → Dashboard de paciente
- `/dashboard` → Dashboard genérico (fallback)

### API REST
- `/api/auth/login` → Login (POST JSON)
- `/api/auth/refresh` → Renovar token
- `/api/auth/logout` → Cerrar sesión
- `/api/admin/*` → Endpoints de administración
- `/api/practitioner/*` → Endpoints para médicos
- `/api/patient/*` → Endpoints para pacientes
- `/health` → Health check

### Archivos Estáticos
- `/static/*` → CSS, JS, assets del frontend

## Funcionalidades por Rol

### Admin (`/admin`)
- Ver y gestionar usuarios
- Crear nuevos usuarios con roles
- Eliminar usuarios
- Ver métricas del sistema
- Gestionar infraestructura (próximamente)
- Ver logs de auditoría

**Endpoints usados:**
- `GET /api/admin/users` - Listar usuarios
- `POST /api/admin/users` - Crear usuario
- `DELETE /api/admin/users/{id}` - Eliminar usuario
- `GET /api/admin/monitor/metrics` - Métricas del sistema
- `GET /api/admin/monitor/audit` - Logs de auditoría

### Médico/Practitioner (`/medic`)
- Ver citas admitidas pendientes
- Ver información de pacientes asignados
- Acceder a historiales clínicos (próximamente)

**Endpoints usados:**
- `GET /api/practitioner/appointments?admitted=true` - Citas admitidas
- `GET /api/practitioner/patients/{id}` - Información de paciente

### Paciente (`/patient`)
- Ver próximas citas
- Agendar nuevas citas
- Cancelar citas
- Ver medicamentos activos
- Ver alergias registradas
- Ver resumen médico (próximamente)

**Endpoints usados:**
- `GET /api/patient/me/appointments` - Mis citas
- `POST /api/patient/me/appointments` - Crear cita
- `DELETE /api/patient/me/appointments/{id}` - Cancelar cita
- `GET /api/patient/me/medications` - Medicamentos
- `GET /api/patient/me/allergies` - Alergias
- `GET /api/patient/me/summary` - Resumen médico

## Flujo de Autenticación

1. Usuario accede a `/login`
2. Introduce credenciales (username/password)
3. Frontend hace `POST /api/auth/login` con JSON
4. Backend valida y devuelve:
   ```json
   {
     "access_token": "...",
     "refresh_token": "...",
     "role": "admin|practitioner|patient",
     "username": "..."
   }
   ```
5. Frontend guarda token y role en `localStorage`
6. Redirección automática según role:
   - `admin` → `/admin`
   - `practitioner`/`medic` → `/medic`
   - `patient` → `/patient`
7. Dashboards cargan datos desde API usando token en header `Authorization: Bearer <token>`

## Despliegue en Minikube

### Opción 1: Despliegue Completo (Recomendado)

```bash
# Desde la raíz del proyecto
./setup.sh
```

Este script ejecuta automáticamente:
1. **Paso 0**: Inicia Minikube
2. **Paso 1**: Despliega PostgreSQL + Citus
3. **Paso 2**: Despliega Backend (API)
4. **Paso 3**: Despliega Frontend integrado (reconstruye imagen con frontend)

### Opción 2: Solo Frontend (si Backend ya está desplegado)

```bash
# Desde la raíz del proyecto
./scripts/dev/3-DeployFrontend.sh clinical-database
```

Este script:
1. Construye imagen Docker con backend + frontend
2. Usa contexto desde raíz del proyecto
3. Carga imagen en Docker de Minikube
4. Aplica manifests de K8s
5. Reinicia deployment con nueva imagen
6. Verifica pods y servicios
7. Muestra URL de acceso

### Acceso al Sistema

Una vez desplegado, el script mostrará la URL de acceso. Puedes obtenerla también con:

```bash
# Obtener URL del servicio NodePort
minikube service backend-service -n clinical-database --url

# O hacer port-forward si es ClusterIP
kubectl port-forward -n clinical-database svc/backend-service 8000:8000
```

Luego accede a:
- Login: `http://<URL>/login`
- API Docs: `http://<URL>/docs`

## Desarrollo Local (sin Kubernetes)

### 1. Instalar dependencias

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Crear `backend/.env`:
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
JWT_SECRET=tu-secret-seguro
DEBUG=true
```

### 3. Levantar backend con frontend

```bash
cd backend
. .venv/bin/activate
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

Acceso: http://127.0.0.1:8000/login

## Verificación del Despliegue

```bash
# Ver pods
kubectl get pods -n clinical-database

# Ver logs del backend
kubectl logs -n clinical-database deployment/backend-deployment --tail=50 -f

# Ver servicios
kubectl get svc -n clinical-database

# Describir pod si hay problemas
kubectl describe pod -n clinical-database <pod-name>
```

## Troubleshooting

### Error: ImagePullBackOff
- La imagen no está en Docker de Minikube
- Solución: Ejecutar `scripts/dev/3-DeployFrontend.sh` para reconstruir

### Error: CrashLoopBackOff
- Verificar logs: `kubectl logs -n clinical-database <pod-name>`
- Problemas comunes:
  - Base de datos no disponible (verificar Citus)
  - Variables de entorno incorrectas (verificar ConfigMap/Secret)
  - Puerto ya en uso

### Frontend no carga o muestra 404
- Verificar que la carpeta `frontend` se copió en la imagen Docker
- Verificar logs del backend: debe mostrar "Mounting /static"
- Verificar que `main.py` tiene configuradas las rutas HTML

### Endpoints de API devuelven 401
- Token expirado o inválido
- Verificar que el middleware de auth permite las rutas públicas (`/login`, `/static`)
- Hacer logout y volver a iniciar sesión

### Redirección incorrecta tras login
- Verificar que `/api/auth/login` devuelve el campo `role`
- Verificar que `auth.js` guarda correctamente el role en localStorage
- Abrir DevTools del navegador → Console para ver errores JS

## Limpieza

```bash
# Eliminar recursos del namespace
kubectl delete namespace clinical-database

# O usar el script de limpieza
./scripts/dev/clean_env.sh

# Detener Minikube
minikube stop
```

## Próximas Mejoras

- [ ] Añadir refresh token automático antes de expiración
- [ ] Implementar WebSockets para notificaciones en tiempo real
- [ ] Añadir paginación en tablas de dashboards
- [ ] Mejorar manejo de errores con toasts/notifications
- [ ] Añadir loading states en botones y fetch
- [ ] Implementar modo offline con Service Workers
- [ ] Añadir tests E2E con Playwright/Cypress
- [ ] Configurar CI/CD con GitHub Actions

