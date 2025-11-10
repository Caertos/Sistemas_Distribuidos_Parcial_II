#!/bin/bash
# cleanup_system.sh - Script para limpiar archivos temporales y mantener el sistema limpio

echo "🧹 Limpiando sistema FHIR..."

# Limpiar archivos Python compilados
echo "Eliminando archivos __pycache__..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Limpiar logs antiguos
echo "Limpiando logs antiguos..."
find ./fastapi-app/logs -name "*.log" -mtime +7 -delete 2>/dev/null || true

# Limpiar volúmenes Docker no utilizados
echo "Limpiando volúmenes Docker..."
docker system prune -f --volumes 2>/dev/null || true

# Reconstruir imágenes si es necesario
echo "Verificando imágenes Docker..."
if [ "$1" == "--rebuild" ]; then
    echo "Reconstruyendo imágenes..."
    docker compose build --no-cache
fi

echo "✅ Limpieza completada"
echo "🚀 Sistema listo para usar"