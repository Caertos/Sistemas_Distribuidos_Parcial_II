"""
Admission ORM Model - Mapeo a tabla 'admision'
Modelo SQLAlchemy para el sistema de admisión y triage de pacientes
"""

from sqlalchemy import (
    Column, BigInteger, Text, Integer, DECIMAL, String,
    PrimaryKeyConstraint, Index, CheckConstraint, ForeignKey
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import text, func

from .base import (
    DistributedModel, AuditMixin,
    CitusTableConfig, get_table_comment
)


class AdmissionORM(DistributedModel, AuditMixin):
    """
    Modelo ORM para la tabla 'admision'
    
    Tabla distribuida por documento_id en Citus para co-localizar
    todos los datos relacionados con un paciente específico.
    Gestiona la admisión de pacientes y el triage inicial.
    """
    
    __tablename__ = "admision"
    __table_args__ = (
        # Primary Key compuesta requerida por Citus (incluye columna de distribución)
        PrimaryKeyConstraint("documento_id", "admission_id"),
        
        # Índices para optimizar consultas comunes
        Index("idx_admision_fecha", "fecha_admision"),
        Index("idx_admision_paciente", "documento_id", "paciente_id"),
        Index("idx_admision_cita", "documento_id", "cita_id"),
        Index("idx_admision_estado", "estado_admision"),
        Index("idx_admision_prioridad", "prioridad"),
        Index("idx_admision_admitido_por", "admitido_por"),
        Index("idx_admision_codigo", "admission_id"),
        
        # Constraints de validación
        CheckConstraint(
            "prioridad IN ('urgente', 'normal', 'baja')",
            name="chk_admision_prioridad"
        ),
        CheckConstraint(
            "estado_admision IN ('activa', 'atendida', 'cancelada')",
            name="chk_admision_estado"
        ),
        CheckConstraint(
            "nivel_dolor >= 0 AND nivel_dolor <= 10",
            name="chk_admision_nivel_dolor"
        ),
        CheckConstraint(
            "saturacion_oxigeno >= 0 AND saturacion_oxigeno <= 100",
            name="chk_admision_saturacion"
        ),
        CheckConstraint(
            "temperatura > 30 AND temperatura < 45",
            name="chk_admision_temperatura"
        ),
        CheckConstraint(
            "nivel_conciencia IN ('alerta', 'somnoliento', 'confuso', 'inconsciente')",
            name="chk_admision_nivel_conciencia"
        ),
        
        # Comentario de tabla
        {"comment": get_table_comment("Admission", is_distributed=True)}
    )
    
    # ========================================================================
    # PRIMARY KEY FIELDS
    # ========================================================================
    
    admission_id = Column(
        Text,
        nullable=False,
        comment="Código único de admisión (ej: ADM-20241112-0001)"
    )
    
    # Campo documento_id ya definido en DistributedModel
    
    # ========================================================================
    # INFORMACIÓN DE ADMISIÓN
    # ========================================================================
    
    paciente_id = Column(
        BigInteger,
        nullable=False,
        comment="ID del paciente"
    )
    
    cita_id = Column(
        BigInteger,
        nullable=True,
        comment="ID de la cita asociada (si existe)"
    )
    
    fecha_admision = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Fecha y hora de la admisión"
    )
    
    admitido_por = Column(
        Text,
        nullable=True,
        comment="Username del usuario que realizó la admisión"
    )
    
    motivo_consulta = Column(
        Text,
        nullable=True,
        comment="Motivo de consulta del paciente"
    )
    
    prioridad = Column(
        Text,
        nullable=False,
        server_default=text("'normal'"),
        comment="Nivel de prioridad: urgente, normal, baja"
    )
    
    estado_admision = Column(
        Text,
        nullable=False,
        server_default=text("'activa'"),
        comment="Estado de la admisión: activa, atendida, cancelada"
    )
    
    # ========================================================================
    # DATOS DE TRIAGE (SIGNOS VITALES)
    # ========================================================================
    
    presion_arterial_sistolica = Column(
        Integer,
        nullable=True,
        comment="Presión arterial sistólica en mmHg"
    )
    
    presion_arterial_diastolica = Column(
        Integer,
        nullable=True,
        comment="Presión arterial diastólica en mmHg"
    )
    
    frecuencia_cardiaca = Column(
        Integer,
        nullable=True,
        comment="Frecuencia cardíaca en latidos por minuto"
    )
    
    frecuencia_respiratoria = Column(
        Integer,
        nullable=True,
        comment="Frecuencia respiratoria en respiraciones por minuto"
    )
    
    temperatura = Column(
        DECIMAL(4, 2),
        nullable=True,
        comment="Temperatura corporal en grados Celsius"
    )
    
    saturacion_oxigeno = Column(
        Integer,
        nullable=True,
        comment="Saturación de oxígeno en porcentaje (0-100)"
    )
    
    peso = Column(
        DECIMAL(5, 2),
        nullable=True,
        comment="Peso en kilogramos"
    )
    
    altura = Column(
        Integer,
        nullable=True,
        comment="Altura en centímetros"
    )
    
    # ========================================================================
    # INFORMACIÓN ADICIONAL DE TRIAGE
    # ========================================================================
    
    nivel_dolor = Column(
        Integer,
        nullable=True,
        comment="Escala de dolor de 0 (sin dolor) a 10 (dolor máximo)"
    )
    
    nivel_conciencia = Column(
        Text,
        nullable=True,
        comment="Nivel de conciencia: alerta, somnoliento, confuso, inconsciente"
    )
    
    sintomas_principales = Column(
        Text,
        nullable=True,
        comment="Descripción de los síntomas principales"
    )
    
    alergias_conocidas = Column(
        Text,
        nullable=True,
        comment="Alergias conocidas del paciente"
    )
    
    medicamentos_actuales = Column(
        Text,
        nullable=True,
        comment="Medicamentos que está tomando actualmente"
    )
    
    # ========================================================================
    # NOTAS Y OBSERVACIONES
    # ========================================================================
    
    notas_enfermeria = Column(
        Text,
        nullable=True,
        comment="Notas del personal de enfermería"
    )
    
    observaciones = Column(
        Text,
        nullable=True,
        comment="Observaciones generales"
    )
    
    # Campos de auditoría ya definidos en AuditMixin (created_at, updated_at)
    
    def __repr__(self) -> str:
        """Representación string del modelo"""
        return (
            f"<AdmissionORM("
            f"admission_id='{self.admission_id}', "
            f"documento_id={self.documento_id}, "
            f"paciente_id={self.paciente_id}, "
            f"prioridad='{self.prioridad}', "
            f"estado='{self.estado_admision}'"
            f")>"
        )
    
    def calcular_imc(self) -> float:
        """
        Calcula el Índice de Masa Corporal (IMC)
        
        Returns:
            IMC calculado o None si faltan datos
        """
        if self.peso and self.altura and self.altura > 0:
            altura_metros = self.altura / 100.0
            imc = float(self.peso) / (altura_metros ** 2)
            return round(imc, 2)
        return None
    
    def calcular_pam(self) -> int:
        """
        Calcula la Presión Arterial Media (PAM)
        PAM = ((2 × diastólica) + sistólica) / 3
        
        Returns:
            PAM calculada o None si faltan datos
        """
        if self.presion_arterial_sistolica and self.presion_arterial_diastolica:
            pam = ((2 * self.presion_arterial_diastolica) + self.presion_arterial_sistolica) / 3
            return int(pam)
        return None
    
    def get_presion_arterial(self) -> str:
        """
        Obtiene la presión arterial en formato legible
        
        Returns:
            String con formato "120/80" o "N/A" si no hay datos
        """
        if self.presion_arterial_sistolica and self.presion_arterial_diastolica:
            return f"{self.presion_arterial_sistolica}/{self.presion_arterial_diastolica}"
        return "N/A"
    
    def evaluar_signos_vitales(self) -> dict:
        """
        Evalúa si los signos vitales están dentro de rangos normales
        
        Returns:
            Diccionario con evaluación de cada signo vital
        """
        evaluacion = {}
        
        # Presión arterial
        if self.presion_arterial_sistolica:
            if self.presion_arterial_sistolica < 90:
                evaluacion['presion_sistolica'] = 'baja'
            elif 90 <= self.presion_arterial_sistolica <= 120:
                evaluacion['presion_sistolica'] = 'normal'
            elif 120 < self.presion_arterial_sistolica <= 140:
                evaluacion['presion_sistolica'] = 'elevada'
            else:
                evaluacion['presion_sistolica'] = 'alta'
        
        if self.presion_arterial_diastolica:
            if self.presion_arterial_diastolica < 60:
                evaluacion['presion_diastolica'] = 'baja'
            elif 60 <= self.presion_arterial_diastolica <= 80:
                evaluacion['presion_diastolica'] = 'normal'
            else:
                evaluacion['presion_diastolica'] = 'alta'
        
        # Frecuencia cardíaca
        if self.frecuencia_cardiaca:
            if self.frecuencia_cardiaca < 60:
                evaluacion['frecuencia_cardiaca'] = 'bradicardia'
            elif 60 <= self.frecuencia_cardiaca <= 100:
                evaluacion['frecuencia_cardiaca'] = 'normal'
            else:
                evaluacion['frecuencia_cardiaca'] = 'taquicardia'
        
        # Temperatura
        if self.temperatura:
            temp_float = float(self.temperatura)
            if temp_float < 36.0:
                evaluacion['temperatura'] = 'hipotermia'
            elif 36.0 <= temp_float <= 37.5:
                evaluacion['temperatura'] = 'normal'
            elif 37.5 < temp_float <= 38.0:
                evaluacion['temperatura'] = 'febrícula'
            else:
                evaluacion['temperatura'] = 'fiebre'
        
        # Saturación de oxígeno
        if self.saturacion_oxigeno:
            if self.saturacion_oxigeno < 90:
                evaluacion['saturacion_oxigeno'] = 'crítica'
            elif 90 <= self.saturacion_oxigeno < 95:
                evaluacion['saturacion_oxigeno'] = 'baja'
            else:
                evaluacion['saturacion_oxigeno'] = 'normal'
        
        return evaluacion
    
    def requiere_atencion_urgente(self) -> bool:
        """
        Determina si el paciente requiere atención urgente basado en signos vitales
        
        Returns:
            True si requiere atención urgente
        """
        evaluacion = self.evaluar_signos_vitales()
        
        # Condiciones críticas
        condiciones_criticas = [
            evaluacion.get('saturacion_oxigeno') == 'crítica',
            evaluacion.get('presion_sistolica') == 'baja' and evaluacion.get('presion_diastolica') == 'baja',
            evaluacion.get('temperatura') == 'fiebre' and float(self.temperatura) > 39.0,
            self.nivel_dolor and self.nivel_dolor >= 8,
            self.nivel_conciencia in ['confuso', 'inconsciente']
        ]
        
        return any(condiciones_criticas)
    
    @classmethod
    def get_by_admission_id(cls, session, admission_id: str):
        """
        Obtiene una admisión por su código
        
        Args:
            session: Sesión de SQLAlchemy
            admission_id: Código de admisión
        
        Returns:
            Instancia de AdmissionORM o None
        """
        return session.query(cls).filter(
            cls.admission_id == admission_id
        ).first()
    
    @classmethod
    def get_admisiones_activas(cls, session):
        """
        Obtiene todas las admisiones activas
        
        Args:
            session: Sesión de SQLAlchemy
        
        Returns:
            Query con admisiones activas
        """
        return session.query(cls).filter(
            cls.estado_admision == 'activa'
        ).order_by(cls.fecha_admision.desc())
    
    @classmethod
    def get_by_paciente(cls, session, documento_id: int, paciente_id: int):
        """
        Obtiene admisiones de un paciente específico
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            paciente_id: ID del paciente
        
        Returns:
            Query con admisiones del paciente
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.paciente_id == paciente_id
        ).order_by(cls.fecha_admision.desc())
    
    @classmethod
    def get_by_prioridad(cls, session, prioridad: str):
        """
        Obtiene admisiones por nivel de prioridad
        
        Args:
            session: Sesión de SQLAlchemy
            prioridad: urgente, normal, baja
        
        Returns:
            Query con admisiones filtradas
        """
        return session.query(cls).filter(
            cls.prioridad == prioridad,
            cls.estado_admision == 'activa'
        ).order_by(cls.fecha_admision.asc())
    
    def to_dict(self) -> dict:
        """
        Convierte el modelo a diccionario
        
        Returns:
            Diccionario con los campos del modelo
        """
        return {
            "admission_id": self.admission_id,
            "documento_id": self.documento_id,
            "paciente_id": self.paciente_id,
            "cita_id": self.cita_id,
            "fecha_admision": self.fecha_admision.isoformat() if self.fecha_admision else None,
            "admitido_por": self.admitido_por,
            "motivo_consulta": self.motivo_consulta,
            "prioridad": self.prioridad,
            "estado_admision": self.estado_admision,
            # Signos vitales
            "presion_arterial_sistolica": self.presion_arterial_sistolica,
            "presion_arterial_diastolica": self.presion_arterial_diastolica,
            "presion_arterial": self.get_presion_arterial(),
            "frecuencia_cardiaca": self.frecuencia_cardiaca,
            "frecuencia_respiratoria": self.frecuencia_respiratoria,
            "temperatura": float(self.temperatura) if self.temperatura else None,
            "saturacion_oxigeno": self.saturacion_oxigeno,
            "peso": float(self.peso) if self.peso else None,
            "altura": self.altura,
            "imc": self.calcular_imc(),
            "pam": self.calcular_pam(),
            # Información adicional
            "nivel_dolor": self.nivel_dolor,
            "nivel_conciencia": self.nivel_conciencia,
            "sintomas_principales": self.sintomas_principales,
            "alergias_conocidas": self.alergias_conocidas,
            "medicamentos_actuales": self.medicamentos_actuales,
            "notas_enfermeria": self.notas_enfermeria,
            "observaciones": self.observaciones,
            # Evaluaciones
            "evaluacion_signos_vitales": self.evaluar_signos_vitales(),
            "requiere_atencion_urgente": self.requiere_atencion_urgente(),
            # Auditoría
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Aliases para compatibilidad
Admission = AdmissionORM

# Exportaciones del módulo
__all__ = [
    "AdmissionORM",
    "Admission"
]
