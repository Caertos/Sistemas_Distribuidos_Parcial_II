#!/bin/bash

# 🚀 Script de instalación rápida para FastAPI FHIR API
# ===================================================

echo "🚀 Instalando FastAPI FHIR Clinical Records API..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir con color
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar Python
print_status "Verificando Python..."
if ! command -v python3 &> /dev/null; then
    print_error "Python3 no está instalado"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
print_success "Python encontrado: $PYTHON_VERSION"

# Crear entorno virtual
print_status "Creando entorno virtual..."
if [ -d "venv" ]; then
    print_warning "El entorno virtual ya existe"
else
    python3 -m venv venv
    print_success "Entorno virtual creado"
fi

# Activar entorno virtual
print_status "Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
print_status "Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt
print_success "Dependencias instaladas"

# Crear archivo .env si no existe
if [ ! -f ".env" ]; then
    print_status "Creando archivo .env..."
    cp .env.example .env
    print_success "Archivo .env creado desde .env.example"
    print_warning "¡Recuerda configurar las variables de entorno en .env!"
else
    print_warning "El archivo .env ya existe"
fi

print_success "¡Instalación completada!"
echo ""
print_status "Para ejecutar la aplicación:"
echo "  1. Activar entorno virtual: source venv/bin/activate"
echo "  2. Configurar .env con tus valores"
echo "  3. Ejecutar: python main.py"
echo ""
print_status "Documentación disponible en: http://localhost:8000/docs"