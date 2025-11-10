"""
Dashboard de Pacientes - Endpoints API simplificados
"""

import hashlib
import json
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from sqlalchemy import text
from app.config.database import db_manager


async def verify_patient_token(authorization: str) -> Optional[Dict]:
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


async def get_patient_dashboard_data(authorization: str):
    """Obtener datos completos del dashboard del paciente"""
    
    # Verificar token
    token_data = await verify_patient_token(authorization)
    if not token_data:
        raise HTTPException(status_code=401, detail="Token inválido o acceso no autorizado")
    
    user_id = token_data["user_id"]
    
    async with db_manager.AsyncSessionLocal() as session:
        # Obtener datos del paciente
        query_patient = text("""
            SELECT u.id, u.username, u.full_name, u.email, u.fhir_patient_id,
                   p.paciente_id, p.documento_id, p.nombre, p.apellido, 
                   p.sexo, p.fecha_nacimiento, p.contacto, p.ciudad
            FROM users u
            LEFT JOIN paciente p ON u.fhir_patient_id = p.paciente_id::varchar
            WHERE u.id = :user_id AND u.user_type = 'patient' AND u.is_active = true
        """)
        
        result = await session.execute(query_patient, {"user_id": user_id})
        patient_row = result.first()
        
        if not patient_row or not patient_row[6]:  # documento_id
            raise HTTPException(status_code=404, detail="Datos del paciente no encontrados")
        
        documento_id = patient_row[6]
        paciente_id = patient_row[5]
        
        # Obtener estadísticas
        stats_query = text("""
            SELECT 
                -- Próxima cita
                (SELECT EXTRACT(DAYS FROM MIN(fecha_hora) - NOW()) 
                 FROM cita 
                 WHERE documento_id = :doc_id AND paciente_id = :pac_id
                 AND fecha_hora > NOW() AND estado IN ('programada', 'confirmada')) as next_appointment_days,
                
                -- Medicamentos activos
                (SELECT COUNT(*) FROM medicamento
                 WHERE documento_id = :doc_id AND paciente_id = :pac_id
                 AND estado = 'activo') as active_medications,
                
                -- Exámenes pendientes
                (SELECT COUNT(*) FROM resultado_laboratorio
                 WHERE documento_id = :doc_id AND paciente_id = :pac_id
                 AND estado IN ('registrado', 'preliminar')) as pending_results,
                
                -- Condiciones activas
                (SELECT COUNT(*) FROM condicion
                 WHERE documento_id = :doc_id AND paciente_id = :pac_id
                 AND (fecha_fin IS NULL OR fecha_fin > CURRENT_DATE)) as active_conditions,
                
                -- Citas este año
                (SELECT COUNT(*) FROM encuentro
                 WHERE documento_id = :doc_id AND paciente_id = :pac_id
                 AND fecha >= DATE_TRUNC('year', CURRENT_DATE)) as total_appointments
        """)
        
        stats_result = await session.execute(stats_query, {
            "doc_id": documento_id, 
            "pac_id": paciente_id
        })
        stats = stats_result.first()
        
        # Obtener próximas citas
        appointments_query = text("""
            SELECT c.cita_id, c.fecha_hora, c.duracion_minutos, c.tipo_cita, c.motivo, c.estado,
                   COALESCE(p.nombre || ' ' || p.apellido, 'Por asignar') as doctor_name,
                   COALESCE(p.especialidad, 'Medicina General') as specialty,
                   COALESCE(u.nombre, 'Por definir') as ubicacion
            FROM cita c
            LEFT JOIN profesional p ON c.profesional_id = p.profesional_id
            LEFT JOIN ubicacion u ON c.ubicacion_id = u.ubicacion_id
            WHERE c.documento_id = :doc_id AND c.paciente_id = :pac_id
            AND c.fecha_hora > NOW()
            AND c.estado IN ('programada', 'confirmada')
            ORDER BY c.fecha_hora ASC
            LIMIT 5
        """)
        
        appointments_result = await session.execute(appointments_query, {
            "doc_id": documento_id,
            "pac_id": paciente_id
        })
        
        # Obtener medicamentos activos
        medications_query = text("""
            SELECT m.medicamento_id, m.nombre_medicamento, m.dosis, m.via_administracion,
                   m.frecuencia, m.fecha_inicio, m.fecha_fin,
                   COALESCE(p.nombre || ' ' || p.apellido, 'Médico') as prescriptor
            FROM medicamento m
            LEFT JOIN profesional p ON m.prescriptor_id = p.profesional_id
            WHERE m.documento_id = :doc_id AND m.paciente_id = :pac_id
            AND m.estado = 'activo'
            ORDER BY m.fecha_inicio DESC
            LIMIT 10
        """)
        
        medications_result = await session.execute(medications_query, {
            "doc_id": documento_id,
            "pac_id": paciente_id
        })
        
        # Obtener historial médico reciente
        history_query = text("""
            SELECT e.encuentro_id, e.fecha, e.motivo, e.diagnostico,
                   COALESCE(p.nombre || ' ' || p.apellido, 'Médico') as doctor_name,
                   COALESCE(p.especialidad, 'Medicina General') as specialty,
                   'encounter' as entry_type
            FROM encuentro e
            LEFT JOIN profesional p ON e.profesional_id = p.profesional_id
            WHERE e.documento_id = :doc_id AND e.paciente_id = :pac_id
            ORDER BY e.fecha DESC
            LIMIT 5
        """)
        
        history_result = await session.execute(history_query, {
            "doc_id": documento_id,
            "pac_id": paciente_id
        })
        
        # Obtener alergias importantes
        allergies_query = text("""
            SELECT descripcion_sustancia, severidad, manifestacion
            FROM alergia_intolerancia
            WHERE documento_id = :doc_id AND paciente_id = :pac_id
            AND estado = 'activa' AND severidad IN ('moderada', 'severa')
            ORDER BY 
                CASE severidad 
                    WHEN 'severa' THEN 1 
                    WHEN 'moderada' THEN 2 
                    ELSE 3 
                END
        """)
        
        allergies_result = await session.execute(allergies_query, {
            "doc_id": documento_id,
            "pac_id": paciente_id
        })
        
        # Procesar resultados
        next_appointment_days = int(stats[0]) if stats[0] is not None else None
        health_score = max(85 - (stats[3] * 5), 60) if stats[3] else 85
        
        # Formatear citas
        appointments = []
        for row in appointments_result:
            appointments.append({
                "id": row[0],
                "datetime": row[1].isoformat(),
                "duration": row[2],
                "type": row[3],
                "reason": row[4],
                "status": row[5],
                "doctor_name": row[6],
                "specialty": row[7],
                "location": row[8],
                "can_reschedule": True
            })
        
        # Formatear medicamentos
        medications = []
        for row in medications_result:
            medications.append({
                "id": row[0],
                "medication_name": row[1],
                "dosage": row[2],
                "route": row[3],
                "frequency": row[4],
                "start_date": row[5].isoformat() if row[5] else None,
                "end_date": row[6].isoformat() if row[6] else None,
                "prescriptor": row[7],
                "type_color": "primary",
                "icon": "capsule"
            })
        
        # Formatear historial
        history = []
        for row in history_result:
            history.append({
                "id": row[0],
                "date": row[1].isoformat(),
                "title": row[2] or "Consulta médica",
                "description": row[3] or "Sin descripción",
                "doctor_name": row[4],
                "specialty": row[5],
                "icon": "calendar-check",
                "type_color": "primary",
                "entry_type": row[6]
            })
        
        # Formatear alergias
        allergies = []
        for row in allergies_result:
            allergies.append({
                "allergen": row[0],
                "severity": row[1],
                "reaction": row[2]
            })
        
        # Construir respuesta
        return {
            "success": True,
            "patient_info": {
                "full_name": patient_row[2] or f"{patient_row[8]} {patient_row[9]}" if patient_row[8] else patient_row[1],
                "username": patient_row[1],
                "email": patient_row[3],
                "phone": patient_row[11],
                "city": patient_row[12],
                "birth_date": patient_row[10].isoformat() if patient_row[10] else None,
                "gender": patient_row[9]
            },
            "health_metrics": {
                "next_appointment_days": next_appointment_days,
                "active_medications": stats[1] or 0,
                "pending_results": stats[2] or 0,
                "health_score": health_score,
                "total_appointments": stats[4] or 0,
                "adherence_rate": 95,
                "health_score_change": 2,
                "last_results_days": 0
            },
            "upcoming_appointments": appointments,
            "medication_reminders": medications,
            "recent_medical_history": history,
            "important_allergies": allergies,
            "chronic_conditions": [],
            "emergency_contact": {
                "name": "No configurado",
                "phone": None,
                "relationship": None
            },
            "primary_doctor": {
                "name": "Por asignar",
                "phone": None
            },
            "unread_messages": 0,
            "health_alerts": []
        }