#!/usr/bin/env python3
"""Genera HTML estático de las plantillas Jinja2 en `frontend/templates` y copia los estáticos a `frontend/dist/static`.

Uso:
  python3 scripts/build_frontend.py

Esto permite previsualizar el frontend sin arrancar el backend. Requiere: jinja2
Instalación: pip install jinja2
"""
import os
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / 'frontend'
TEMPLATES_DIR = FRONTEND / 'templates'
DIST = FRONTEND / 'dist'

def discover_templates():
    """Descubrir plantillas para renderizar.

    - Conserva `frontend/templates/base.html` y `frontend/templates/dashboard.html`.
    - Añade plantillas encontradas en `frontend/dashboards/**/templates/*.html`.
    Devuelve una lista de rutas relativas a `FRONTEND` que Jinja2 puede cargar.
    """
    tpl_paths = []
    # incluir solo base.html y dashboard.html desde frontend/templates
    for name in ('base.html', 'dashboard.html'):
        p = TEMPLATES_DIR / name
        if p.exists():
            tpl_paths.append(p.relative_to(FRONTEND).as_posix())

    # buscar plantillas por rol dentro de dashboards
    for p in FRONTEND.glob('dashboards/**/templates/*.html'):
        tpl_paths.append(p.relative_to(FRONTEND).as_posix())

    return tpl_paths

SAMPLE_CONTEXT = {
    'title': 'Demo local',
    'metrics': {'patients': 120, 'appointments_today': 8, 'alerts': 2, 'users': 5, 'servers': 2, 'assigned': 24},
    'recent_entries': [
        {'id': 1, 'name': 'Juan Pérez', 'date': '2025-11-17', 'status': 'Ingreso'},
        {'id': 2, 'name': 'María López', 'date': '2025-11-16', 'status': 'Alta'},
    ],
    'next_appointment': '2025-11-20',
    'status': 'Estable',
    'current_year': 2025,
}


def ensure_dist():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True, exist_ok=True)


def copy_statics():
    # Copiar css y js a dist/static
    static_dest = DIST / 'static'
    static_dest.mkdir(parents=True, exist_ok=True)
    for sub in ('css', 'js'):
        src = FRONTEND / sub
        dst = static_dest / sub
        if src.exists():
            shutil.copytree(src, dst)
        else:
            print(f'Advertencia: {src} no existe, saltando')
    # Copiar carpeta dashboards (contiene css/js por rol)
    src_dash = FRONTEND / 'dashboards'
    dst_dash = static_dest / 'dashboards'
    if src_dash.exists():
        shutil.copytree(src_dash, dst_dash)
    else:
        print(f'Advertencia: {src_dash} no existe, saltando')
    # Nota: no copiamos iconos SVG (se usan emojis)


def render_templates():
    # Cargar desde `frontend/templates` primero (para que 'base.html' y
    # 'dashboard.html' se resuelvan) y luego desde la raíz `frontend`.
    env = Environment(
        loader=FileSystemLoader([str(TEMPLATES_DIR), str(FRONTEND)]),
        autoescape=select_autoescape(['html', 'xml'])
    )

    # Proveer una función url_for compatible con las plantillas (dev local)
    env.globals['url_for'] = lambda endpoint, path=None: (f'static/{path}' if path else 'static')

    tpl_list = discover_templates()
    for tpl_name in tpl_list:
        tpl = env.get_template(tpl_name)
        rendered = tpl.render(**SAMPLE_CONTEXT, request=None)
        # escribir en dist con nombre base de la plantilla (dashboard.html, admin.html, ...)
        out_path = DIST / Path(tpl_name).name
        out_path.write_text(rendered, encoding='utf-8')
        print(f'Generado {out_path}')


def main():
    ensure_dist()
    copy_statics()
    render_templates()
    print('\nBuild completado. Previsualiza con:')
    print('  cd frontend/dist && python3 -m http.server 8000')


if __name__ == '__main__':
    main()
