"""
Sistema Distribuido de Historias Clínicas - FHIR
FastAPI Backend con PostgreSQL + Citus - Versión Simplificada
"""

import hashlib
import json
import base64
from datetime import datetime
from fastapi import FastAPI, Header, HTTPException, Query, Request, Depends
from fastapi.responses import JSONResponse, Response, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.config.database import db_manager
from patient_api import get_patient_dashboard_data
from app.routes.medic import router as medic_router
from app.routes.auth import router as auth_router
from app.routes.admission import router as admission_router
from app.auth.unified_auth import verify_patient_token_unified, PatientTokenRequired
from app.auth.jwt_utils import jwt_manager
from app.models.auth import UserType

# Crear aplicación FastAPI
app = FastAPI(
    title="Sistema FHIR Distribuido",
    description="Sistema de Historias Clínicas FHIR con base de datos distribuida",
    version="1.0.0"
)

# Configurar templates y archivos estáticos
templates = Jinja2Templates(directory="templates")

# FastAPI + Jinja2 nativo - sin filtros Flask

app.mount("/static", StaticFiles(directory="static"), name="static")

# Incluir routers
app.include_router(medic_router)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(admission_router)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with db_manager.AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}
    except Exception:
        return {"status": "unhealthy", "database": "disconnected"}

# ================================
# AUTENTICACIÓN - Endpoints del form
# ================================

@app.post("/auth/login")
async def login_form(request: Request):
    """Endpoint para el formulario de login (form-data)"""
    try:
        form_data = await request.form()
        username = form_data.get("username")
        password = form_data.get("password")
        
        if not username or not password:
            return templates.TemplateResponse(
                "login.html", 
                {"request": request, "error": "Usuario y contraseña requeridos"}
            )
        
        # Hash de la contraseña usando SHA256 como en la BD
        password_with_salt = password + 'demo_salt_fhir'
        password_hash = hashlib.sha256(password_with_salt.encode()).hexdigest()
        
        async with db_manager.AsyncSessionLocal() as session:
            query = text("""
                SELECT id, username, full_name, email, user_type, fhir_patient_id
                FROM users 
                WHERE username = :username AND hashed_password = :password_hash AND is_active = true
            """)
            
            result = await session.execute(query, {
                "username": username, 
                "password_hash": password_hash
            })
            user = result.first()
            
            if not user:
                return templates.TemplateResponse(
                    "login.html", 
                    {"request": request, "error": "Credenciales inválidas"}
                )
            
            # Crear token JWT usando jwt_manager
            # Convertir el string user_type a enum UserType
            try:
                user_type_enum = UserType(user[4])
            except ValueError:
                # Si el user_type no es válido, usar OTHER como fallback
                user_type_enum = UserType.OTHER
            
            # Crear JWT token con jwt_manager
            token = jwt_manager.create_access_token(
                user_id=str(user[0]),
                username=user[1],
                user_type=user_type_enum,
                roles=[user[4]]  # Roles basados en user_type
            )
            
            # Preparar contexto común para templates
            template_context = {
                "request": request,
                "user": {
                    "id": user[0],
                    "username": user[1],
                    "email": user[2],
                    "full_name": user[3],
                    "user_type": user[4],
                    "role": user[4],  # Alias para compatibilidad con templates
                    "fhir_patient_id": user[5]
                },
                "current_user": {
                    "id": user[0],
                    "username": user[1],
                    "email": user[2],
                    "full_name": user[3],
                    "user_type": user[4],
                    "role": user[4],  # Alias para compatibilidad con templates
                    "fhir_patient_id": user[5]
                }
            }
            
            # Redirigir según el tipo de usuario
            if user[4] == "patient":
                response = RedirectResponse(url="/patient/dashboard", status_code=302)
            elif user[4] == "practitioner":
                response = RedirectResponse(url="/medic/dashboard", status_code=302) 
            elif user[4] == "admin":
                response = RedirectResponse(url="/admin/dashboard", status_code=302)
            elif user[4] == "auditor":
                response = RedirectResponse(url="/auditor/dashboard", status_code=302)
            elif user[4] == "admission":
                response = RedirectResponse(url="/admission/dashboard", status_code=302)
            else:
                response = RedirectResponse(url="/dashboard", status_code=302)
            
            # Establecer cookie con el token
            response.set_cookie(
                "authToken", 
                f"FHIR-{token}",
                max_age=86400,  # 24 horas
                httponly=False,  # Permitir acceso desde JavaScript
                secure=False  # Para desarrollo local
            )
            

            
            return response
            
    except Exception as e:
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": f"Error interno: {str(e)}"}
        )

# ================================
# AUTENTICACIÓN - API JSON
# ================================

@app.post("/api/auth/login")
async def login(request: Request):
    """Endpoint de login simplificado"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username y password requeridos")
        
        # Hash de la contraseña usando SHA256 como en la BD
        import hashlib
        password_with_salt = password + 'demo_salt_fhir'
        password_hash = hashlib.sha256(password_with_salt.encode()).hexdigest()
        
        async with db_manager.AsyncSessionLocal() as session:
            query = text("""
                SELECT id, username, full_name, email, user_type, fhir_patient_id
                FROM users 
                WHERE username = :username AND hashed_password = :password_hash AND is_active = true
            """)
            
            result = await session.execute(query, {
                "username": username, 
                "password_hash": password_hash
            })
            user = result.first()
            
            if not user:
                raise HTTPException(status_code=401, detail="Credenciales inválidas")
            
            # Crear token simple
            token_data = {
                "user_id": str(user[0]),  # Convertir UUID a string
                "username": user[1],
                "full_name": user[2],
                "email": user[3],
                "user_type": user[4],
                "fhir_patient_id": user[5],
                "expires": (datetime.now().timestamp() + 86400)  # 24 horas
            }
            
            token = base64.b64encode(json.dumps(token_data).encode()).decode()
            
            return {
                "success": True,
                "token": f"FHIR-{token}",
                "user": {
                    "id": str(user[0]),  # Convertir UUID a string
                    "username": user[1],
                    "full_name": user[2],
                    "email": user[3],
                    "user_type": user[4]
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

async def logout_handler():
    """Función helper para el logout"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("authToken")
    response.delete_cookie("authToken", domain="localhost")
    response.delete_cookie("authToken", path="/")
    return response

@app.post("/auth/logout")
async def logout_post():
    """Endpoint de logout POST"""
    try:
        return await logout_handler()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/auth/logout")
async def logout_get():
    """Endpoint de logout GET"""
    try:
        return await logout_handler()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# ================================
# DASHBOARD DE PACIENTES
# ================================

@app.get("/api/patient/dashboard")
async def get_patient_dashboard(token_data: dict = PatientTokenRequired):
    """
    Endpoint principal del dashboard de pacientes
    Retorna todos los datos necesarios para el dashboard dinámico
    """
    try:
        # Crear header de autorización compatible con la función existente
        authorization = f"Bearer FHIR-{base64.b64encode(json.dumps(token_data).encode()).decode()}"
        
        return await get_patient_dashboard_data(authorization)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# Endpoint de prueba para verificar que funciona
@app.get("/api/patient/test")
async def test_patient_endpoint():
    """Endpoint de prueba"""
    return {"success": True, "message": "Endpoint funcionando correctamente"}

@app.get("/patient/dashboard")
async def patient_dashboard_page(request: Request):
    """Página del dashboard de pacientes"""
    return templates.TemplateResponse("patient/dashboard.html", {"request": request})

# ================================
# ADMIN DASHBOARD - Template y API
# ================================

@app.get("/admin/dashboard")
async def admin_dashboard_page(request: Request):
    """Página del dashboard de administrador"""
    return templates.TemplateResponse("admin/adminDashboard.html", {"request": request})

@app.get("/api/admin/dashboard-stats")
async def get_admin_dashboard_stats(authorization: str = Header(None, alias="Authorization")):
    """
    Endpoint para obtener estadísticas del dashboard de administrador
    Requiere autenticación con rol de admin
    """
    try:
        # Verificar token y permisos de admin
        if not authorization:
            raise HTTPException(status_code=401, detail="Token de autenticación requerido")
        
        # Extraer token
        token = authorization.replace("Bearer ", "").replace("FHIR-", "")
        
        try:
            token_data = json.loads(base64.b64decode(token).decode())
        except:
            raise HTTPException(status_code=401, detail="Token inválido")
        
        # Verificar que sea admin
        if token_data.get("user_type") != "admin":
            raise HTTPException(status_code=403, detail="Acceso denegado. Se requiere rol de administrador")
        
        # Obtener estadísticas del sistema
        async with db_manager.AsyncSessionLocal() as session:
            # Consulta optimizada para todas las estadísticas
            query = text("""
                SELECT 
                    (SELECT COUNT(*) FROM users WHERE is_active = true) as active_users,
                    (SELECT COUNT(*) FROM paciente) as total_patients,
                    (SELECT COUNT(*) FROM profesional) as active_practitioners,
                    (SELECT 
                        COUNT(*) 
                     FROM observacion o
                     UNION ALL
                     SELECT COUNT(*) FROM condicion
                     UNION ALL
                     SELECT COUNT(*) FROM medicamento
                     UNION ALL
                     SELECT COUNT(*) FROM informe_diagnostico
                    ) as medical_records_count
            """)
            
            result = await session.execute(query)
            stats = result.first()
            
            # Contar registros médicos totales de forma simple
            medical_records_query = text("""
                SELECT 
                    (SELECT COUNT(*) FROM observacion) +
                    (SELECT COUNT(*) FROM condicion) +
                    (SELECT COUNT(*) FROM medicamento) +
                    (SELECT COUNT(*) FROM informe_diagnostico) as total
            """)
            
            medical_result = await session.execute(medical_records_query)
            medical_count = medical_result.scalar()
            
            return {
                "success": True,
                "stats": {
                    "active_users": stats[0] or 0,
                    "total_patients": stats[1] or 0,
                    "active_practitioners": stats[2] or 0,
                    "medical_records": medical_count or 0
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# ================================
# ADMISSION DASHBOARD - Template
# ================================

@app.get("/admission/dashboard")
async def admission_dashboard_page(request: Request):
    """Página del dashboard de admisiones/enfermería"""
    return templates.TemplateResponse("admission/admissionDashboard.html", {"request": request})

# ================================
# PATIENT HEALTH RECORD
# ================================

@app.get("/api/patient/health-record/download")
async def download_patient_health_record(authorization: str = Header(None, alias="Authorization")):
    """Descargar historia clínica del paciente en PDF"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from io import BytesIO
        
        # Verificar token
        token_data = await verify_patient_token(authorization)
        if not token_data:
            raise HTTPException(status_code=401, detail="Token inválido o acceso no autorizado")
        
        # Obtener datos completos del paciente
        dashboard_data = await get_patient_dashboard_data(authorization)
        
        if not dashboard_data["success"]:
            raise HTTPException(status_code=404, detail="No se encontraron datos del paciente")
        
        # Crear PDF en memoria
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Configurar estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # Centrado
            textColor=colors.HexColor('#2c3e50')
        )
        
        story = []
        
        # Título
        story.append(Paragraph("HISTORIA CLÍNICA DIGITAL", title_style))
        story.append(Spacer(1, 20))
        
        # Información del paciente
        patient_info = dashboard_data["patient_info"]
        patient_data = [
            ["Nombre Completo:", patient_info.get("full_name", "N/A")],
            ["Username:", patient_info.get("username", "N/A")],
            ["Email:", patient_info.get("email", "N/A")],
            ["Teléfono:", patient_info.get("phone", "N/A")],
            ["Ciudad:", patient_info.get("city", "N/A")],
            ["Fecha de Nacimiento:", patient_info.get("birth_date", "N/A")],
            ["Género:", patient_info.get("gender", "N/A")]
        ]
        
        patient_table = Table(patient_data, colWidths=[2*inch, 3*inch])
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(Paragraph("INFORMACIÓN DEL PACIENTE", styles['Heading2']))
        story.append(patient_table)
        story.append(Spacer(1, 20))
        
        # Métricas de salud
        metrics = dashboard_data["health_metrics"]
        story.append(Paragraph("MÉTRICAS DE SALUD", styles['Heading2']))
        metrics_data = [
            ["Días próxima cita:", str(metrics.get("next_appointment_days", "N/A"))],
            ["Medicamentos activos:", str(metrics.get("active_medications", 0))],
            ["Puntuación salud:", f"{metrics.get('health_score', 0)}%"],
            ["Citas este año:", str(metrics.get("total_appointments", 0))]
        ]
        
        metrics_table = Table(metrics_data, colWidths=[2*inch, 1*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e3f2fd')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10)
        ]))
        
        story.append(metrics_table)
        story.append(Spacer(1, 20))
        
        # Medicamentos activos
        medications = dashboard_data.get("medication_reminders", [])
        if medications:
            story.append(Paragraph("MEDICAMENTOS ACTIVOS", styles['Heading2']))
            med_data = [["Medicamento", "Dosis", "Frecuencia", "Prescriptor"]]
            
            for med in medications:
                med_data.append([
                    med.get("medication_name", "N/A"),
                    med.get("dosage", "N/A"),
                    med.get("frequency", "N/A"),
                    med.get("prescriptor", "N/A")
                ])
            
            med_table = Table(med_data, colWidths=[2*inch, 1*inch, 1.5*inch, 1.5*inch])
            med_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4caf50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(med_table)
            story.append(Spacer(1, 20))
        
        # Historial médico reciente
        history = dashboard_data.get("recent_medical_history", [])
        if history:
            story.append(Paragraph("HISTORIAL MÉDICO RECIENTE", styles['Heading2']))
            
            for record in history:
                story.append(Paragraph(f"<b>Fecha:</b> {record.get('date', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"<b>Título:</b> {record.get('title', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"<b>Descripción:</b> {record.get('description', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"<b>Doctor:</b> {record.get('doctor_name', 'N/A')} - {record.get('specialty', 'N/A')}", styles['Normal']))
                story.append(Spacer(1, 10))
        
        # Alergias importantes
        allergies = dashboard_data.get("important_allergies", [])
        if allergies:
            story.append(Paragraph("ALERGIAS IMPORTANTES", styles['Heading2']))
            allergy_data = [["Alérgeno", "Severidad", "Reacción"]]
            
            for allergy in allergies:
                allergy_data.append([
                    allergy.get("allergen", "N/A"),
                    allergy.get("severity", "N/A"),
                    allergy.get("reaction", "N/A")
                ])
            
            allergy_table = Table(allergy_data, colWidths=[2*inch, 1.5*inch, 2.5*inch])
            allergy_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff9800')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(allergy_table)
        
        # Generar PDF
        doc.build(story)
        
        # Configurar respuesta
        buffer.seek(0)
        
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=historia_clinica_{patient_info.get('username', 'paciente')}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")

# Función auxiliar mantenida para compatibilidad con funciones existentes
async def verify_patient_token(authorization: str):
    """Verificar token y extraer información del paciente"""
    try:
        if not authorization or not authorization.startswith("Bearer FHIR-"):
            return None
        
        # Extraer token
        token = authorization.replace("Bearer FHIR-", "")
        token_data = json.loads(base64.b64decode(token).decode())
        
        # Verificar que el usuario sea paciente
        if token_data.get("user_type") != "patient":
            return None
        
        return token_data
    except:
        return None

# ================================
# PÁGINAS PRINCIPALES
# ================================

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Página principal del sistema"""
    return templates.TemplateResponse("homepage.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Página de login"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def general_dashboard(request: Request):
    """Dashboard general - redirige según tipo de usuario"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

# ================================
# ENDPOINTS BÁSICOS DE DATOS
# ================================

@app.get("/api/patients")
async def get_patients(limit: int = Query(50, ge=1, le=100)):
    """Obtener lista de pacientes"""
    try:
        async with db_manager.AsyncSessionLocal() as session:
            query = text("""
                SELECT p.paciente_id, p.documento_id, p.nombre, p.apellido, 
                       p.sexo, p.fecha_nacimiento, p.contacto, p.ciudad,
                       u.username, u.email
                FROM paciente p
                LEFT JOIN users u ON p.paciente_id::varchar = u.fhir_patient_id
                ORDER BY p.nombre, p.apellido
                LIMIT :limit
            """)
            
            result = await session.execute(query, {"limit": limit})
            patients = []
            
            for row in result:
                patients.append({
                    "paciente_id": row[0],
                    "documento_id": row[1],
                    "nombre": row[2],
                    "apellido": row[3],
                    "sexo": row[4],
                    "fecha_nacimiento": row[5].isoformat() if row[5] else None,
                    "contacto": row[6],
                    "ciudad": row[7],
                    "username": row[8],
                    "email": row[9]
                })
            
            return {
                "success": True,
                "patients": patients,
                "total": len(patients)
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/api/practitioners")
async def get_practitioners(limit: int = Query(50, ge=1, le=100)):
    """Obtener lista de profesionales"""
    try:
        async with db_manager.AsyncSessionLocal() as session:
            query = text("""
                SELECT p.profesional_id, p.nombre, p.apellido, p.especialidad,
                       p.numero_licencia, p.contacto, p.activo,
                       u.username, u.email
                FROM profesional p
                LEFT JOIN users u ON p.profesional_id::varchar = u.fhir_practitioner_id
                ORDER BY p.nombre, p.apellido
                LIMIT :limit
            """)
            
            result = await session.execute(query, {"limit": limit})
            practitioners = []
            
            for row in result:
                practitioners.append({
                    "profesional_id": row[0],
                    "nombre": row[1],
                    "apellido": row[2],
                    "especialidad": row[3],
                    "numero_licencia": row[4],
                    "contacto": row[5],
                    "activo": row[6],
                    "username": row[7],
                    "email": row[8]
                })
            
            return {
                "success": True,
                "practitioners": practitioners,
                "total": len(practitioners)
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/api/patient/available-doctors")
async def get_available_doctors(token_data: dict = PatientTokenRequired):
    """Obtener lista de médicos disponibles para agendar citas"""
    try:
        
        async with db_manager.AsyncSessionLocal() as session:
            query = text("""
                SELECT DISTINCT p.profesional_id, p.nombre, p.apellido, p.especialidad, 
                       p.registro_medico, u.email
                FROM profesional p
                LEFT JOIN users u ON p.profesional_id::varchar = u.fhir_practitioner_id
                WHERE p.profesional_id IS NOT NULL
                ORDER BY p.especialidad, p.nombre, p.apellido
            """)
            
            result = await session.execute(query)
            doctors = []
            
            for row in result:
                doctors.append({
                    "id": row[0],
                    "name": f"{row[1]} {row[2]}",
                    "specialty": row[3] or "Medicina General",
                    "registration": row[4],
                    "email": row[5]
                })
            
            return {
                "success": True,
                "doctors": doctors
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.post("/api/patient/schedule-appointment")
async def schedule_appointment(
    request: Request,
    token_data: dict = PatientTokenRequired
):
    """Agendar una nueva cita médica"""
    try:
        
        data = await request.json()
        doctor_id = data.get("doctor_id")
        appointment_date = data.get("appointment_date")
        appointment_time = data.get("appointment_time")
        reason = data.get("reason", "Consulta médica")
        notes = data.get("notes", "")
        
        # Validaciones
        if not doctor_id or not appointment_date or not appointment_time:
            raise HTTPException(status_code=400, detail="Faltan datos requeridos")
        
        # Obtener datos del paciente
        user_id = token_data["user_id"]
        fhir_patient_id = token_data.get("fhir_patient_id")
        
        if not fhir_patient_id:
            raise HTTPException(status_code=400, detail="Paciente no vinculado correctamente")
        
        async with db_manager.AsyncSessionLocal() as session:
            # Obtener datos del paciente desde la tabla paciente
            patient_query = text("""
                SELECT documento_id, paciente_id FROM paciente 
                WHERE paciente_id = :patient_id
            """)
            patient_result = await session.execute(patient_query, {"patient_id": int(fhir_patient_id)})
            patient_data = patient_result.first()
            
            if not patient_data:
                raise HTTPException(status_code=404, detail="Datos del paciente no encontrados")
            
            documento_id = patient_data[0]
            paciente_id = patient_data[1]
            
            # Combinar fecha y hora
            datetime_str = f"{appointment_date} {appointment_time}"
            appointment_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            
            # Verificar que la fecha no sea en el pasado
            if appointment_datetime < datetime.now():
                raise HTTPException(status_code=400, detail="No se puede agendar citas en el pasado")
            
            # Obtener el siguiente ID de cita
            next_id_query = text("SELECT COALESCE(MAX(cita_id), 0) + 1 FROM cita")
            next_id_result = await session.execute(next_id_query)
            next_cita_id = next_id_result.scalar()
            
            # Insertar la nueva cita con estado_admision pendiente
            insert_query = text("""
                INSERT INTO cita (
                    cita_id, documento_id, paciente_id, profesional_id, 
                    fecha_hora, duracion_minutos, tipo_cita, motivo, estado, notas,
                    estado_admision
                ) VALUES (
                    :cita_id, :documento_id, :paciente_id, :profesional_id,
                    :fecha_hora, :duracion, :tipo_cita, :motivo, :estado, :notas,
                    :estado_admision
                )
            """)
            
            await session.execute(insert_query, {
                "cita_id": next_cita_id,
                "documento_id": documento_id,
                "paciente_id": paciente_id,
                "profesional_id": int(doctor_id),
                "fecha_hora": appointment_datetime,
                "duracion": 30,  # 30 minutos por defecto
                "tipo_cita": "consulta",
                "motivo": reason,
                "estado": "programada",
                "notas": notes,
                "estado_admision": "pendiente"  # Requiere admisión por enfermería
            })
            
            await session.commit()
            
            return {
                "success": True,
                "message": "Cita agendada exitosamente. Deberás pasar por admisión/enfermería antes de tu consulta médica.",
                "appointment": {
                    "id": next_cita_id,
                    "date": appointment_date,
                    "time": appointment_time,
                    "doctor_id": doctor_id,
                    "reason": reason,
                    "status": "programada",
                    "admission_status": "pendiente"
                }
            }
            
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Formato de fecha/hora inválido")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/api/statistics")
async def get_system_statistics():
    """Obtener estadísticas generales del sistema"""
    try:
        async with db_manager.AsyncSessionLocal() as session:
            query = text("""
                SELECT 
                    (SELECT COUNT(*) FROM paciente) as total_patients,
                    (SELECT COUNT(*) FROM profesional) as active_practitioners,
                    (SELECT COUNT(*) FROM encuentro WHERE fecha >= CURRENT_DATE - INTERVAL '30 days') as recent_encounters,
                    (SELECT COUNT(*) FROM cita WHERE fecha_hora >= NOW()) as upcoming_appointments,
                    (SELECT COUNT(*) FROM medicamento WHERE estado = 'activo') as active_medications,
                    (SELECT COUNT(*) FROM users WHERE is_active = true) as active_users
            """)
            
            result = await session.execute(query)
            stats = result.first()
            
            return {
                "success": True,
                "statistics": {
                    "total_patients": stats[0] or 0,
                    "active_practitioners": stats[1] or 0,
                    "recent_encounters": stats[2] or 0,
                    "upcoming_appointments": stats[3] or 0,
                    "active_medications": stats[4] or 0,
                    "active_users": stats[5] or 0
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# ================================
# MANEJO DE ERRORES
# ================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"success": False, "detail": "Endpoint no encontrado"}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"success": False, "detail": "Error interno del servidor"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)