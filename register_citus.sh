#!/usr/bin/env bash
# Script para registrar nodos worker en Citus Coordinator
# Uso: ./register_citus.sh

set -eu

# Nombre de la base de datos a usar por defecto. El usuario indica que usa `hce_distribuida`.
# Puede sobrescribirse exportando DB_NAME en el entorno antes de ejecutar el script.
DB_NAME=${DB_NAME:-hce_distribuida}

# Establece el hostname público del coordinator que los workers usarán para conectarse.
# Debe ser el nombre del servicio/contenedor accesible en la red de Docker Compose (por ejemplo: citus-coordinator).
set_coordinator_host() {
    local host_name=${1:-citus-coordinator}
    echo "Configurando coordinator hostname a: $host_name"
    if docker compose exec citus-coordinator psql -U postgres -d "$DB_NAME" -c "SELECT citus_set_coordinator_host('$host_name');"; then
        echo "Coordinator hostname establecido correctamente."
    else
        echo "Warning: no se pudo establecer citus_set_coordinator_host('$host_name')." >&2
    fi
}

# Registrar nodo worker en Citus Coordinator
register_worker() {
    local worker_name=$1
    echo "Registrando worker: $worker_name"
    # Usar citus_add_node en lugar de master_add_node (función moderna)
    if docker compose exec citus-coordinator psql -U postgres -d "$DB_NAME" -c "SELECT citus_add_node('$worker_name', 5432);"; then
        echo "Worker $worker_name registrado correctamente."
    else
        echo "Error registrando worker $worker_name (ver salida arriba)." >&2
    fi
}

# --- Flujo principal ---
# 1) Aseguramos que el coordinator exponga un hostname válido para que los workers puedan conectarse.
set_coordinator_host "citus-coordinator"


# 2) Asegurar que la base de datos existe en cada worker antes de registrar
ensure_db_on_worker() {
    local worker_name=$1
    echo "Asegurando existencia de la BD '$DB_NAME' en worker: $worker_name"
    if docker compose exec "$worker_name" psql -U postgres -c "CREATE DATABASE \"$DB_NAME\";"; then
        echo "BD '$DB_NAME' creada en $worker_name (o ya existía)."
    else
        echo "Advertencia: no se pudo crear/asegurar BD en $worker_name (ver salida)." >&2
    fi
}

# Crear la extensión citus en una base de datos concreta del host indicado
create_extension_on() {
    local host_name=$1
    local db_name=${2:-$DB_NAME}
    echo "Creando extensión citus en $host_name (BD: $db_name)"
    if docker compose exec "$host_name" psql -U postgres -d "$db_name" -c "CREATE EXTENSION IF NOT EXISTS citus;"; then
        echo "Extensión citus creada en $host_name/$db_name (o ya existía)."
    else
        echo "Error creando extensión citus en $host_name/$db_name (ver salida)." >&2
    fi
}

# Lista de workers presentes en docker-compose.yml
register_worker "citus-worker1"
register_worker "citus-worker2"

# Crear la BD en cada worker y luego registrarlos
ensure_db_on_worker "citus-worker1"
ensure_db_on_worker "citus-worker2"

# Crear extensiones en coordinator y workers
create_extension_on "citus-coordinator" "$DB_NAME"
create_extension_on "citus-worker1" "$DB_NAME"
create_extension_on "citus-worker2" "$DB_NAME"

# Registrar (se intenta registrar aunque la creación de la BD/extensiones pueda fallar)
register_worker "citus-worker1"
register_worker "citus-worker2"

# Ejecutar rebalance de shards para distribuir datos entre workers.
rebalance_shards() {
    echo "Iniciando rebalance de shards en el coordinator (puede tardar)."
    if docker compose exec citus-coordinator psql -U postgres -d "$DB_NAME" -c "SELECT rebalance_table_shards();"; then
        echo "Comando rebalance_table_shards() enviado correctamente."
    else
        echo "Error al ejecutar rebalance_table_shards() (ver salida)." >&2
    fi
}

# Argumentos: --rebalance para ejecutar rebalance automáticamente
DO_REBALANCE=false
DO_DRAIN=false
# Lista de tablas a forzar PK si es necesario, formato: tabla:col,tabla2:col2
# Se puede sobrescribir exportando PK_FIX_LIST antes de ejecutar el script.
PK_FIX_LIST=${PK_FIX_LIST:-"t_test:id"}
for arg in "$@"; do
    case "$arg" in
        --rebalance)
            DO_REBALANCE=true
            ;;
        --drain)
            DO_DRAIN=true
            ;;
        --help|-h)
            echo "Uso: $0 [--rebalance] [--drain] [--help]"
            echo "  --rebalance   Ejecutar SELECT rebalance_table_shards() al final del registro"
            echo "  --drain       Ejecutar SELECT citus_drain_node('citus-coordinator',5432) después del rebalance"
            echo "  PK_FIX_LIST   (env) Lista tabla:col separadas por comas para añadir PK si falta (ej: \"t_test:id,otra:pk\")"
            exit 0
            ;;
    esac
done

if [ "$DO_REBALANCE" = true ]; then
    rebalance_shards
else
    echo "Proceso de registro finalizado. Revise los mensajes anteriores para confirmar éxito/errores."
fi

# Opcional: drenar el coordinator para mover permanentemente shards a los workers.
drain_coordinator() {
    echo "Iniciando citus_drain_node('citus-coordinator',5432) (puede tardar)."
    if docker compose exec citus-coordinator psql -U postgres -d "$DB_NAME" -c "SELECT citus_drain_node('citus-coordinator',5432);"; then
        echo "Comando citus_drain_node enviado correctamente."
    else
        echo "Error al ejecutar citus_drain_node() (ver salida)." >&2
    fi
}

if [ "$DO_DRAIN" = true ]; then
    # si el usuario pidió drain pero no rebalance, avisar (drain funciona mejor tras rebalance)
    echo "--drain solicitado. Ejecutando drain en el coordinator..."
    drain_coordinator
fi

# Función para asegurar que una tabla tenga PRIMARY KEY. Se usa antes de drenar.
ensure_table_has_pk() {
    # args: table, column
    local table_name=$1
    local col_name=$2
    echo "Verificando PK en tabla $table_name (col: $col_name) en BD $DB_NAME"

    # Comprobar existencia de la tabla
    if ! docker compose exec citus-coordinator psql -U postgres -d "$DB_NAME" -tAc "SELECT 1 FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE c.relname='${table_name}' AND n.nspname NOT IN ('pg_catalog','information_schema');" | grep -q 1; then
        echo "Tabla $table_name no encontrada en $DB_NAME, omitida." >&2
        return
    fi

    # Comprobar si ya tiene PK
    has_pk=$(docker compose exec citus-coordinator psql -U postgres -d "$DB_NAME" -tAc "SELECT 1 FROM pg_constraint con JOIN pg_class c ON con.conrelid=c.oid WHERE c.relname='${table_name}' AND con.contype='p';" || true)
    if echo "$has_pk" | grep -q 1; then
        echo "La tabla $table_name ya tiene PRIMARY KEY."
        return
    fi

    # Comprobar si la columna existe
    col_exists=$(docker compose exec citus-coordinator psql -U postgres -d "$DB_NAME" -tAc "SELECT 1 FROM information_schema.columns WHERE table_name='${table_name}' AND column_name='${col_name}';" || true)
    if ! echo "$col_exists" | grep -q 1; then
        echo "La columna $col_name no existe en $table_name; no se puede crear PRIMARY KEY." >&2
        return
    fi

    # Intentar añadir PK
    echo "Añadiendo PRIMARY KEY ($col_name) a $table_name"
    if docker compose exec citus-coordinator psql -U postgres -d "$DB_NAME" -c "ALTER TABLE \"$table_name\" ADD PRIMARY KEY (\"$col_name\");"; then
        echo "PRIMARY KEY añadida a $table_name"
    else
        echo "Fallo al añadir PRIMARY KEY a $table_name (ver salida)." >&2
    fi
}

# Si se solicitó --drain, intentar arreglar tablas listadas en PK_FIX_LIST antes de drenar
if [ "$DO_DRAIN" = true ]; then
    IFS=',' read -ra pairs <<< "$PK_FIX_LIST"
    for p in "${pairs[@]}"; do
        table=${p%%:*}
        col=${p##*:}
        if [ -n "$table" ] && [ -n "$col" ]; then
            ensure_table_has_pk "$table" "$col"
        fi
    done
fi