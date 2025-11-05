README - Versión estudiante
===========================

Propósito
--------
Pequeña guía para levantar rápidamente el laboratorio de Citus + PostgreSQL para prácticas. Ideal para estudiantes que quieren empezar con lo mínimo para probar registro de workers, re-balanceo y drain.

Requisitos
---------
- Docker y docker-compose (o Docker Engine con "docker compose").
- Opcional: Minikube y kubectl (para despliegues en Kubernetes).

Inicio rápido (Docker Compose)
-----------------------------
1) Levantar servicios:

```bash
docker compose up -d
```

2) Registrar workers y ejecutar rebalance/drain (usa la base `test_db` por defecto):

```bash
bash register_citus.sh --rebalance --drain
```

- Alternativa todo-en-uno (si existe):

```bash
./setup_all.sh compose
```

Verificación rápida
-------------------
Entrar al coordinator y comprobar nodos activos:

```bash
# Desde el host (ajusta el puerto si es necesario)
psql -h localhost -p 5432 -U postgres -d test_db -c "SELECT * FROM master_get_active_worker_nodes();"
```

Crear tabla distribuida de prueba y ejecutar una consulta corta:

```sql
CREATE TABLE IF NOT EXISTS students(id serial PRIMARY KEY, name text);
SELECT create_distributed_table('students', 'id');
INSERT INTO students(name) VALUES ('Ana'), ('Luis');
SELECT count(*) FROM students;
```

Notas rápidas y problemas comunes
--------------------------------
- Si el script falla con "cannot add a worker node when the coordinator hostname is set to localhost", el script intentará ejecutar `SELECT citus_set_coordinator_host('citus-coordinator');` automáticamente. Asegúrate de que los nombres de hosts sean accesibles desde los workers.
- Rebalance/drain requieren `wal_level=logical` en PostgreSQL. El `docker-compose.yml` incluido ya arranca Postgres con esa opción.
- Si `citus_drain_node` falla porque una tabla no tiene PRIMARY KEY, añade la PK o usa la variable `PK_FIX_LIST` en `register_citus.sh` para intentar añadirla automáticamente.

Minikube (opcional)
--------------------
- Manifiestos Kubernetes están en `k8s/`. Usa `k8s/setup_minikube.sh` para validar dependencias. Para desplegar:

```bash
./k8s/setup_minikube.sh
# El script hace TODO: build/load de la imagen personalizada, aplica manifests,
# registra automáticamente los workers, ejecuta rebalance/drain, levanta un
# port-forward a localhost:5432 y ejecuta una verificación automática.
```

Notas sobre la instalación en Minikube
------------------------------------
- El paso `./k8s/setup_minikube.sh` construye/carga la imagen `local/citus-custom:12.1`
	(desde `postgres-citus/`) y la usa en los manifiestos. No se requieren pasos manuales
	adicionales.
- Tras la finalización, el coordinator estará accesible en `localhost:5432` gracias al
	`port-forward` que se lanza en background por el script (los logs van a `/tmp/citus_port_forward.log`).
- Si prefieres controlar manualmente el registro o el port-forward, puedes ejecutar
	`./k8s/register_citus_k8s.sh --rebalance --drain` y `kubectl port-forward svc/citus-coordinator 5432:5432`.
 
Reporte de verificación
----------------------
- El flujo automático genera un archivo `k8s/verify_report.json` con el resultado global (`PASS`/`FAIL`) y detalles por check (extensión, workers, shards, prueba funcional).
- Si el reporte indica `FAIL`, revisa los logs de los pods y `/tmp/citus_port_forward.log`.
