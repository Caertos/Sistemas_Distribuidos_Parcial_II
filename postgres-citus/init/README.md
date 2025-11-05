# Scripts de Inicialización PostgreSQL + Citus

Esta carpeta contiene los scripts SQL que se ejecutan automáticamente al inicializar PostgreSQL por primera vez (a través de `/docker-entrypoint-initdb.d/`).

## 📋 Orden de Ejecución

Los scripts se ejecutan en orden alfabético:

### 1️⃣ `01-extensions.sql`
**Propósito:** Crear extensiones necesarias y configuración inicial

**Acciones:**
- Crea extensión `citus` en la BD principal
- Crea extensión `pgcrypto` para generación de UUIDs
- Crea rol `hce_app` (usuario de aplicación)
- Crea base de datos `hce` para el esquema FHIR
- Instala extensiones en la BD `hce`

**Variables de entorno utilizadas:**
- `POSTGRES_DB` - Base de datos principal (default: `hce_distribuida`)

---

### 2️⃣ `02-schema-fhir.sql`
**Propósito:** Crear el esquema de base de datos FHIR distribuido

**Tablas creadas:**

#### Tablas Distribuidas (por `documento_id`)
- **`paciente`** - Información demográfica de pacientes
- **`encuentro`** - Consultas/encuentros médicos
- **`observacion`** - Observaciones clínicas (signos vitales, etc.)
- **`condicion`** - Diagnósticos y condiciones médicas

#### Tablas Replicadas (en todos los nodos)
- **`profesional`** - Catálogo de profesionales de salud

**Características:**
- ✅ PKs compuestas incluyendo `documento_id` (requisito de Citus)
- ✅ Índices optimizados para consultas comunes
- ✅ Funciones modernas de Citus (`create_distributed_table`)
- ✅ Co-location de datos por paciente (mismo `documento_id`)

---

### 3️⃣ `03-sample-data.sql` (Opcional)
**Propósito:** Insertar datos de ejemplo para pruebas

**Datos insertados:**
- 5 profesionales de salud
- 5 pacientes de ejemplo
- 5 encuentros médicos
- 9 observaciones clínicas
- 3 condiciones/diagnósticos

**Nota:** Usa `ON CONFLICT DO NOTHING` para evitar errores en reinicios.

---

## 🔧 Uso

### En Docker Compose
Los scripts se ejecutan automáticamente al crear el contenedor por primera vez:

```bash
docker compose up -d
```

### En Kubernetes
La imagen personalizada incluye estos scripts:

```bash
# Construir imagen
docker build -t local/citus-custom:12.1 -f postgres-citus/Dockerfile postgres-citus/

# Los scripts se ejecutan al inicializar el pod
```

### Manualmente (para desarrollo)
```bash
# Conectarse a la BD
psql -h localhost -p 5432 -U postgres -d hce_distribuida

# Ejecutar scripts en orden
\i postgres-citus/init/01-extensions.sql
\i postgres-citus/init/02-schema-fhir.sql
\i postgres-citus/init/03-sample-data.sql
```

---

## ⚠️ Notas Importantes

### Primary Keys en Tablas Distribuidas
Citus requiere que las PKs incluyan la columna de distribución:

```sql
-- ✅ CORRECTO
PRIMARY KEY (documento_id, paciente_id)

-- ❌ INCORRECTO (fallará)
PRIMARY KEY (paciente_id)
```

### Columna de Distribución
Todas las tablas distribuidas usan `documento_id` como columna de partición:
- Agrupa todos los datos de un paciente en el mismo shard
- Permite JOINs eficientes entre tablas relacionadas
- Mejora el rendimiento de queries por paciente

### Orden de Creación
1. Primero crear las tablas (con PKs compuestas)
2. Luego distribuirlas con `create_distributed_table()`
3. Finalmente crear índices

---

## 🔍 Verificación

### Verificar extensiones
```sql
SELECT extname, extversion FROM pg_extension WHERE extname='citus';
```

### Verificar tablas distribuidas
```sql
SELECT logicalrelid::regclass AS tabla, partkey 
FROM pg_dist_partition 
ORDER BY logicalrelid::text;
```

### Verificar distribución de shards
```sql
SELECT 
  logicalrelid::regclass AS tabla,
  count(*) AS num_shards
FROM pg_dist_shard
GROUP BY logicalrelid;
```

### Verificar workers
```sql
SELECT * FROM citus_get_active_worker_nodes();
```

---

## 📚 Recursos

- [Documentación Citus](https://docs.citusdata.com/)
- [FHIR Resources](https://www.hl7.org/fhir/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Última actualización:** 5 de noviembre de 2025  
**Versión:** PostgreSQL 16.6 + Citus 12.1
