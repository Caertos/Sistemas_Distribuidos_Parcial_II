"""
Medic API Routes - Endpoints específicos para funcionalidades de médicos

Incluye dashboard, gestión de pacientes, agenda, consultas y herramientas médicas.
"""

import json
import base64
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request, Header
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config.database import db_manager
from app.auth.unified_auth import MedicTokenRequired

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
# AUTENTICACIÓN UNIFICADA
# ================================
# Autenticación manejada por unified_auth.py

# ================================
# DASHBOARD MÉDICO
# ================================

@router.get("/dashboard")
async def medic_dashboard(request: Request, user: dict = MedicTokenRequired):
    return templates.TemplateResponse("medic/dashboard.html", {"request": request, "user": user})

@router.get("/api/dashboard-data")
async def get_medic_dashboard_data(request: Request, token_data: dict = MedicTokenRequired):
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
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

# ================================
# NUEVOS ENDPOINTS PARA DASHBOARD REFACTORIZADO  
# ================================

async def get_profesional_id(session, user_id: str) -> int:
    """Función auxiliar optimizada para obtener profesional_id"""
    medic_query = text("""
        SELECT p.profesional_id 
        FROM profesional p
        JOIN users u ON p.profesional_id::varchar = u.fhir_practitioner_id
        WHERE u.id::varchar = :user_id
    """)
    result = await session.execute(medic_query, {"user_id": str(user_id)})
    medic_info = result.first()
    
    if not medic_info:
        raise HTTPException(status_code=404, detail="Médico no encontrado")
    
    return medic_info[0]

@router.get("/api/dashboard-stats")
async def get_dashboard_stats(request: Request, token_data: dict = MedicTokenRequired):
    """Estadísticas específicas para el nuevo dashboard"""
    try:
        async with db_manager.AsyncSessionLocal() as session:
            profesional_id = await get_profesional_id(session, token_data["user_id"])
            
            # Estadísticas del dashboard - consultas separadas para compatibilidad con Citus
            
            # Estadísticas de citas de hoy
            appointments_query = text("""
                SELECT 
                    COUNT(DISTINCT CASE WHEN estado IN ('programada', 'confirmada') THEN paciente_id END) as pending_patients,
                    COUNT(cita_id) as todays_appointments
                FROM cita 
                WHERE profesional_id = :profesional_id 
                    AND DATE(fecha_hora) = CURRENT_DATE
            """)
            appointments_result = await session.execute(appointments_query, {"profesional_id": profesional_id})
            appointments_stats = appointments_result.first()
            
            # Estadísticas de encuentros/consultas completadas hoy
            encounters_query = text("""
                SELECT COUNT(DISTINCT encuentro_id) as completed_consultations
                FROM encuentro 
                WHERE profesional_id = :profesional_id 
                    AND DATE(fecha) = CURRENT_DATE
            """)
            encounters_result = await session.execute(encounters_query, {"profesional_id": profesional_id})
            encounters_stats = encounters_result.first()
            
            # Estadísticas de prescripciones pendientes
            prescriptions_query = text("""
                SELECT COUNT(*) as pending_prescriptions
                FROM medicamento 
                WHERE prescriptor_id = :profesional_id
                    AND estado = 'activa'
            """)
            prescriptions_result = await session.execute(prescriptions_query, {"profesional_id": profesional_id})
            prescriptions_stats = prescriptions_result.first()
            
            return {
                "success": True,
                "stats": {
                    "pending_patients": appointments_stats[0] if appointments_stats else 0,
                    "todays_appointments": appointments_stats[1] if appointments_stats else 0,
                    "completed_consultations": encounters_stats[0] if encounters_stats else 0,
                    "pending_prescriptions": prescriptions_stats[0] if prescriptions_stats else 0
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/api/patients/pending-queue")
async def get_pending_patients_queue(request: Request, token_data: dict = MedicTokenRequired):
    """Cola de pacientes pendientes - versión simplificada para Citus"""
    try:
        async with db_manager.AsyncSessionLocal() as session:
            profesional_id = await get_profesional_id(session, token_data["user_id"])
            
            # Consulta simplificada sin JOINs complejos
            queue_query = text("""
                SELECT cita_id, paciente_id, fecha_hora, motivo, estado
                FROM cita
                WHERE profesional_id = :profesional_id
                    AND DATE(fecha_hora) = CURRENT_DATE
                    AND estado IN ('programada', 'confirmada')
                ORDER BY fecha_hora ASC
                LIMIT 10
            """)
            
            queue_result = await session.execute(queue_query, {"profesional_id": profesional_id})
            patients = []
            
            result = await session.execute(queue_query, {"profesional_id": profesional_id})
            patients = []
            
            for row in result:
                # Obtener datos del paciente por separado
                patient_query = text("SELECT nombre, apellido FROM paciente WHERE paciente_id = :paciente_id")
                patient_result = await session.execute(patient_query, {"paciente_id": row[1]})
                patient = patient_result.first()
                
                # Determinar prioridad
                motivo = row[3] or ""
                if any(word in motivo.lower() for word in ['urgente', 'emergencia']):
                    priority = 'urgente'
                elif any(word in motivo.lower() for word in ['control', 'seguimiento']):
                    priority = 'normal'
                else:
                    priority = 'normal'
                
                patients.append({
                    "id": row[1],  # paciente_id
                    "name": f"{patient[0]} {patient[1]}" if patient else "Paciente no encontrado",
                    "appointment_time": row[2].strftime('%H:%M') if row[2] else None,
                    "reason": motivo or "Consulta médica",
                    "priority": priority,
                    "arrival_time": row[2].strftime('%H:%M') if row[2] else "No registrada",
                    "position": len(patients) + 1
                })
            
            return {
                "success": True,
                "patients": patients,
                "count": len(patients)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/api/recent-activity")
async def get_recent_activity(request: Request, token_data: dict = MedicTokenRequired):
    """Actividad reciente del médico - versión simplificada para Citus"""
    try:
        async with db_manager.AsyncSessionLocal() as session:
            profesional_id = await get_profesional_id(session, token_data["user_id"])
            activities = []
            
            # Obtener encuentros recientes
            encounters_query = text("""
                SELECT encuentro_id, paciente_id, fecha
                FROM encuentro
                WHERE profesional_id = :profesional_id
                    AND fecha >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY fecha DESC
                LIMIT 5
            """)
            encounters_result = await session.execute(encounters_query, {"profesional_id": profesional_id})
            
            for row in encounters_result:
                # Obtener nombre del paciente por separado
                patient_query = text("SELECT nombre, apellido FROM paciente WHERE paciente_id = :paciente_id")
                patient_result = await session.execute(patient_query, {"paciente_id": row[1]})
                patient = patient_result.first()
                
                activities.append({
                    "type": "consultation",
                    "description": f"Consulta con {patient[0]} {patient[1]}" if patient else "Consulta médica",
                    "time": row[2].strftime('%H:%M - %d/%m') if row[2] else "Fecha no disponible",
                    "timestamp": row[2].isoformat() if row[2] else None
                })
            
            # Obtener prescripciones recientes
            prescriptions_query = text("""
                SELECT medicamento_id, paciente_id, nombre_medicamento, created_at
                FROM medicamento
                WHERE prescriptor_id = :profesional_id
                    AND created_at >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            prescriptions_result = await session.execute(prescriptions_query, {"profesional_id": profesional_id})
            
            for row in prescriptions_result:
                # Obtener nombre del paciente por separado
                patient_query = text("SELECT nombre, apellido FROM paciente WHERE paciente_id = :paciente_id")
                patient_result = await session.execute(patient_query, {"paciente_id": row[1]})
                patient = patient_result.first()
                
                activities.append({
                    "type": "prescription",
                    "description": f"Prescripción de {row[2]} para {patient[0]} {patient[1]}" if patient else f"Prescripción de {row[2]}",
                    "time": row[3].strftime('%H:%M - %d/%m') if row[3] else "Fecha no disponible",
                    "timestamp": row[3].isoformat() if row[3] else None
                })
            
            # Ordenar por timestamp
            activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            activities = activities[:10]  # Limitar a 10
            
            return {
                "success": True,
                "activities": activities,
                "count": len(activities)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/api/consultations")
async def save_consultation(request: Request, token_data: dict = MedicTokenRequired):
    """Guardar nueva consulta médica"""
    try:
        data = await request.json()
        
        async with db_manager.AsyncSessionLocal() as session:
            # Obtener profesional_id
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
            
            # Insertar nueva consulta (encuentro)
            insert_query = text("""
                INSERT INTO encuentro (
                    paciente_id, profesional_id, fecha, tipo, 
                    motivo_consulta, hallazgos_clinicos, diagnostico, plan_tratamiento
                ) VALUES (
                    :patient_id, :profesional_id, CURRENT_TIMESTAMP, :consultation_type,
                    :reason, :clinical_findings, :diagnosis, :treatment_plan
                )
                RETURNING encuentro_id
            """)
            
            result = await session.execute(insert_query, {
                "patient_id": data["patient_id"],
                "profesional_id": profesional_id,
                "consultation_type": data["consultation_type"],
                "reason": data["reason"],
                "clinical_findings": data.get("clinical_findings", ""),
                "diagnosis": data.get("diagnosis", ""),
                "treatment_plan": data.get("treatment_plan", "")
            })
            
            consultation_id = result.scalar()
            await session.commit()
            
            return {
                "success": True,
                "consultation_id": consultation_id,
                "message": "Consulta guardada exitosamente"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Error guardando consulta: {str(e)}")

@router.post("/api/prescriptions")
async def save_prescription(request: Request, token_data: dict = MedicTokenRequired):
    """Guardar nueva prescripción médica"""
    try:
        data = await request.json()
        
        async with db_manager.AsyncSessionLocal() as session:
            # Obtener profesional_id
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
            
            # Buscar encuentro reciente del paciente con este médico
            encounter_query = text("""
                SELECT encuentro_id FROM encuentro 
                WHERE paciente_id = :patient_id AND profesional_id = :profesional_id
                ORDER BY fecha DESC
                LIMIT 1
            """)
            
            encounter_result = await session.execute(encounter_query, {
                "patient_id": data["patient_id"],
                "profesional_id": profesional_id
            })
            encounter = encounter_result.first()
            
            if not encounter:
                raise HTTPException(status_code=404, detail="No se encontró consulta previa para este paciente")
            
            # Insertar nueva prescripción
            prescription_query = text("""
                INSERT INTO medicamento (
                    documento_id, paciente_id, nombre_medicamento, dosis, frecuencia, 
                    prescriptor_id, estado, notas
                ) VALUES (
                    :encounter_id, :patient_id, :medication_name, :dosage, :frequency,
                    :prescriptor_id, 'activa', :instructions
                )
                RETURNING medicamento_id
            """)
            
            result = await session.execute(prescription_query, {
                "encounter_id": encounter[0],  # documento_id
                "patient_id": data["patient_id"],
                "medication_name": data["medication_name"],
                "dosage": data["dosage"],
                "frequency": data["frequency"],
                "prescriptor_id": profesional_id,
                "instructions": data.get("instructions", "")
            })
            
            prescription_id = result.scalar()
            await session.commit()
            
            return {
                "success": True,
                "prescription_id": prescription_id,
                "message": "Prescripción guardada exitosamente"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Error guardando prescripción: {str(e)}")
            
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
    token_data: dict = MedicTokenRequired
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
    token_data: dict = MedicTokenRequired
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
    token_data: dict = MedicTokenRequired
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

# Rutas específicas que deben ir antes de las rutas con parámetros
@router.get("/patients/pending", response_class=HTMLResponse)
async def patients_pending_page(request: Request, user: dict = MedicTokenRequired):
    """Página de pacientes pendientes - redirige al dashboard"""
    return RedirectResponse(url="/medic/dashboard", status_code=302)

@router.get("/appointments/today", response_class=HTMLResponse)
async def appointments_today_page(request: Request, user: dict = MedicTokenRequired):
    """Página de citas de hoy - redirige al dashboard"""
    return RedirectResponse(url="/medic/dashboard", status_code=302)

@router.get("/medical-records", response_class=HTMLResponse)
async def medical_records_page(request: Request, user: dict = MedicTokenRequired):
    """Página de historia clínica - redirige al dashboard"""
    return RedirectResponse(url="/medic/dashboard", status_code=302)

@router.get("/prescriptions", response_class=HTMLResponse)
async def prescriptions_page(request: Request, user: dict = MedicTokenRequired):
    """Página de prescripciones - redirige al dashboard"""
    return RedirectResponse(url="/medic/dashboard", status_code=302)

@router.get("/patients/{patient_id}", response_class=HTMLResponse)
async def medic_patient_detail(
    request: Request,
    patient_id: int = Path(...),
    token_data: dict = MedicTokenRequired
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
    token_data: dict = MedicTokenRequired
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
    token_data: dict = MedicTokenRequired
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

@router.get("/api/appointments/today")
async def get_todays_appointments(token_data: dict = MedicTokenRequired):
    """Obtener citas de hoy del médico - versión compatible con Citus"""
    try:
        async with db_manager.AsyncSessionLocal() as session:
            # Obtener profesional_id del médico
            profesional_id = await get_profesional_id(session, token_data["user_id"])
            
            # Consulta simple sin JOINs complejos
            appointments_query = text("""
                SELECT cita_id, fecha_hora, duracion_minutos, motivo, estado, notas, paciente_id
                FROM cita
                WHERE profesional_id = :profesional_id
                    AND DATE(fecha_hora) = CURRENT_DATE
                ORDER BY fecha_hora
            """)
            
            result = await session.execute(appointments_query, {"profesional_id": profesional_id})
            appointments = []
            
            for row in result:
                # Obtener datos del paciente por separado
                patient_query = text("SELECT nombre, apellido, documento_id, contacto FROM paciente WHERE paciente_id = :paciente_id")
                patient_result = await session.execute(patient_query, {"paciente_id": row[6]})
                patient = patient_result.first()
                
                appointments.append({
                    "id": row[0],
                    "datetime": row[1].isoformat() if row[1] else None,
                    "time": row[1].strftime("%H:%M") if row[1] else None,
                    "duration": row[2],
                    "reason": row[3] or "Consulta médica",
                    "status": row[4],
                    "notes": row[5],
                    "patient": {
                        "name": f"{patient[0]} {patient[1]}" if patient else "Paciente no encontrado",
                        "document": patient[2] if patient else "",
                        "contact": patient[3] if patient else ""
                    }
                })
            
            return {
                "success": True,
                "appointments": appointments,
                "count": len(appointments)
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
    token_data: dict = MedicTokenRequired
):
    """Calculadora de IMC"""
    return templates.TemplateResponse("medic/tools/bmi_calculator.html", {
        "request": request,
        "current_user": token_data.get("full_name", token_data.get("username"))
    })

@router.post("/api/tools/calculate-bmi")
async def calculate_bmi(
    request: Request,
    token_data: dict = MedicTokenRequired
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
    token_data: dict = MedicTokenRequired
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
    token_data: dict = MedicTokenRequired
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
    token_data: dict = MedicTokenRequired
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
    token_data: dict = MedicTokenRequired
):
    """Página de recetas del médico"""
    return templates.TemplateResponse("medic/prescriptions.html", {
        "request": request,
        "current_user": token_data.get("full_name", token_data.get("username"))
    })

@router.get("/reports", response_class=HTMLResponse)
async def medic_reports_page(
    request: Request,
    token_data: dict = MedicTokenRequired
):
    """Página de reportes médicos"""
    return templates.TemplateResponse("medic/reports.html", {
        "request": request,
        "current_user": token_data.get("full_name", token_data.get("username"))
    })

@router.get("/new-patient", response_class=HTMLResponse)
async def new_patient_page(
    request: Request,
    token_data: dict = MedicTokenRequired
):
    """Página para registrar nuevo paciente"""
    return templates.TemplateResponse("medic/new_patient.html", {
        "request": request,
        "current_user": token_data.get("full_name", token_data.get("username"))
    })

# Endpoint de salud específico para médicos
@router.get("/health")
async def medic_health_check(request: Request, token_data: dict = MedicTokenRequired):
    """Health check específico para funcionalidades de médicos"""
    return {
        "status": "healthy",
        "module": "medic",
        "user": token_data.get("username"),
        "user_type": token_data.get("user_type"),
        "timestamp": datetime.now().isoformat()
    }

# ================================
# RUTAS ADICIONALES PARA NAVEGACIÓN
# ================================

