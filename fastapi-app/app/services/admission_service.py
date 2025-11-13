"""
Admission Service - Servicio de negocio para gestión de admisiones y triage
Implementa operaciones para el sistema de admisión de pacientes por enfermería
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, text, func
from datetime import datetime, date, timedelta

from app.models.orm import AdmissionORM, PatientORM
from .base import DistributedService, ResourceNotFoundException, ValidationException


class AdmissionService(DistributedService):
    """
    Servicio de negocio para gestión de admisiones y triage
    
    Implementa operaciones para:
    - Crear admisiones con datos de triage
    - Listar citas pendientes de admisión
    - Actualizar información de triage
    - Gestionar el flujo de admisión de pacientes
    """
    
    def __init__(self):
        super().__init__(
            pydantic_model=None,  # No usamos modelo Pydantic por ahora
            orm_model=AdmissionORM,
            create_model=None,
            update_model=None,
            resource_name="Admission"
        )
    
    async def generar_codigo_admision(self, session: AsyncSession) -> str:
        """
        Genera un código único de admisión usando la función SQL
        
        Args:
            session: Sesión de base de datos
            
        Returns:
            Código de admisión único (ej: ADM-20241112-0001)
        """
        try:
            result = await session.execute(text("SELECT generar_codigo_admision()"))
            codigo = result.scalar()
            return codigo
        except Exception as e:
            self.logger.error(f"Error generating admission code: {str(e)}")
            # Fallback: generar código manualmente
            fecha_actual = datetime.now().strftime('%Y%m%d')
            # Contar admisiones del día
            count_query = select(func.count(AdmissionORM.admission_id)).where(
                AdmissionORM.admission_id.like(f'ADM-{fecha_actual}-%')
            )
            result = await session.execute(count_query)
            contador = result.scalar() + 1
            return f'ADM-{fecha_actual}-{contador:04d}'
    
    async def crear_admision(
        self,
        session: AsyncSession,
        documento_id: int,
        paciente_id: int,
        cita_id: Optional[int],
        motivo_consulta: str,
        admitido_por: str,
        prioridad: str = 'normal',
        # Signos vitales
        presion_sistolica: Optional[int] = None,
        presion_diastolica: Optional[int] = None,
        frecuencia_cardiaca: Optional[int] = None,
        frecuencia_respiratoria: Optional[int] = None,
        temperatura: Optional[float] = None,
        saturacion_oxigeno: Optional[int] = None,
        peso: Optional[float] = None,
        altura: Optional[int] = None,
        # Información adicional
        nivel_dolor: Optional[int] = None,
        nivel_conciencia: Optional[str] = None,
        sintomas_principales: Optional[str] = None,
        alergias_conocidas: Optional[str] = None,
        medicamentos_actuales: Optional[str] = None,
        notas_enfermeria: Optional[str] = None,
        observaciones: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crea una nueva admisión con datos de triage
        
        Args:
            session: Sesión de base de datos
            documento_id: ID del documento del paciente
            paciente_id: ID del paciente
            cita_id: ID de la cita (opcional si es admisión sin cita previa)
            motivo_consulta: Motivo de la consulta
            admitido_por: Username del usuario que realiza la admisión
            prioridad: Nivel de prioridad (urgente, normal, baja)
            ... (resto de parámetros de triage)
            
        Returns:
            Diccionario con la admisión creada
        """
        try:
            # Validar que el paciente existe
            patient_query = select(PatientORM).where(
                and_(
                    PatientORM.documento_id == documento_id,
                    PatientORM.paciente_id == paciente_id
                )
            )
            patient_result = await session.execute(patient_query)
            patient = patient_result.scalar_one_or_none()
            
            if not patient:
                raise ResourceNotFoundException(
                    f"Patient with documento_id={documento_id}, paciente_id={paciente_id} not found"
                )
            
            # Generar código de admisión
            admission_id = await self.generar_codigo_admision(session)
            
            # Crear objeto de admisión
            admision = AdmissionORM(
                admission_id=admission_id,
                documento_id=documento_id,
                paciente_id=paciente_id,
                cita_id=cita_id,
                fecha_admision=datetime.now(),
                admitido_por=admitido_por,
                motivo_consulta=motivo_consulta,
                prioridad=prioridad,
                estado_admision='activa',
                # Signos vitales
                presion_arterial_sistolica=presion_sistolica,
                presion_arterial_diastolica=presion_diastolica,
                frecuencia_cardiaca=frecuencia_cardiaca,
                frecuencia_respiratoria=frecuencia_respiratoria,
                temperatura=temperatura,
                saturacion_oxigeno=saturacion_oxigeno,
                peso=peso,
                altura=altura,
                # Información adicional
                nivel_dolor=nivel_dolor,
                nivel_conciencia=nivel_conciencia,
                sintomas_principales=sintomas_principales,
                alergias_conocidas=alergias_conocidas,
                medicamentos_actuales=medicamentos_actuales,
                notas_enfermeria=notas_enfermeria,
                observaciones=observaciones
            )
            
            session.add(admision)
            
            # Si hay cita asociada, actualizar su estado de admisión
            if cita_id:
                update_cita = text("""
                    UPDATE cita 
                    SET admission_id = :admission_id,
                        estado_admision = 'admitida',
                        fecha_admision = NOW(),
                        admitido_por = :admitido_por
                    WHERE documento_id = :documento_id AND cita_id = :cita_id
                """)
                await session.execute(update_cita, {
                    'admission_id': admission_id,
                    'admitido_por': admitido_por,
                    'documento_id': documento_id,
                    'cita_id': cita_id
                })
            
            await session.commit()
            await session.refresh(admision)
            
            self.logger.info(f"Created admission {admission_id} for patient {documento_id}/{paciente_id}")
            
            return admision.to_dict()
            
        except ResourceNotFoundException:
            raise
        except Exception as e:
            await session.rollback()
            self.logger.error(f"Error creating admission: {str(e)}")
            raise ValidationException(f"Error creating admission: {str(e)}")
    
    async def obtener_citas_pendientes(
        self,
        session: AsyncSession,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene lista de citas pendientes de admisión
        
        Args:
            session: Sesión de base de datos
            fecha_desde: Fecha inicial para filtrar (opcional)
            fecha_hasta: Fecha final para filtrar (opcional)
            limit: Número máximo de resultados
            
        Returns:
            Lista de citas pendientes con información del paciente
        """
        try:
            # Usar la vista creada en SQL
            query = text("""
                SELECT 
                    cita_id,
                    documento_id,
                    paciente_id,
                    fecha_hora,
                    tipo_cita,
                    motivo,
                    estado,
                    estado_admision,
                    nombre,
                    apellido,
                    sexo,
                    fecha_nacimiento,
                    contacto,
                    edad,
                    profesional_nombre,
                    profesional_apellido,
                    especialidad
                FROM vista_citas_pendientes_admision
                WHERE 1=1
                    AND (:fecha_desde IS NULL OR fecha_hora >= :fecha_desde)
                    AND (:fecha_hasta IS NULL OR fecha_hora <= :fecha_hasta)
                ORDER BY fecha_hora ASC
                LIMIT :limit
            """)
            
            params = {
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta,
                'limit': limit
            }
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            citas = []
            for row in rows:
                citas.append({
                    'cita_id': row[0],
                    'documento_id': row[1],
                    'paciente_id': row[2],
                    'fecha_hora': row[3].isoformat() if row[3] else None,
                    'tipo_cita': row[4],
                    'motivo': row[5],
                    'estado': row[6],
                    'estado_admision': row[7],
                    'paciente': {
                        'nombre': row[8],
                        'apellido': row[9],
                        'sexo': row[10],
                        'fecha_nacimiento': row[11].isoformat() if row[11] else None,
                        'contacto': row[12],
                        'edad': int(row[13]) if row[13] else None
                    },
                    'profesional': {
                        'nombre': row[14],
                        'apellido': row[15],
                        'especialidad': row[16]
                    } if row[14] else None
                })
            
            return citas
            
        except Exception as e:
            self.logger.error(f"Error fetching pending appointments: {str(e)}")
            raise ValidationException(f"Error fetching pending appointments: {str(e)}")
    
    async def obtener_admisiones_activas(
        self,
        session: AsyncSession,
        prioridad: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene lista de admisiones activas
        
        Args:
            session: Sesión de base de datos
            prioridad: Filtrar por prioridad (urgente, normal, baja)
            limit: Número máximo de resultados
            
        Returns:
            Lista de admisiones activas con información completa
        """
        try:
            query = text("""
                SELECT *
                FROM vista_admisiones_completas
                WHERE estado_admision = 'activa'
                    AND (:prioridad IS NULL OR prioridad = :prioridad)
                ORDER BY 
                    CASE prioridad 
                        WHEN 'urgente' THEN 1
                        WHEN 'normal' THEN 2
                        WHEN 'baja' THEN 3
                    END,
                    fecha_admision DESC
                LIMIT :limit
            """)
            
            params = {
                'prioridad': prioridad,
                'limit': limit
            }
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            admisiones = []
            for row in rows:
                # Mapear columnas de la vista
                admisiones.append({
                    'admission_id': row[0],
                    'documento_id': row[1],
                    'paciente_id': row[2],
                    'cita_id': row[3],
                    'fecha_admision': row[4].isoformat() if row[4] else None,
                    'admitido_por': row[5],
                    'motivo_consulta': row[6],
                    'prioridad': row[7],
                    'estado_admision': row[8],
                    'signos_vitales': {
                        'presion_sistolica': row[9],
                        'presion_diastolica': row[10],
                        'frecuencia_cardiaca': row[11],
                        'frecuencia_respiratoria': row[12],
                        'temperatura': float(row[13]) if row[13] else None,
                        'saturacion_oxigeno': row[14],
                        'peso': float(row[15]) if row[15] else None,
                        'altura': row[16],
                        'imc': float(row[17]) if row[17] else None,
                        'pam': row[18]
                    },
                    'evaluacion': {
                        'nivel_dolor': row[19],
                        'nivel_conciencia': row[20],
                        'sintomas_principales': row[21]
                    },
                    'notas_enfermeria': row[22],
                    'paciente': {
                        'nombre': row[23],
                        'apellido': row[24],
                        'sexo': row[25],
                        'fecha_nacimiento': row[26].isoformat() if row[26] else None,
                        'edad': int(row[27]) if row[27] else None
                    },
                    'cita': {
                        'fecha_hora': row[28].isoformat() if row[28] else None,
                        'profesional_id': row[29],
                        'tipo_cita': row[30]
                    } if row[28] else None
                })
            
            return admisiones
            
        except Exception as e:
            self.logger.error(f"Error fetching active admissions: {str(e)}")
            raise ValidationException(f"Error fetching active admissions: {str(e)}")
    
    async def obtener_admision_por_codigo(
        self,
        session: AsyncSession,
        admission_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene una admisión específica por su código
        
        Args:
            session: Sesión de base de datos
            admission_id: Código de admisión
            
        Returns:
            Diccionario con la admisión o None si no existe
        """
        try:
            admision = await AdmissionORM.get_by_admission_id(session, admission_id)
            
            if not admision:
                return None
            
            return admision.to_dict()
            
        except Exception as e:
            self.logger.error(f"Error fetching admission {admission_id}: {str(e)}")
            raise ValidationException(f"Error fetching admission: {str(e)}")
    
    async def actualizar_triage(
        self,
        session: AsyncSession,
        admission_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Actualiza los datos de triage de una admisión existente
        
        Args:
            session: Sesión de base de datos
            admission_id: Código de admisión
            **kwargs: Campos a actualizar
            
        Returns:
            Diccionario con la admisión actualizada
        """
        try:
            # Buscar la admisión
            query = select(AdmissionORM).where(
                AdmissionORM.admission_id == admission_id
            )
            result = await session.execute(query)
            admision = result.scalar_one_or_none()
            
            if not admision:
                raise ResourceNotFoundException(f"Admission {admission_id} not found")
            
            # Actualizar campos permitidos
            campos_permitidos = {
                'presion_arterial_sistolica', 'presion_arterial_diastolica',
                'frecuencia_cardiaca', 'frecuencia_respiratoria',
                'temperatura', 'saturacion_oxigeno', 'peso', 'altura',
                'nivel_dolor', 'nivel_conciencia', 'sintomas_principales',
                'alergias_conocidas', 'medicamentos_actuales',
                'notas_enfermeria', 'observaciones', 'prioridad',
                'motivo_consulta'
            }
            
            for key, value in kwargs.items():
                if key in campos_permitidos and hasattr(admision, key):
                    setattr(admision, key, value)
            
            await session.commit()
            await session.refresh(admision)
            
            self.logger.info(f"Updated triage for admission {admission_id}")
            
            return admision.to_dict()
            
        except ResourceNotFoundException:
            raise
        except Exception as e:
            await session.rollback()
            self.logger.error(f"Error updating triage: {str(e)}")
            raise ValidationException(f"Error updating triage: {str(e)}")
    
    async def cambiar_estado_admision(
        self,
        session: AsyncSession,
        admission_id: str,
        nuevo_estado: str
    ) -> Dict[str, Any]:
        """
        Cambia el estado de una admisión
        
        Args:
            session: Sesión de base de datos
            admission_id: Código de admisión
            nuevo_estado: Nuevo estado (activa, atendida, cancelada)
            
        Returns:
            Diccionario con la admisión actualizada
        """
        try:
            if nuevo_estado not in ['activa', 'atendida', 'cancelada']:
                raise ValidationException(f"Invalid state: {nuevo_estado}")
            
            query = select(AdmissionORM).where(
                AdmissionORM.admission_id == admission_id
            )
            result = await session.execute(query)
            admision = result.scalar_one_or_none()
            
            if not admision:
                raise ResourceNotFoundException(f"Admission {admission_id} not found")
            
            admision.estado_admision = nuevo_estado
            
            await session.commit()
            await session.refresh(admision)
            
            self.logger.info(f"Changed admission {admission_id} state to {nuevo_estado}")
            
            return admision.to_dict()
            
        except (ResourceNotFoundException, ValidationException):
            raise
        except Exception as e:
            await session.rollback()
            self.logger.error(f"Error changing admission state: {str(e)}")
            raise ValidationException(f"Error changing admission state: {str(e)}")
    
    async def obtener_estadisticas_admision(
        self,
        session: AsyncSession,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Obtiene estadísticas del sistema de admisión
        
        Args:
            session: Sesión de base de datos
            fecha_desde: Fecha inicial (opcional)
            fecha_hasta: Fecha final (opcional)
            
        Returns:
            Diccionario con estadísticas
        """
        try:
            # Si no se especifican fechas, usar últimos 7 días
            if not fecha_desde:
                fecha_desde = date.today() - timedelta(days=7)
            if not fecha_hasta:
                fecha_hasta = date.today()
            
            query = text("""
                SELECT 
                    COUNT(*) as total_admisiones,
                    COUNT(*) FILTER (WHERE estado_admision = 'activa') as admisiones_activas,
                    COUNT(*) FILTER (WHERE estado_admision = 'atendida') as admisiones_atendidas,
                    COUNT(*) FILTER (WHERE prioridad = 'urgente') as admisiones_urgentes,
                    COUNT(*) FILTER (WHERE prioridad = 'normal') as admisiones_normales,
                    COUNT(*) FILTER (WHERE prioridad = 'baja') as admisiones_bajas,
                    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))/60) as tiempo_promedio_minutos
                FROM admision
                WHERE fecha_admision >= :fecha_desde 
                    AND fecha_admision <= :fecha_hasta + INTERVAL '1 day'
            """)
            
            result = await session.execute(query, {
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta
            })
            row = result.fetchone()
            
            # Obtener citas pendientes
            query_pendientes = text("""
                SELECT COUNT(*) 
                FROM cita 
                WHERE (estado_admision = 'pendiente' OR estado_admision IS NULL)
                    AND fecha_hora >= NOW()
            """)
            result_pendientes = await session.execute(query_pendientes)
            citas_pendientes = result_pendientes.scalar()
            
            return {
                'total_admisiones': row[0] or 0,
                'admisiones_activas': row[1] or 0,
                'admisiones_atendidas': row[2] or 0,
                'admisiones_urgentes': row[3] or 0,
                'admisiones_normales': row[4] or 0,
                'admisiones_bajas': row[5] or 0,
                'tiempo_promedio_atencion_minutos': round(row[6], 2) if row[6] else 0,
                'citas_pendientes_admision': citas_pendientes or 0,
                'periodo': {
                    'desde': fecha_desde.isoformat(),
                    'hasta': fecha_hasta.isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching admission statistics: {str(e)}")
            raise ValidationException(f"Error fetching statistics: {str(e)}")
    
    async def obtener_admision_por_id(
        self,
        session: AsyncSession,
        admission_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene una admisión por su ID único
        
        Args:
            session: Sesión de base de datos
            admission_id: Código de admisión único
            
        Returns:
            Diccionario con datos de la admisión o None si no existe
        """
        try:
            query = select(AdmissionORM).where(
                AdmissionORM.admission_id == admission_id
            )
            result = await session.execute(query)
            admision = result.scalar_one_or_none()
            
            if not admision:
                return None
            
            return admision.to_dict()
            
        except Exception as e:
            self.logger.error(f"Error fetching admission by ID: {str(e)}")
            raise ValidationException(f"Error fetching admission: {str(e)}")
    
    async def buscar_admisiones_por_paciente(
        self,
        session: AsyncSession,
        documento_id: int,
        estado: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Busca admisiones de un paciente específico
        
        Args:
            session: Sesión de base de datos
            documento_id: Documento del paciente
            estado: Filtrar por estado (opcional)
            limit: Número máximo de resultados
            
        Returns:
            Lista de admisiones del paciente
        """
        try:
            conditions = [AdmissionORM.paciente_documento_id == documento_id]
            
            if estado:
                conditions.append(AdmissionORM.estado_admision == estado)
            
            query = (
                select(AdmissionORM)
                .where(and_(*conditions))
                .order_by(AdmissionORM.fecha_admision.desc())
                .limit(limit)
            )
            
            result = await session.execute(query)
            admisiones = result.scalars().all()
            
            return [adm.to_dict() for adm in admisiones]
            
        except Exception as e:
            self.logger.error(f"Error searching admissions by patient: {str(e)}")
            raise ValidationException(f"Error searching admissions: {str(e)}")


# Exportar servicio
__all__ = ['AdmissionService']
