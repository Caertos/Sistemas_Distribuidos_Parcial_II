#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
COMPOSE_FILE="$ROOT_DIR/docker-compose.e2e.yml"

echo "Starting DB for E2E (docker compose -f $COMPOSE_FILE up -d db)"
docker compose -f "$COMPOSE_FILE" up -d db

echo "Waiting for DB container to be healthy..."
# obtener el container id
DB_CID="$(docker compose -f "$COMPOSE_FILE" ps -q db)"
if [ -z "$DB_CID" ]; then
  echo "No DB container found. Exiting." >&2
  exit 1
fi

# esperar readiness
RETRIES=60
COUNT=0
until docker exec "$DB_CID" pg_isready -U test -d testdb >/dev/null 2>&1; do
  sleep 1
  COUNT=$((COUNT+1))
  if [ "$COUNT" -ge "$RETRIES" ]; then
    echo "DB did not become ready after $RETRIES seconds" >&2
    docker logs "$DB_CID" --tail 200
    exit 2
  fi
done

echo "DB ready. SQL init scripts from ./postgres-citus/init have been executed (if compatible)."

cat <<'EOF'
Next steps:
  1) Start the backend pointing to the DB created above. Example:
     DATABASE_URL=postgresql://test:test@localhost:5432/testdb uvicorn src.main:app --reload

  2) In another terminal, run the E2E pytest suite (requires E2E token):
     export E2E_BACKEND_URL=http://localhost:8000
     export E2E_PATIENT_TOKEN=<bearer-token-for-a-seeded-patient-or-mock>
     pytest backend/tests_e2e -q

Notes:
  - The init SQL may include Citus-specific statements. If you need Citus behavior, use a Citus image or adapt the SQL.
  - The E2E tests below are a skeleton that expects a valid Bearer token in E2E_PATIENT_TOKEN.
EOF
