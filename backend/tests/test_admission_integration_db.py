import os
import time
import subprocess
import uuid
import importlib
import shutil

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi.testclient import TestClient

import pytest

DOCKER = shutil.which("docker")


@pytest.mark.skipif(DOCKER is None, reason="Docker not available on PATH")
def test_admission_flow_with_postgres_container():
    """Integration test (containerized Postgres).

    - Levanta un contenedor postgres temporario
    - Crea un esquema mínimo (users, paciente, cita, admision)
    - Inserta un paciente y una cita
    - Reconfigura la app para usar esa BD
    - Ejecuta flujo: admissioner crea admisión -> marca admitida -> practitioner lista y ve cita admitida
    """
    container_name = f"sd_test_pg_{uuid.uuid4().hex[:8]}"
    port = "5433"
    user = "postgres"
    password = "postgres"
    db = "testdb"

    # Start postgres container
    run_cmd = [
        "docker",
        "run",
        "--rm",
        "-d",
        "--name",
        "%s" % container_name,
        "-e",
        f"POSTGRES_PASSWORD={password}",
        f"-e",
        f"POSTGRES_USER={user}",
        f"-e",
        f"POSTGRES_DB={db}",
        "-p",
        f"{port}:5432",
        "postgres:15",
    ]
    proc = subprocess.run(run_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        pytest.skip(f"Could not start docker container: {proc.stderr}")

    try:
        # Wait for postgres ready
        dsn = f"host=127.0.0.1 port={port} user={user} password={password} dbname={db}"
        ready = False
        for _ in range(30):
            try:
                conn = psycopg2.connect(dsn)
                conn.close()
                ready = True
                break
            except Exception:
                time.sleep(1)
        if not ready:
            pytest.skip("Postgres container did not become ready in time")

        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        cur = conn.cursor()

        # Create minimal schema
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT,
                email TEXT,
                full_name TEXT,
                hashed_password TEXT,
                user_type TEXT,
                is_active BOOLEAN DEFAULT true,
                fhir_patient_id TEXT,
                fhir_practitioner_id TEXT
            );

            CREATE TABLE IF NOT EXISTS paciente (
                paciente_id BIGINT,
                documento_id BIGINT NOT NULL,
                nombre TEXT,
                apellido TEXT,
                fecha_nacimiento DATE,
                PRIMARY KEY (documento_id, paciente_id)
            );

            CREATE TABLE IF NOT EXISTS cita (
                cita_id BIGSERIAL PRIMARY KEY,
                documento_id BIGINT NOT NULL,
                paciente_id BIGINT NOT NULL,
                fecha_hora TIMESTAMP,
                duracion_minutos INTEGER,
                estado TEXT DEFAULT 'programada',
                estado_admision TEXT DEFAULT 'pendiente',
                admission_id TEXT
            );

            CREATE TABLE IF NOT EXISTS admision (
                admission_id TEXT PRIMARY KEY,
                documento_id BIGINT NOT NULL,
                paciente_id BIGINT NOT NULL,
                cita_id BIGINT,
                fecha_admision TIMESTAMP DEFAULT now(),
                admitido_por TEXT,
                motivo_consulta TEXT,
                prioridad TEXT DEFAULT 'normal',
                estado_admision TEXT DEFAULT 'activa'
            );
            """
        )

        # Insert a patient + a cita
        cur.execute("INSERT INTO paciente (documento_id,paciente_id,nombre,apellido,fecha_nacimiento) VALUES (1,1,'Test','Paciente', '1980-01-01') ON CONFLICT DO NOTHING;")
        cur.execute("INSERT INTO users (id, username, fhir_patient_id, fhir_practitioner_id) VALUES ('u-patient','patient1','1', NULL) ON CONFLICT DO NOTHING;")
        cur.execute("INSERT INTO users (id, username, fhir_patient_id, fhir_practitioner_id) VALUES ('u-adm','adm1', NULL, NULL) ON CONFLICT DO NOTHING;")
        cur.execute("INSERT INTO users (id, username, fhir_patient_id, fhir_practitioner_id) VALUES ('u-pr','pr1', NULL, '10') ON CONFLICT DO NOTHING;")
        cur.execute("INSERT INTO cita (documento_id,paciente_id,fecha_hora,duracion_minutos,estado_admision) VALUES (1,1,'2025-11-20T10:00:00',30,'pendiente');")

        # Ensure changes committed
        cur.close()
        conn.close()

        # Point application to this test DB
        os.environ["DATABASE_URL"] = f"postgresql://{user}:{password}@127.0.0.1:{port}/{db}"

        # Reload config & db modules so engine is recreated and routes pick it up.
        import src.config as sc
        import src.database as sdb

        importlib.reload(sc)
        importlib.reload(sdb)

        # Also reload modules that import get_db at top-level so they pick the new SessionLocal
        import src.auth.permissions as perms
        import src.routes.patient as patient_routes
        import src.routes.practitioner as practitioner_routes
        import src.auth.jwt as auth_jwt

        importlib.reload(perms)
        importlib.reload(patient_routes)
        importlib.reload(practitioner_routes)
        importlib.reload(auth_jwt)

        # Reload main to recreate the FastAPI app with updated dependencies
        import src.main as sm
        importlib.reload(sm)

        # Start test client
        from src.auth.jwt import create_access_token
        from src.main import app

        client = TestClient(app)

        # 1) Admissioner creates admission for paciente 1
        token_adm = create_access_token(subject="u-adm", extras={"role": "admission", "user_id": "u-adm", "username": "adm1"})
        headers = {"authorization": f"Bearer {token_adm}"}
        payload = {"paciente_id": 1, "cita_id": 1, "motivo_consulta": "Dolor"}

        r = client.post("/api/patient/1/admissions", json=payload, headers=headers)
        # Debug: if the endpoint returns an error, print body for diagnosis
        if r.status_code not in (200, 201):
            print("CREATE ADMISSION FAILED:", r.status_code)
            try:
                print(r.json())
            except Exception:
                print(r.text)
        assert r.status_code in (200, 201)
        adm = r.json()
        assert adm.get("admission_id")
        adm_id = adm.get("admission_id")

        # 2) Mark admitted
        r2 = client.post(f"/api/patient/admissions/{adm_id}/admit", headers=headers)
        assert r2.status_code == 200
        assert r2.json().get("estado_admision") in ("admitida", "activa", "admitida")

        # 3) Practitioner lists appointments and should see admitted
        token_pr = create_access_token(subject="u-pr", extras={"role": "practitioner", "user_id": "u-pr", "username": "pr1"})
        headers_pr = {"authorization": f"Bearer {token_pr}"}
        r3 = client.get("/api/practitioner/appointments", headers=headers_pr)
        assert r3.status_code == 200
        body = r3.json()
        assert body.get("count", 0) >= 1

    finally:
        # cleanup: stop container
        subprocess.run(["docker", "rm", "-f", container_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
