#!/usr/bin/env python3
"""
Frontend Flask Application
Aplicación frontend con Flask para el sistema FHIR distribuido
"""

import os
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la aplicación
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-super-secret-flask-key-change-in-production')

# Configuración de la API FastAPI
FASTAPI_URL = os.getenv('FASTAPI_URL', 'http://fastapi-app:8000')

# Configuración de Flask
app.config.update(
    SECRET_KEY=app.secret_key,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
    SESSION_COOKIE_SECURE=False,  # True en producción con HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

def make_api_request(endpoint, method='GET', data=None, headers=None):
    """Realizar petición a la API FastAPI"""
    url = f"{FASTAPI_URL}{endpoint}"
    
    # Headers por defecto
    default_headers = {'Content-Type': 'application/json'}
    if headers:
        default_headers.update(headers)
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=default_headers, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=default_headers, timeout=10)
        elif method == 'PUT':
            response = requests.put(url, json=data, headers=default_headers, timeout=10)
        elif method == 'DELETE':
            response = requests.delete(url, headers=default_headers, timeout=10)
        else:
            raise ValueError(f"Método HTTP no soportado: {method}")
            
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error en petición API: {e}")
        return None

def get_user_from_token(token):
    """Obtener información del usuario desde el token"""
    try:
        # El token tiene formato FHIR-{base64_encoded_json}
        if token.startswith('FHIR-'):
            token_data = token[5:]  # Remover prefijo FHIR-
        else:
            token_data = token
        
        # Decodificar base64 y convertir a JSON
        import base64
        import json
        
        # Agregar padding si es necesario
        missing_padding = len(token_data) % 4
        if missing_padding:
            token_data += '=' * (4 - missing_padding)
            
        decoded_bytes = base64.b64decode(token_data)
        payload = json.loads(decoded_bytes.decode('utf-8'))
        return payload
    except Exception as e:
        print(f"Error decodificando token: {e}")
        return None

@app.route('/')
def index():
    """Página principal"""
    # Verificar si el usuario está autenticado
    token = session.get('access_token')
    user = None
    
    if token:
        user = get_user_from_token(token)
    
    return render_template('index.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'GET':
        # Si ya está autenticado, redirigir según el rol
        token = session.get('access_token')
        if token:
            user = get_user_from_token(token)
            if user and user.get('user_type'):
                return redirect(url_for('dashboard', role=user['user_type']))
        
        return render_template('login.html')
    
    elif request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me') == 'on'
        
        if not username or not password:
            flash('Usuario y contraseña son requeridos', 'error')
            return render_template('login.html')
        
        # Realizar login a través de la API
        login_data = {
            'username': username,
            'password': password,
            'remember_me': remember_me
        }
        
        response = make_api_request('/auth/login', 'POST', login_data)
        
        if response and response.status_code == 200:
            tokens = response.json()
            
            # Guardar tokens en la sesión
            session['access_token'] = tokens.get('access_token')
            session['refresh_token'] = tokens.get('refresh_token')
            session.permanent = remember_me
            
            # Obtener información del usuario
            user = get_user_from_token(tokens.get('access_token'))
            
            if user and user.get('user_type'):
                flash('Login exitoso', 'success')
                return redirect(url_for('dashboard', role=user['user_type']))
            else:
                flash('Error al obtener información del usuario', 'error')
        else:
            flash('Credenciales inválidas', 'error')
        
        return render_template('login.html')

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    flash('Sesión cerrada exitosamente', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard/<role>')
def dashboard(role):
    """Dashboard por rol"""
    # Verificar autenticación
    token = session.get('access_token')
    if not token:
        flash('Debe iniciar sesión para acceder', 'error')
        return redirect(url_for('login'))
    
    user = get_user_from_token(token)
    if not user:
        flash('Token inválido, inicie sesión nuevamente', 'error')
        return redirect(url_for('login'))
    
    # Verificar que el usuario tenga el rol correcto
    user_role = user.get('user_type', '').lower()
    if user_role != role.lower() and user_role != 'admin':
        flash('No tiene permisos para acceder a este dashboard', 'error')
        return redirect(url_for('index'))
    
    # Obtener datos del dashboard desde la API
    headers = {'Authorization': f'Bearer {token}'}
    response = make_api_request(f'/dashboard/{role}', 'GET', headers=headers)
    
    if response and response.status_code == 200:
        # Si la API devuelve HTML, mostrar directamente
        if 'text/html' in response.headers.get('Content-Type', ''):
            return response.text
        else:
            # Si devuelve JSON, renderizar template local
            data = response.json()
            return render_template(f'dashboard_{role}.html', user=user, data=data)
    else:
        flash('Error al cargar el dashboard', 'error')
        return redirect(url_for('index'))

@app.route('/health')
def health():
    """Health check del frontend"""
    return jsonify({
        'status': 'healthy',
        'service': 'flask-frontend',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.errorhandler(404)
def not_found(error):
    """Página de error 404"""
    return render_template('error.html', 
                         error_code=404, 
                         error_message='Página no encontrada'), 404

@app.errorhandler(500)
def internal_error(error):
    """Página de error 500"""
    return render_template('error.html', 
                         error_code=500, 
                         error_message='Error interno del servidor'), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    
    print(f"🚀 Frontend Flask iniciando en puerto {port}")
    print(f"🔗 API Backend: {FASTAPI_URL}")
    print(f"🐛 Debug: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)