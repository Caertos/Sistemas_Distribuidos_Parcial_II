"""
Dashboard de Pacientes - API Endpoints
Endpoints específicos para el dashboard de pacientes con acceso seguro a datos personales
"""

import hashlib
import json
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, Header
from sqlalchemy import text
from app.config.database import db_manager

class PatientDashboardService:
    """Servicio para gestionar el dashboard de pacientes"""
    
    def __init__(self):
        self.db_manager = db_manager
    
    async def verify_patient_token(self, authorization: str) -> Optional[Dict]:
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
    
    async def get_patient_data(self, user_id: str) -> Optional[Dict]:
        """Obtener datos básicos del paciente"""
        async with self.db_manager.AsyncSessionLocal() as session:
            query = text("""
                SELECT u.id, u.username, u.full_name, u.email, u.fhir_patient_id,
                       p.paciente_id, p.documento_id, p.nombre, p.apellido, 
                       p.sexo, p.fecha_nacimiento, p.contacto, p.ciudad
                FROM users u
                LEFT JOIN paciente p ON u.fhir_patient_id = p.paciente_id::varchar
                WHERE u.id = :user_id AND u.user_type = 'patient' AND u.is_active = true
            """)
            
            result = await session.execute(query, {"user_id": user_id})
            row = result.first()
            
            if not row:
                return None
            
            return {
                "user_id": row[0],
                "username": row[1], 
                "full_name": row[2],
                "email": row[3],
                "fhir_patient_id": row[4],
                "paciente_id": row[5],
                "documento_id": row[6],
                "nombre": row[7],
                "apellido": row[8],
                "sexo": row[9],
                "fecha_nacimiento": row[10],
                "contacto": row[11],
                "ciudad": row[12]
            }
    
    async def get_patient_statistics(self, documento_id: int, paciente_id: int) -> Dict:
        """Obtener estadísticas del paciente"""
        async with self.db_manager.AsyncSessionLocal() as session:
            # Próxima cita
            query_cita = text("""
                SELECT fecha_hora, 
                       EXTRACT(DAYS FROM fecha_hora - NOW()) as dias_restantes
                FROM cita 
                WHERE documento_id = :documento_id AND paciente_id = :paciente_id
                AND fecha_hora > NOW() AND estado IN ('programada', 'confirmada')
                ORDER BY fecha_hora ASC
                LIMIT 1
            """)
            
            result_cita = await session.execute(query_cita, {
                "documento_id": documento_id, 
                "paciente_id": paciente_id
            })
            proxima_cita = result_cita.first()
            
            # Medicamentos activos
            query_medicamentos = text("""
                SELECT COUNT(*) FROM medicamento
                WHERE documento_id = :documento_id AND paciente_id = :paciente_id
                AND estado = 'activo'
            """)
            
            result_medicamentos = await session.execute(query_medicamentos, {
                "documento_id": documento_id,
                "paciente_id": paciente_id
            })
            medicamentos_activos = result_medicamentos.scalar() or 0
            
            # Exámenes pendientes (resultados sin recibir)
            query_examenes = text("""
                SELECT COUNT(*) FROM resultado_laboratorio
                WHERE documento_id = :documento_id AND paciente_id = :paciente_id
                AND estado IN ('registrado', 'preliminar')
            """)
            
            result_examenes = await session.execute(query_examenes, {
                "documento_id": documento_id,
                "paciente_id": paciente_id
            })
            examenes_pendientes = result_examenes.scalar() or 0
            
            # Condiciones activas para índice de salud
            query_condiciones = text("""
                SELECT COUNT(*) FROM condicion
                WHERE documento_id = :documento_id AND paciente_id = :paciente_id
                AND (fecha_fin IS NULL OR fecha_fin > CURRENT_DATE)
            """)
            
            result_condiciones = await session.execute(query_condiciones, {
                "documento_id": documento_id,
                "paciente_id": paciente_id
            })
            condiciones_activas = result_condiciones.scalar() or 0
            
            return {
                "next_appointment_days": int(proxima_cita[1]) if proxima_cita else None,
                "next_appointment_date": proxima_cita[0] if proxima_cita else None,
                "active_medications": medicamentos_activos,
                "pending_results": examenes_pendientes,
                "health_score": max(85 - (condiciones_activas * 5), 60),  # Índice básico
                "total_appointments": await self._count_appointments_this_year(session, documento_id, paciente_id),
                "adherence_rate": 95,  # Valor por defecto
                "health_score_change": 2,  # Valor por defecto
                "last_results_days": await self._days_since_last_result(session, documento_id, paciente_id)
            }
    
    async def _count_appointments_this_year(self, session, documento_id: int, paciente_id: int) -> int:
        """Contar citas este año"""
        query = text("""
            SELECT COUNT(*) FROM encuentro
            WHERE documento_id = :documento_id AND paciente_id = :paciente_id
            AND fecha >= DATE_TRUNC('year', CURRENT_DATE)
        """)
        
        result = await session.execute(query, {
            "documento_id": documento_id,
            "paciente_id": paciente_id
        })
        return result.scalar() or 0
    
    async def _days_since_last_result(self, session, documento_id: int, paciente_id: int) -> int:
        """Días desde último resultado"""
        query = text("""
            SELECT EXTRACT(DAYS FROM NOW() - MAX(fecha_resultado)) as dias
            FROM resultado_laboratorio
            WHERE documento_id = :documento_id AND paciente_id = :paciente_id
            AND estado = 'final'
        """)
        
        result = await session.execute(query, {
            "documento_id": documento_id,
            "paciente_id": paciente_id
        })
        return int(result.scalar() or 0)
    
    async def get_upcoming_appointments(self, documento_id: int, paciente_id: int, limit: int = 5) -> List[Dict]:
        """Obtener próximas citas"""
        async with self.db_manager.AsyncSessionLocal() as session:
            query = text("""
                SELECT c.cita_id, c.fecha_hora, c.duracion_minutos, c.tipo_cita, c.motivo, c.estado,
                       p.nombre || ' ' || p.apellido as doctor_name,
                       p.especialidad,
                       u.nombre as ubicacion
                FROM cita c
                LEFT JOIN profesional p ON c.profesional_id = p.profesional_id
                LEFT JOIN ubicacion u ON c.ubicacion_id = u.ubicacion_id
                WHERE c.documento_id = :documento_id AND c.paciente_id = :paciente_id
                AND c.fecha_hora > NOW()
                AND c.estado IN ('programada', 'confirmada')
                ORDER BY c.fecha_hora ASC
                LIMIT :limit
            """)
            
            result = await session.execute(query, {
                "documento_id": documento_id,
                "paciente_id": paciente_id,
                "limit": limit
            })
            
            appointments = []
            for row in result:
                appointments.append({
                    "id": row[0],
                    "date": row[1].date(),
                    "time": row[1].time(),
                    "datetime": row[1],
                    "duration": row[2],
                    "type": row[3],
                    "reason": row[4],
                    "status": row[5],
                    "doctor_name": row[6] or "Por asignar",
                    "specialty": row[7] or "Medicina General",
                    "location": row[8] or "Por definir",
                    "can_reschedule": True,  # Lógica de negocio
                    "preparation_notes": None  # Podría venir de otra tabla
                })
            
            return appointments
    
    async def get_active_medications(self, documento_id: int, paciente_id: int) -> List[Dict]:
        """Obtener medicamentos activos con recordatorios"""
        async with self.db_manager.AsyncSessionLocal() as session:
            query = text("""
                SELECT m.medicamento_id, m.nombre_medicamento, m.dosis, m.via_administracion,
                       m.frecuencia, m.fecha_inicio, m.fecha_fin,
                       p.nombre || ' ' || p.apellido as prescriptor
                FROM medicamento m
                LEFT JOIN profesional p ON m.prescriptor_id = p.profesional_id
                WHERE m.documento_id = :documento_id AND m.paciente_id = :paciente_id
                AND m.estado = 'activo'
                ORDER BY m.fecha_inicio DESC
            """)
            
            result = await session.execute(query, {
                "documento_id": documento_id,
                "paciente_id": paciente_id
            })
            
            medications = []
            for row in result:
                # Simular recordatorios basados en frecuencia
                next_time = self._calculate_next_dose(row[4])
                
                medications.append({
                    "id": row[0],
                    "medication_name": row[1],
                    "dosage": row[2],
                    "route": row[3],
                    "frequency": row[4],
                    "start_date": row[5],
                    "end_date": row[6],
                    "prescriptor": row[7] or "Médico",
                    "next_time": next_time,
                    "type_color": "primary",
                    "icon": "capsule"
                })
            
            return medications
    
    def _calculate_next_dose(self, frequency: str) -> str:
        """Calcular próxima dosis basada en frecuencia"""
        now = datetime.now()
        
        if "8 horas" in frequency.lower():
            next_dose = now.replace(hour=(now.hour // 8 + 1) * 8 % 24, minute=0, second=0)
        elif "12 horas" in frequency.lower():
            next_dose = now.replace(hour=(now.hour // 12 + 1) * 12 % 24, minute=0, second=0)
        elif "24 horas" in frequency.lower():
            next_dose = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0)
        else:
            next_dose = now + timedelta(hours=6)  # Por defecto
        
        if next_dose <= now:
            next_dose += timedelta(days=1)
            
        return next_dose.strftime("%H:%M")
    
    async def get_medical_history(self, documento_id: int, paciente_id: int, limit: int = 10) -> List[Dict]:
        """Obtener historial médico reciente"""
        async with self.db_manager.AsyncSessionLocal() as session:
            query = text("""
                SELECT e.encuentro_id, e.fecha, e.motivo, e.diagnostico,
                       p.nombre || ' ' || p.apellido as doctor_name,
                       p.especialidad,
                       'encounter' as entry_type
                FROM encuentro e
                LEFT JOIN profesional p ON e.profesional_id = p.profesional_id
                WHERE e.documento_id = :documento_id AND e.paciente_id = :paciente_id
                UNION ALL
                SELECT c.condicion_id, c.created_at, c.descripcion, 
                       'Diagnóstico: ' || c.gravedad,
                       'Sistema', 'Diagnóstico',
                       'condition' as entry_type
                FROM condicion c
                WHERE c.documento_id = :documento_id AND c.paciente_id = :paciente_id
                ORDER BY fecha DESC
                LIMIT :limit
            """)
            
            result = await session.execute(query, {
                "documento_id": documento_id,
                "paciente_id": paciente_id,
                "limit": limit
            })
            
            history = []
            for row in result:
                entry_type = row[6]
                
                if entry_type == 'encounter':
                    icon = "calendar-check"
                    type_color = "primary"
                    title = row[2] or "Consulta médica"
                else:  # condition
                    icon = "heart-pulse"
                    type_color = "warning"
                    title = row[2]
                
                history.append({
                    "id": row[0],
                    "date": row[1],
                    "title": title,
                    "description": row[3],
                    "doctor_name": row[4],
                    "specialty": row[5],
                    "icon": icon,
                    "type_color": type_color,
                    "entry_type": entry_type
                })
            
            return history
    
    async def get_allergies_and_conditions(self, documento_id: int, paciente_id: int) -> Dict:
        """Obtener alergias y condiciones importantes"""
        async with self.db_manager.AsyncSessionLocal() as session:
            # Alergias importantes
            query_allergies = text("""
                SELECT descripcion_sustancia, severidad, manifestacion
                FROM alergia_intolerancia
                WHERE documento_id = :documento_id AND paciente_id = :paciente_id
                AND estado = 'activa' AND severidad IN ('moderada', 'severa')
                ORDER BY 
                    CASE severidad 
                        WHEN 'severa' THEN 1 
                        WHEN 'moderada' THEN 2 
                        ELSE 3 
                    END
            """)
            
            result_allergies = await session.execute(query_allergies, {
                "documento_id": documento_id,
                "paciente_id": paciente_id
            })
            
            # Condiciones crónicas
            query_conditions = text("""
                SELECT descripcion, gravedad
                FROM condicion
                WHERE documento_id = :documento_id AND paciente_id = :paciente_id
                AND (fecha_fin IS NULL OR fecha_fin > CURRENT_DATE)
                AND gravedad IN ('Moderada', 'Severa')
            """)
            
            result_conditions = await session.execute(query_conditions, {
                "documento_id": documento_id,
                "paciente_id": paciente_id
            })
            
            allergies = [{"allergen": row[0], "severity": row[1], "reaction": row[2]} 
                        for row in result_allergies]
            
            conditions = [{"name": row[0], "severity": row[1]} 
                         for row in result_conditions]
            
            return {
                "important_allergies": allergies,
                "chronic_conditions": conditions
            }

# Instancia global del servicio
patient_service = PatientDashboardService()