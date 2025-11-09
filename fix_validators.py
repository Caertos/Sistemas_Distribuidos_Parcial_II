#!/usr/bin/env python3
"""
Script para actualizar todos los validators de pydantic v1 a v2
"""

import os
import re
from pathlib import Path

def fix_validators_in_file(filepath):
    """Arreglar todos los validators en un archivo"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Cambiar @validator por @field_validator
    content = re.sub(r'@validator\(([^)]+)\)', r'@field_validator(\1)', content)
    
    # Cambiar la firma de las funciones de validator
    # Patrón: def nombre_validator(cls, v): -> @classmethod def nombre_validator(cls, v):
    content = re.sub(
        r'(\s+)def (\w+_validator)\(cls, v\):',
        r'\1@classmethod\n\1def \2(cls, v):',
        content
    )
    
    # Patrón: def nombre_validator(cls, v, values): -> @classmethod def nombre_validator(cls, v, info):
    content = re.sub(
        r'(\s+)def (\w+)\(cls, v, values\):',
        r'\1@classmethod\n\1def \2(cls, v, info):\n\1    values = info.data if info else {}',
        content
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed validators in: {filepath}")

# Buscar todos los archivos .py en fastapi-app
fastapi_dir = Path('fastapi-app')
for py_file in fastapi_dir.rglob('*.py'):
    # Leer el archivo para verificar si tiene @validator
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if '@validator(' in content:
            fix_validators_in_file(py_file)
    except Exception as e:
        print(f"Error processing {py_file}: {e}")

print("Proceso completado!")