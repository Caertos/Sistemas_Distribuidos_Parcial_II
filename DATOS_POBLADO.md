# Poblado de Base de Datos - Sistema FHIR

## 🔄 Cambios Importantes

### ⚠️ Archivo `03-sample-data.sql` DEPRECADO

El archivo `postgres-citus/init/03-sample-data.sql` **ya NO se usa** para poblar la base de datos. Ha sido marcado como deprecado y ahora solo muestra mensajes informativos.

### ✅ Nuevo Sistema: Script `llenar.sh`

Ahora usamos el script `llenar.sh` que proporciona datos mucho más completos y coherentes:

## 📊 Datos Incluidos en `llenar.sh`

### 👥 Usuarios (22 total)
- **4 Administradores**: `admin`, `admin1`, `admin2` + original
- **1 Auditor**: `auditor`, `auditor1` 
- **6 Médicos**: `medico` + 5 especialistas (`cardiologo1`, `neurologo1`, `pediatra1`, `oncologo1`, `dermatologo1`)
- **11 Pacientes**: `paciente` + `paciente1` a `paciente10`

### 🏥 Datos Médicos Completos
- **15 Pacientes** con historiales completos
- **5 Profesionales médicos** especializados
- **13 Condiciones médicas** variadas
- **10 Medicamentos** con prescripciones
- **15 Encuentros médicos** de diferentes tipos
- **19 Observaciones médicas** (signos vitales, laboratorios)

## 🚀 Uso Durante la Instalación

### 1. Con `setup.sh`
```bash
./setup.sh compose
# Cuando pregunte: "¿Deseas poblar la base de datos con datos de ejemplo? (s/N):"
# Responder: S
```

### 2. Manual (después de la instalación)
```bash
./llenar.sh              # Modo interactivo
./llenar.sh --force      # Modo automático sin preguntas
```

## 🎯 Usuarios de Demostración

### Login con Datos Reales
El login ahora muestra usuarios específicos creados por `llenar.sh`:

| Usuario | Contraseña | Tipo | Descripción |
|---------|------------|------|-------------|
| `admin1` | `secret` | Administrador | Dr. Carlos Administrador |
| `cardiologo1` | `secret` | Médico | Dr. Juan Cardiólogo (con pacientes asignados) |
| `paciente1` | `secret` | Paciente | Ana García López (con historial cardiológico) |
| `auditor1` | `secret` | Auditor | Lic. María Auditora |

### 📋 Historial de Paciente1 (Ana García López)
- **Condición**: Insuficiencia cardíaca congestiva (moderada)
- **Medicamentos**: Enalapril 10mg, Furosemida 40mg
- **Encuentro**: Control cardiológico con Dr. Juan
- **Observaciones**: Presión arterial 140/90 mmHg

## 🔧 Características Técnicas

### Script `llenar.sh`
- ✅ Verificación de conexión a base de datos
- ✅ Detección de datos existentes
- ✅ Logging estructurado con timestamps
- ✅ Manejo de errores robusto
- ✅ Modo interactivo y automático
- ✅ Datos coherentes entre tablas relacionadas

### Archivo `03-sample-data.sql`
- ❌ **DEPRECADO** - No insertar datos
- ℹ️ Solo muestra mensajes informativos
- 🔄 Redirige al usuario a usar `llenar.sh`

## 🎯 Beneficios del Nuevo Sistema

1. **Datos Coherentes**: Relaciones consistentes entre usuarios, pacientes, médicos y historiales
2. **Más Completo**: 22 usuarios vs 4 anteriores, historiales médicos detallados
3. **Mejor Experiencia**: Usuarios específicos en login con nombres reales
4. **Dashboards Funcionales**: Cada tipo de usuario tiene datos relevantes para mostrar
5. **Mantenible**: Un solo script centralizado vs múltiples archivos SQL

## 🚨 Migración desde `03-sample-data.sql`

Si tenías datos del archivo antiguo:
1. El script `llenar.sh` detecta datos existentes
2. Pregunta si deseas continuar y agregar más datos
3. Usa `--force` para modo automático
4. Los datos nuevos se integran con los existentes

---

**Recomendación**: Siempre usar `llenar.sh` para poblar la base de datos. El archivo `03-sample-data.sql` permanece solo por compatibilidad pero no ejecuta código.