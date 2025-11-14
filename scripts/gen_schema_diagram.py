#!/usr/bin/env python3
"""
Genera un archivo Graphviz DOT a partir de un SQL de esquema (CREATE TABLE + ALTER TABLE ... FOREIGN KEY).
Uso: python3 scripts/gen_schema_diagram.py ../postgres-citus/init/02-schema-fhir.sql
Salida:
  - doc/schema_diagram.dot
  - doc/schema_diagram.png (si 'dot' está disponible)

Este script intenta extraer tablas, claves primarias y relaciones FK mediante regex simple.
No ejecuta SQL; es un parser heurístico para documentación.
"""
import re
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Uso: gen_schema_diagram.py <schema.sql>")
    sys.exit(2)

sql_path = Path(sys.argv[1])
if not sql_path.exists():
    print(f"Archivo no encontrado: {sql_path}")
    sys.exit(2)

text = sql_path.read_text(encoding='utf-8')

# encontrar bloques CREATE TABLE
create_re = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w_]+)\s*\((.*?)\);", re.I | re.S)

tables = {}
for m in create_re.finditer(text):
    name = m.group(1)
    body = m.group(2)
    # buscar primary key dentro del cuerpo
    pk_match = re.search(r"PRIMARY\s+KEY\s*\(([^)]+)\)", body, re.I)
    if pk_match:
        pk_cols = [c.strip() for c in pk_match.group(1).split(',')]
    else:
        pk_cols = []
    # intentar extraer columnas (líneas que empiezan con nombre)
    cols = []
    for line in body.split('\n'):
        line = line.strip()
        if not line or line.upper().startswith('PRIMARY KEY') or line.upper().startswith('CONSTRAINT'):
            continue
        col_match = re.match(r"([\w_]+)\s+([A-Z0-9_\(\)]+)", line, re.I)
        if col_match:
            cols.append(col_match.group(1))
    tables[name] = {'pk': pk_cols, 'cols': cols}

# encontrar FKs en ALTER TABLE ... FOREIGN KEY
fk_re = re.compile(r"ALTER\s+TABLE\s+([\w_]+).*?FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+([\w_]+)\s*\(([^)]+)\)", re.I | re.S)

fks = []
for m in fk_re.finditer(text):
    src_table = m.group(1)
    src_cols = [c.strip() for c in m.group(2).split(',')]
    ref_table = m.group(3)
    ref_cols = [c.strip() for c in m.group(4).split(',')]
    fks.append({'src': src_table, 'src_cols': src_cols, 'ref': ref_table, 'ref_cols': ref_cols})

# generar DOT (HTML-like labels)
out_dir = Path('doc')
out_dir.mkdir(parents=True, exist_ok=True)
dot_path = out_dir / 'schema_diagram.dot'

with dot_path.open('w', encoding='utf-8') as fh:
    fh.write('digraph schema {\n')
    fh.write('  graph [rankdir=LR, fontsize=12];\n')
    fh.write('  node [shape=plaintext];\n')
    for tname, info in tables.items():
        # construir tabla HTML
        fh.write(f'  {tname} [label=<\n')
        fh.write('    <table border="0" cellborder="1" cellspacing="0" cellpadding="4">\n')
        fh.write(f'      <tr><td bgcolor="#c0c0ff" colspan="2"><b>{tname}</b></td></tr>\n')
        # mostrar PKs first
        if info['pk']:
            for pk in info['pk']:
                fh.write(f'      <tr><td align="left"><i>PK</i></td><td align="left">{pk}</td></tr>\n')
        # then some columns (limit to 8 to keep diagram readable)
        shown = 0
        for col in info['cols']:
            if col in info['pk']:
                continue
            if shown >= 8:
                break
            fh.write(f'      <tr><td align="left"></td><td align="left">{col}</td></tr>\n')
            shown += 1
        if len(info['cols']) - len(info['pk']) > 8:
            fh.write(f'      <tr><td align="left" colspan="2">... +{len(info["cols"]) - len(info["pk"]) - 8} more cols</td></tr>\n')
        fh.write('    </table>\n')
        fh.write('  >];\n')
    # relaciones
    for fk in fks:
        src = fk['src']
        ref = fk['ref']
        label = ','.join(fk['src_cols']) + ' -> ' + ','.join(fk['ref_cols'])
        # avoid duplicates if tables missing
        if src in tables and ref in tables:
            fh.write(f'  {src} -> {ref} [label="{label}", fontsize=10];\n')
    fh.write('}\n')

print(f"DOT generado: {dot_path}")

# intentar renderizar con dot si está disponible
import shutil, subprocess
if shutil.which('dot'):
    png_path = out_dir / 'schema_diagram.png'
    try:
        subprocess.run(['dot', '-Tpng', '-o', str(png_path), str(dot_path)], check=True)
        print(f"PNG generado: {png_path}")
    except subprocess.CalledProcessError as e:
        print('Error al ejecutar dot:', e)
else:
    print("Graphviz 'dot' no encontrado en PATH. Instala graphviz para generar PNG (ej: apt install graphviz) o usa el archivo DOT generado.")
