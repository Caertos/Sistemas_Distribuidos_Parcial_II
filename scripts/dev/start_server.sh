#!/bin/bash

# Script para iniciar el servidor FastAPI FHIR
# Navega al directorio correcto y usa el entorno virtual apropiado

echo "Iniciando servidor FHIR FastAPI..."
echo "Directorio actual: $(pwd)"

# Asegurar que estamos en el directorio fastapi-app
cd "$(dirname "$0")"
echo "Cambiado a directorio: $(pwd)"

# Activar entorno virtual y ejecutar servidor
export PYTHONPATH="$(pwd):$PYTHONPATH"
/media/caertos/DC/ProyectosAcademicos/Sistemas_Distribuidos_Parcial_II/.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000