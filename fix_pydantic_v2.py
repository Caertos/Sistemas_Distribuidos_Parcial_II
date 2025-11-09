#!/usr/bin/env python3
"""
Script para actualizar modelos de pydantic v1 a v2
"""

import os
import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Agregar import de Literal si no existe
    if 'from typing import' in content and 'Literal' not in content:
        content = re.sub(
            r'from typing import ([^)]+)',
            r'from typing import \1, Literal',
            content
        )
    
    # Reemplazar const=True con Literal
    patterns = [
        (r'resource_type: str = Field\("([^"]+)", const=True\)', r'resource_type: Literal["\1"] = "\1"'),
        (r'@validator\(', r'@field_validator('),
        (r'def (\w+)_validator\(cls, v\):', r'@classmethod\n    def \1_validator(cls, v):'),
        (r'def (\w+)_validator\(cls, v, values\):', r'@classmethod\n    def \1_validator(cls, v, info):\n        values = info.data if info else {}'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # Agregar import de field_validator si hay validators
    if '@field_validator' in content and 'field_validator' not in content:
        content = re.sub(
            r'from pydantic import ([^)]+)',
            r'from pydantic import \1, field_validator',
            content
        )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed: {filepath}")

# Archivos a arreglar
files_to_fix = [
    'fastapi-app/app/models/condition.py',
    'fastapi-app/app/models/diagnostic_report.py',
    'fastapi-app/app/models/medication_request.py',
    'fastapi-app/app/models/observation.py',
    'fastapi-app/app/models/practitioner.py',
]

for filepath in files_to_fix:
    if os.path.exists(filepath):
        fix_file(filepath)
    else:
        print(f"File not found: {filepath}")