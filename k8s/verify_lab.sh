#!/usr/bin/env bash
set -euo pipefail

# Verificación automática del laboratorio Citus desplegado en Minikube
# Genera un reporte JSON con PASS/FAIL y detalles en k8s/verify_report.json

NAMESPACE=${NAMESPACE:-default}
DB_NAME=${DB_NAME:-test_db}
PGUSER=${PGUSER:-postgres}
PGPASSWORD=${PGPASSWORD:-postgres}
PGHOST=${PGHOST:-localhost}
PGPORT=${PGPORT:-5432}
REPORT_FILE=${REPORT_FILE:-k8s/verify_report.json}

export PGPASSWORD="$PGPASSWORD"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "ERROR: se necesita '$1' en PATH" >&2; exit 1; }
}

need_cmd psql

CHECKS_JSON=""
ADD_COMMA=false
overall_status="PASS"

add_check() {
  local name="$1"; shift
  local status="$1"; shift
  local msg="$*"
  if [ "$ADD_COMMA" = true ]; then
    CHECKS_JSON=",${CHECKS_JSON}"
  fi
  # append JSON object (escape simple quotes)
  local obj="{\"name\":\"${name}\",\"status\":\"${status}\",\"message\":\"${msg//\"/\\\"}\"}"
  CHECKS_JSON="${CHECKS_JSON}${obj}"
  ADD_COMMA=true
  if [ "$status" != "PASS" ]; then
    overall_status="FAIL"
  fi
}

echo "1) Comprobando que la extensión 'citus' está instalada en la BD $DB_NAME..."
if psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -tAc "SELECT extname FROM pg_extension WHERE extname='citus';" | grep -q citus; then
  add_check "citus_extension" "PASS" "Extensión 'citus' encontrada en $DB_NAME"
  echo "  OK: extensión 'citus' encontrada."
else
  add_check "citus_extension" "FAIL" "Extensión 'citus' no encontrada en $DB_NAME"
  echo "  ERROR: la extensión 'citus' no se encontró en $DB_NAME." >&2
fi

echo "2) Verificando workers registrados (master_get_active_worker_nodes)..."
workers_out=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -tAc "SELECT count(*) FROM master_get_active_worker_nodes();" || true)
if echo "$workers_out" | grep -qE '^[[:space:]]*[0-9]+'; then
  add_check "workers_registered" "PASS" "Workers activos: ${workers_out//[[:space:]]/}"
  echo "  Workers activos: $workers_out"
else
  add_check "workers_registered" "FAIL" "No se pudieron listar workers: $workers_out"
  echo "  ERROR leyendo workers: $workers_out" >&2
fi

echo "3) Contando shards en pg_dist_shard..."
shards_out=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -tAc "SELECT count(*) FROM pg_dist_shard;" || true)
if echo "$shards_out" | grep -qE '^[[:space:]]*[0-9]+'; then
  add_check "shard_count" "PASS" "Shards: ${shards_out//[[:space:]]/}"
  echo "  Shards: $shards_out"
else
  add_check "shard_count" "FAIL" "No se pudo contar shards: $shards_out"
  echo "  ERROR contando shards: $shards_out" >&2
fi

echo "4) Prueba funcional: crear tabla distribuida, insertar y consultar"
if psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'; then
CREATE TABLE IF NOT EXISTS verify_students(id serial PRIMARY KEY, name text);
SELECT create_distributed_table('verify_students','id') WHERE NOT EXISTS (SELECT 1 FROM pg_dist_partition WHERE logicalrelid = 'verify_students'::regclass) ;
INSERT INTO verify_students(name) VALUES ('Alumno1'), ('Alumno2') ON CONFLICT DO NOTHING;
SELECT count(*) FROM verify_students;
SQL
  func_out=$(
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -tAc "SELECT count(*) FROM verify_students;" || true
  )
  if echo "$func_out" | grep -qE '^[[:space:]]*[0-9]+'; then
    add_check "functional_test" "PASS" "verify_students count: ${func_out//[[:space:]]/}"
    echo "  Prueba funcional OK: $func_out"
  else
    add_check "functional_test" "FAIL" "Prueba funcional falló: $func_out"
    echo "  ERROR en prueba funcional: $func_out" >&2
  fi
else
  add_check "functional_test" "FAIL" "Fallo al ejecutar SQL de prueba funcional"
  echo "  ERROR: fallo al ejecutar SQL de prueba funcional" >&2
fi

# Escribir reporte JSON
timestamp=$(date --iso-8601=seconds)
echo "{\"timestamp\":\"$timestamp\",\"status\":\"$overall_status\",\"checks\":[${CHECKS_JSON}] }" > "$REPORT_FILE"

if [ "$overall_status" = "PASS" ]; then
  echo "Verificación completada: PASS. Reporte: $REPORT_FILE"
  exit 0
else
  echo "Verificación completada: FAIL. Reporte: $REPORT_FILE" >&2
  exit 1
fi
