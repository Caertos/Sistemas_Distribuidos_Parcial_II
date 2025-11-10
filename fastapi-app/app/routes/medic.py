"""
Medic API Routes - Endpoints específicos para funcionalidades de médicos

Incluye dashboard, gestión de pacientes, agenda, consultas y herramientas médicas.
"""

import json
import base64
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config.database import db_manager

# Configurar templates
templates = Jinja2Templates(directory="templates")

# Crear router con prefijo para médicos
router = APIRouter(
    prefix="/medic",
    tags=["Medic"],
    responses={
        404: {"description": "Resource not found"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"}
    }
)

# ================================
# AUTENTICACIÓN Y MIDDLEWARE
# ================================

async def verify_medic_token(authorization: str = Header(None, alias="Authorization")):
    """Verificar token y extraer información del médico"""
    try:
        if not authorization or not authorization.startswith("Bearer FHIR-"):
            raise HTTPException(status_code=401, detail="Token requerido")
        
        # Extraer token
        token = authorization.replace("Bearer FHIR-", "")
        token_data = json.loads(base64.b64decode(token).decode())
        
        # Verificar que el usuario sea médico/practitioner
        if token_data.get("user_type") not in ["practitioner", "medico"]:
            raise HTTPException(status_code=403, detail="Acceso solo para médicos")
        
        # Verificar expiración
        if token_data.get("expires", 0) < datetime.now().timestamp():
            raise HTTPException(status_code=401, detail="Token expirado")
        
        return token_data
    except json.JSONDecodeError:
        raise HTTPException(status_code=401, detail="Token inválido")
    except Exception:
        raise HTTPException(status_code=401, detail="Error verificando token")

# ================================
# DASHBOARD MÉDICO
# ================================

@router.get("/dashboard")
async def medic_dashboard(request: Request, user: dict = Depends(verify_medic_token)):
    return templates.TemplateResponse("medic/medic_dashboard.html", {"request": request, "user": user})

@router.get("/api/dashboard-data")
async def get_medic_dashboard_data(token_data: dict = Depends(verify_medic_token)):
    """Obtener datos dinámicos del dashboard del médico"""
    try:
        async with db_manager.AsyncSessionLocal() as session:
            # Obtener información del médico
            medic_query = text("""
                SELECT p.profesional_id, p.nombre, p.apellido, p.especialidad, 
                       p.registro_medico, u.full_name
                FROM profesional p
                JOIN users u ON p.profesional_id::varchar = u.fhir_practitioner_id
                WHERE u.id = :user_id
            """)
            medic_result = await session.execute(medic_query, {"user_id": token_data["user_id"]})
            medic_info = medic_result.first()
            
            if not medic_info:
                raise HTTPException(status_code=404, detail="Información del médico no encontrada")
            
            profesional_id = medic_info[0]
            
            # Estadísticas del médico
            stats_query = text("""
                SELECT 
                    -- Mis pacientes (únicos que he atendido)
                    (SELECT COUNT(DISTINCT e.paciente_id) 
                     FROM encuentro e 
                     WHERE e.profesional_id = :profesional_id) as my_patients,
                    
                    -- Consultas hoy
                    (SELECT COUNT(*) 
                     FROM cita c 
                     WHERE c.profesional_id = :profesional_id 
                     AND DATE(c.fecha_hora) = CURRENT_DATE) as encounters_today,
                    
                    -- Consultas esta semana
                    (SELECT COUNT(*) 
                     FROM cita c 
                     WHERE c.profesional_id = :profesional_id 
                     AND c.fecha_hora >= DATE_TRUNC('week', CURRENT_DATE)) as encounters_week,
                    
                    -- Resultados pendientes
                    (SELECT COUNT(*) 
                     FROM diagnostico_reporte dr
                     JOIN encuentro e ON dr.encuentro_id = e.encuentro_id
                     WHERE e.profesional_id = :profesional_id
                     AND dr.estado = 'pendiente') as pending_results,
                    
                    -- Urgentes
                    (SELECT COUNT(*) 
                     FROM diagnostico_reporte dr
                     JOIN encuentro e ON dr.encuentro_id = e.encuentro_id
                     WHERE e.profesional_id = :profesional_id
                     AND dr.estado = 'pendiente' 
                     AND dr.prioridad = 'urgente') as urgent_pending,
                    
                    -- Nuevos pacientes este mes
                    (SELECT COUNT(DISTINCT e.paciente_id) 
                     FROM encuentro e 
                     WHERE e.profesional_id = :profesional_id
                     AND e.fecha >= DATE_TRUNC('month', CURRENT_DATE)) as new_patients_month
            """)
            
            stats_result = await session.execute(stats_query, {"profesional_id": profesional_id})
            stats = stats_result.first()
            
            # Agenda de hoy
            agenda_query = text("""
                SELECT c.cita_id, c.fecha_hora, c.duracion_minutos, c.motivo, c.estado,
                       p.nombre, p.apellido, p.documento_id
                FROM cita c
                JOIN paciente p ON c.paciente_id = p.paciente_id
                WHERE c.profesional_id = :profesional_id
                AND DATE(c.fecha_hora) = CURRENT_DATE
                ORDER BY c.fecha_hora
            """)
            
            agenda_result = await session.execute(agenda_query, {"profesional_id": profesional_id})
            agenda_items = []
            
            for row in agenda_result:
                agenda_items.append({
                    "id": row[0],
                    "datetime": row[1].isoformat() if row[1] else None,
                    "duration": row[2] or 30,
                    "reason": row[3] or "Consulta médica",
                    "status": row[4] or "programada",
                    "patient_name": f"{row[5]} {row[6]}",
                    "patient_document": row[7]
                })
            
            # Pacientes prioritarios
            priority_query = text("""
                SELECT DISTINCT p.paciente_id, p.nombre, p.apellido, p.documento_id,
                       e.fecha as last_encounter,
                       COUNT(c.condicion_id) as active_conditions
                FROM paciente p
                JOIN encuentro e ON p.paciente_id = e.paciente_id
                LEFT JOIN condicion c ON p.paciente_id = c.paciente_id AND c.estado = 'active'
                WHERE e.profesional_id = :profesional_id
                GROUP BY p.paciente_id, p.nombre, p.apellido, p.documento_id, e.fecha
                HAVING COUNT(c.condicion_id) > 1
                ORDER BY e.fecha DESC, COUNT(c.condicion_id) DESC
                LIMIT 5
            """)
            
            priority_result = await session.execute(priority_query, {"profesional_id": profesional_id})
            priority_patients = []
            
            for row in priority_result:
                priority_patients.append({
                    "id": row[0],
                    "name": f"{row[1]} {row[2]}",
                    "document": row[3],
                    "last_encounter": row[4].isoformat() if row[4] else None,
                    "conditions_count": row[5] or 0
                })
            
            return {
                "success": True,
                "medic_info": {
                    "id": profesional_id,
                    "name": f"{medic_info[1]} {medic_info[2]}",
                    "specialty": medic_info[3] or "Medicina General",
                    "registration": medic_info[4],
                    "full_name": medic_info[5]
                },
                "stats": {
                    "my_patients": stats[0] or 0,
                    "encounters_today": stats[1] or 0,
                    "encounters_week": stats[2] or 0,
                    "pending_results": stats[3] or 0,
                    "urgent_pending": stats[4] or 0,
                    "new_patients_month": stats[5] or 0,
                    "avg_satisfaction": 4.8,  # Placeholder
                    "total_reviews": 124  # Placeholder
                },
                "agenda_today": agenda_items,
                "priority_patients": priority_patients,
                "current_date": datetime.now().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# ================================
# GESTIÓN DE PACIENTES
# ================================

@router.get("/patients", response_class=HTMLResponse)
async def medic_patients_page(
    request: Request,
    token_data: dict = Depends(verify_medic_token)
):
    """Página de lista de pacientes del médico"""
    return templates.TemplateResponse("medic/patients.html", {
        "request": request,
        "current_user": token_data.get("full_name", token_data.get("username"))
    })

@router.get("/api/patients")
async def get_medic_patients(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    token_data: dict = Depends(verify_medic_token)
):
    """Obtener lista de pacientes del médico con paginación"""
    try:
        async with db_manager.AsyncSessionLocal() as session:
            # Obtener profesional_id del médico
            medic_query = text("""
                SELECT p.profesional_id FROM profesional p
                JOIN users u ON p.profesional_id::varchar = u.fhir_practitioner_id
                WHERE u.id = :user_id
            """)
            medic_result = await session.execute(medic_query, {"user_id": token_data["user_id"]})
            medic_info = medic_result.first()
            
            if not medic_info:
                raise HTTPException(status_code=404, detail="Médico no encontrado")
            
            profesional_id = medic_info[0]
            
            # Construir query base
            base_query = """
                SELECT DISTINCT p.paciente_id, p.documento_id, p.nombre, p.apellido,
                       p.sexo, p.fecha_nacimiento, p.contacto, p.ciudad,
                       MAX(e.fecha) as last_encounter,
                       COUNT(c.condicion_id) as active_conditions
                FROM paciente p
                JOIN encuentro e ON p.paciente_id = e.paciente_id
                LEFT JOIN condicion c ON p.paciente_id = c.paciente_id AND c.estado = 'active'
                WHERE e.profesional_id = :profesional_id
            """
            
            params = {"profesional_id": profesional_id}
            
            # Agregar filtro de búsqueda si existe
            if search:
                base_query += """
                    AND (LOWER(p.nombre) LIKE LOWER(:search) 
                         OR LOWER(p.apellido) LIKE LOWER(:search)
                         OR p.documento_id LIKE :search)
                """
                params["search"] = f"%{search}%"
            
            base_query += """
                GROUP BY p.paciente_id, p.documento_id, p.nombre, p.apellido, 
                         p.sexo, p.fecha_nacimiento, p.contacto, p.ciudad
                ORDER BY MAX(e.fecha) DESC
                LIMIT :limit OFFSET :offset
            """
            
            params["limit"] = limit
            params["offset"] = (page - 1) * limit
            
            result = await session.execute(text(base_query), params)
            patients = []
            
            for row in result:
                # Calcular edad
                age = None
                if row[5]:  # fecha_nacimiento
                    age = (datetime.now().date() - row[5]).days // 365
                
                patients.append({
                    "id": row[0],
                    "document": row[1],
                    "name": f"{row[2]} {row[3]}",
                    "gender": row[4],
                    "birth_date": row[5].isoformat() if row[5] else None,
                    "age": age,
                    "contact": row[6],
                    "city": row[7],
                    "last_encounter": row[8].isoformat() if row[8] else None,
                    "active_conditions": row[9] or 0
                })
            
            # Contar total para paginación
            count_query = text("""
                SELECT COUNT(DISTINCT p.paciente_id)
                FROM paciente p
                JOIN encuentro e ON p.paciente_id = e.paciente_id
                WHERE e.profesional_id = :profesional_id
            """ + (" AND (LOWER(p.nombre) LIKE LOWER(:search) OR LOWER(p.apellido) LIKE LOWER(:search) OR p.documento_id LIKE :search)" if search else ""))
            
            count_params = {"profesional_id": profesional_id}
            if search:
                count_params["search"] = f"%{search}%"
            
            count_result = await session.execute(count_query, count_params)
            total = count_result.scalar() or 0
            
            return {
                "success": True,
                "patients": patients,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/api/patients/search")
async def search_medic_patients(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    token_data: dict = Depends(verify_medic_token)
):
    """Búsqueda rápida de pacientes para AJAX"""
    try:
        async with db_manager.AsyncSessionLocal() as session:
            # Obtener profesional_id del médico
            medic_query = text("""
                SELECT p.profesional_id FROM profesional p
                JOIN users u ON p.profesional_id::varchar = u.fhir_practitioner_id
                WHERE u.id = :user_id
            """)
            medic_result = await session.execute(medic_query, {"user_id": token_data["user_id"]})
            medic_info = medic_result.first()
            
            if not medic_info:
                raise HTTPException(status_code=404, detail="Médico no encontrado")
            
            profesional_id = medic_info[0]
            
            # Búsqueda en múltiples campos
            search_query = text("""
                SELECT DISTINCT p.paciente_id, p.documento_id, p.nombre, p.apellido,
                       p.sexo, p.fecha_nacimiento, MAX(e.fecha) as last_encounter
                FROM paciente p
                JOIN encuentro e ON p.paciente_id = e.paciente_id
                WHERE e.profesional_id = :profesional_id
                AND (LOWER(p.nombre) LIKE LOWER(:search) 
                     OR LOWER(p.apellido) LIKE LOWER(:search)
                     OR p.documento_id LIKE :search
                     OR LOWER(CONCAT(p.nombre, ' ', p.apellido)) LIKE LOWER(:search))
                GROUP BY p.paciente_id, p.documento_id, p.nombre, p.apellido, p.sexo, p.fecha_nacimiento
                ORDER BY MAX(e.fecha) DESC
                LIMIT :limit
            """)
            
            result = await session.execute(search_query, {
                "profesional_id": profesional_id,
                "search": f"%{q}%",
                "limit": limit
            })
            
            patients = []
            for row in result:
                # Calcular edad
                age = None
                if row[5]:  # fecha_nacimiento
                    age = (datetime.now().date() - row[5]).days // 365
                
                patients.append({
                    "id": row[0],
                    "name": f"{row[2]} {row[3]}",
                    "document": row[1],
                    "gender": row[4],
                    "age": age,
                    "last_encounter": row[6].isoformat() if row[6] else None
                })
            
            return {
                "success": True,
                "patients": patients
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/patients/{patient_id}", response_class=HTMLResponse)
async def medic_patient_detail(
    request: Request,
    patient_id: int = Path(...),
    token_data: dict = Depends(verify_medic_token)
):
    """Página de detalle de paciente"""
    return templates.TemplateResponse("medic/patient_detail.html", {
        "request": request,
        "patient_id": patient_id,
        "current_user": token_data.get("full_name", token_data.get("username"))
    })

# ================================
# AGENDA Y CITAS
# ================================

@router.get("/appointments", response_class=HTMLResponse)
async def medic_appointments_page(
    request: Request,
    token_data: dict = Depends(verify_medic_token)
):
    """Página de agenda del médico"""
    return templates.TemplateResponse("medic/appointments.html", {
        "request": request,
        "current_user": token_data.get("full_name", token_data.get("username"))
    })

@router.get("/api/appointments")
async def get_medic_appointments(
    date: Optional[str] = Query(None),
    week: Optional[bool] = Query(False),
    token_data: dict = Depends(verify_medic_token)
):
    """Obtener citas del médico por fecha o semana"""
    try:
        async with db_manager.AsyncSessionLocal() as session:
            # Obtener profesional_id del médico
            medic_query = text("""
                SELECT p.profesional_id FROM profesional p
                JOIN users u ON p.profesional_id::varchar = u.fhir_practitioner_id
                WHERE u.id = :user_id
            """)
            medic_result = await session.execute(medic_query, {"user_id": token_data["user_id"]})
            medic_info = medic_result.first()
            
            if not medic_info:
                raise HTTPException(status_code=404, detail="Médico no encontrado")
            
            profesional_id = medic_info[0]
            
            # Construir filtros de fecha
            date_filter = ""
            params = {"profesional_id": profesional_id}
            
            if date:
                # Fecha específica
                date_filter = "AND DATE(c.fecha_hora) = :date"
                params["date"] = date
            elif week:
                # Semana actual
                date_filter = "AND c.fecha_hora >= DATE_TRUNC('week', CURRENT_DATE) AND c.fecha_hora < DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '7 days'"
            else:
                # Por defecto, hoy
                date_filter = "AND DATE(c.fecha_hora) = CURRENT_DATE"
            
            appointments_query = text(f"""
                SELECT c.cita_id, c.fecha_hora, c.duracion_minutos, c.motivo, c.estado, c.notas,
                       p.nombre, p.apellido, p.documento_id, p.contacto
                FROM cita c
                JOIN paciente p ON c.paciente_id = p.paciente_id
                WHERE c.profesional_id = :profesional_id
                {date_filter}
                ORDER BY c.fecha_hora
            """)
            
            result = await session.execute(appointments_query, params)
            appointments = []
            
            for row in result:
                appointments.append({
                    "id": row[0],
                    "datetime": row[1].isoformat() if row[1] else None,
                    "duration": row[2] or 30,
                    "reason": row[3] or "Consulta médica",
                    "status": row[4] or "programada",
                    "notes": row[5],
                    "patient": {
                        "name": f"{row[6]} {row[7]}",
                        "document": row[8],
                        "contact": row[9]
                    }
                })
            
            return {
                "success": True,
                "appointments": appointments,
                "date": date or datetime.now().date().isoformat(),
                "week": week
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# ================================
# HERRAMIENTAS MÉDICAS
# ================================

@router.get("/tools/bmi-calculator", response_class=HTMLResponse)
async def bmi_calculator(
    request: Request,
    token_data: dict = Depends(verify_medic_token)
):
    """Calculadora de IMC"""
    return templates.TemplateResponse("medic/tools/bmi_calculator.html", {
        "request": request,
        "current_user": token_data.get("full_name", token_data.get("username"))
    })

@router.post("/api/tools/calculate-bmi")
async def calculate_bmi(
    request: Request,
    token_data: dict = Depends(verify_medic_token)
):
    """Calcular índice de masa corporal"""
    try:
        data = await request.json()
        weight = float(data.get("weight", 0))
        height = float(data.get("height", 0))
        
        if weight <= 0 or height <= 0:
            raise HTTPException(status_code=400, detail="Peso y altura deben ser positivos")
        
        # Convertir altura de cm a metros si es necesario
        if height > 3:  # Asumimos que valores > 3 están en cm
            height = height / 100
        
        bmi = weight / (height ** 2)
        
        # Clasificación del IMC
        if bmi < 18.5:
            category = "Bajo peso"
            risk = "Riesgo de problemas nutricionales"
        elif bmi < 25:
            category = "Normal"
            risk = "Riesgo bajo"
        elif bmi < 30:
            category = "Sobrepeso"
            risk = "Riesgo moderado"
        else:
            category = "Obesidad"
            risk = "Riesgo alto"
        
        return {
            "success": True,
            "bmi": round(bmi, 1),
            "category": category,
            "risk": risk,
            "weight": weight,
            "height": height
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Valores numéricos inválidos")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en cálculo: {str(e)}")

@router.post("/api/tools/calculate-gfr")
async def calculate_gfr(
    request: Request,
    token_data: dict = Depends(verify_medic_token)
):
    """Calcular tasa de filtración glomerular (GFR)"""
    try:
        data = await request.json()
        creatinine = float(data.get("creatinine", 0))  # mg/dL
        age = int(data.get("age", 0))
        gender = data.get("gender", "").lower()
        race = data.get("race", "other").lower()
        
        if creatinine <= 0 or age <= 0:
            raise HTTPException(status_code=400, detail="Creatinina y edad deben ser positivos")
        
        # Fórmula CKD-EPI 2021 (sin factor de raza)
        # GFR = 142 × min(Scr/κ, 1)^α × max(Scr/κ, 1)^(-1.200) × 0.9938^Age × (factor gender)
        
        kappa = 0.7 if gender == "female" else 0.9
        alpha = -0.241 if gender == "female" else -0.302
        gender_factor = 1.012 if gender == "female" else 1.0
        
        min_factor = min(creatinine / kappa, 1) ** alpha
        max_factor = max(creatinine / kappa, 1) ** (-1.200)
        age_factor = 0.9938 ** age
        
        gfr = 142 * min_factor * max_factor * age_factor * gender_factor
        
        # Clasificación de función renal
        if gfr >= 90:
            stage = "1"
            description = "Normal"
            risk = "Sin enfermedad renal si otros factores normales"
        elif gfr >= 60:
            stage = "2"
            description = "Ligeramente disminuida"
            risk = "Riesgo bajo"
        elif gfr >= 45:
            stage = "3a"
            description = "Moderadamente disminuida"
            risk = "Riesgo moderado"
        elif gfr >= 30:
            stage = "3b"
            description = "Moderadamente a severamente disminuida"
            risk = "Riesgo alto"
        elif gfr >= 15:
            stage = "4"
            description = "Severamente disminuida"
            risk = "Riesgo muy alto"
        else:
            stage = "5"
            description = "Falla renal"
            risk = "Riesgo máximo - considerar diálisis"
        
        return {
            "success": True,
            "gfr": round(gfr, 1),
            "stage": stage,
            "description": description,
            "risk": risk,
            "creatinine": creatinine,
            "age": age,
            "gender": gender
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Valores numéricos inválidos")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en cálculo: {str(e)}")

# ================================
# CONSULTAS Y ENCUENTROS
# ================================

@router.get("/encounters/new", response_class=HTMLResponse)
async def new_encounter_page(
    request: Request,
    appointment_id: Optional[int] = Query(None),
    token_data: dict = Depends(verify_medic_token)
):
    """Página para crear nueva consulta"""
    return templates.TemplateResponse("medic/new_encounter.html", {
        "request": request,
        "appointment_id": appointment_id,
        "current_user": token_data.get("full_name", token_data.get("username"))
    })

@router.get("/encounters/{encounter_id}", response_class=HTMLResponse)
async def view_encounter(
    request: Request,
    encounter_id: int = Path(...),
    token_data: dict = Depends(verify_medic_token)
):
    """Ver detalles de una consulta específica"""
    return templates.TemplateResponse("medic/encounter_detail.html", {
        "request": request,
        "encounter_id": encounter_id,
        "current_user": token_data.get("full_name", token_data.get("username"))
    })

# ================================
# ENDPOINTS ADICIONALES
# ================================

@router.get("/prescriptions", response_class=HTMLResponse)
async def medic_prescriptions_page(
    request: Request,
    token_data: dict = Depends(verify_medic_token)
):
    """Página de recetas del médico"""
    return templates.TemplateResponse("medic/prescriptions.html", {
        "request": request,
        "current_user": token_data.get("full_name", token_data.get("username"))
    })

@router.get("/reports", response_class=HTMLResponse)
async def medic_reports_page(
    request: Request,
    token_data: dict = Depends(verify_medic_token)
):
    """Página de reportes médicos"""
    return templates.TemplateResponse("medic/reports.html", {
        "request": request,
        "current_user": token_data.get("full_name", token_data.get("username"))
    })

@router.get("/new-patient", response_class=HTMLResponse)
async def new_patient_page(
    request: Request,
    token_data: dict = Depends(verify_medic_token)
):
    """Página para registrar nuevo paciente"""
    return templates.TemplateResponse("medic/new_patient.html", {
        "request": request,
        "current_user": token_data.get("full_name", token_data.get("username"))
    })

# Endpoint de salud específico para médicos
@router.get("/health")
async def medic_health_check(token_data: dict = Depends(verify_medic_token)):
    """Health check específico para funcionalidades de médicos"""
    return {
        "status": "healthy",
        "module": "medic",
        "user": token_data.get("username"),
        "user_type": token_data.get("user_type"),
        "timestamp": datetime.now().isoformat()
    }