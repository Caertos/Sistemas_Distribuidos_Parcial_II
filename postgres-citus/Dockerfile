FROM citusdata/citus:12.1

# Copiamos scripts de inicialización SQL para que Postgres los ejecute
# al inicializar la base de datos (solo se ejecutan en la primera inicialización)
COPY init/ /docker-entrypoint-initdb.d/

# Exponer puerto por defecto de Postgres
EXPOSE 5432
