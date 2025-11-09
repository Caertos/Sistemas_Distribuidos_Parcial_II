"""
MedicationRequest ORM Model - Mapeo a tabla 'medicamento'
Modelo SQLAlchemy para la entidad MedicationRequest del esquema FHIR
"""

from sqlalchemy import (
    Column, BigInteger, Text, Date, String,
    PrimaryKeyConstraint, Index, CheckConstraint, ForeignKey
)

from .base import (
    DistributedModel, AuditMixin, FHIRResourceMixin,
    CitusTableConfig, get_table_comment
)


class MedicationRequestORM(DistributedModel, AuditMixin, FHIRResourceMixin):
    """
    Modelo ORM para la tabla 'medicamento'
    
    Tabla distribuida por documento_id en Citus.
    Contiene solicitudes y prescripciones de medicamentos.
    """
    
    __tablename__ = "medicamento"
    __table_args__ = (
        # Primary Key compuesta requerida por Citus
        PrimaryKeyConstraint("documento_id", "medicamento_id"),
        
        # Índices para optimizar consultas comunes
        Index("idx_medicamento_documento_fecha", "documento_id", "fecha_inicio"),
        Index("idx_medicamento_paciente", "paciente_id"),
        Index("idx_medicamento_codigo", "codigo_medicamento"),
        Index("idx_medicamento_nombre", "nombre_medicamento"),
        Index("idx_medicamento_estado", "estado"),
        Index("idx_medicamento_prescriptor", "prescriptor_id"),
        Index("idx_medicamento_activo", "estado", postgresql_where="estado = 'activo'"),
        Index("idx_medicamento_fecha_inicio", "fecha_inicio"),
        Index("idx_medicamento_fecha_fin", "fecha_fin"),
        Index("idx_medicamento_created", "created_at"),
        
        # Foreign Keys
        ForeignKey(
            ["documento_id", "paciente_id"], 
            ["paciente.documento_id", "paciente.paciente_id"],
            name="fk_medicamento_paciente"
        ),
        ForeignKey(
            "prescriptor_id", 
            "profesional.profesional_id",
            name="fk_medicamento_prescriptor"
        ),
        
        # Constraints de validación
        CheckConstraint(
            "estado IN ('activo', 'suspendido', 'completado', 'cancelado')",
            name="chk_medicamento_estado"
        ),
        CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin >= fecha_inicio",
            name="chk_medicamento_fechas"
        ),
        
        # Configuración de tabla distribuida Citus
        CitusTableConfig.get_distributed_table_args(),
        
        # Comentario de tabla
        comment=get_table_comment("MedicationRequest", is_distributed=True)
    )
    
    # Primary Key fields
    medicamento_id = Column(
        BigInteger,
        nullable=False,
        comment="ID único de la solicitud de medicamento"
    )
    
    # Campo documento_id ya definido en DistributedModel
    
    # Referencia al paciente
    paciente_id = Column(
        BigInteger,
        nullable=False,
        comment="ID del paciente al que se prescribe el medicamento"
    )
    
    # Información del medicamento
    codigo_medicamento = Column(
        Text,
        nullable=True,
        comment="Código del medicamento (RxNorm, ATC, etc.)"
    )
    
    nombre_medicamento = Column(
        Text,
        nullable=False,
        comment="Nombre del medicamento"
    )
    
    dosis = Column(
        Text,
        nullable=True,
        comment="Dosis del medicamento (ej: 500mg, 2 comprimidos)"
    )
    
    via_administracion = Column(
        Text,
        nullable=True,
        comment="Vía de administración (oral, intravenosa, etc.)"
    )
    
    frecuencia = Column(
        Text,
        nullable=True,
        comment="Frecuencia de administración (ej: cada 8 horas, 3 veces al día)"
    )
    
    fecha_inicio = Column(
        Date,
        nullable=True,
        comment="Fecha de inicio del tratamiento"
    )
    
    fecha_fin = Column(
        Date,
        nullable=True,
        comment="Fecha de fin del tratamiento (NULL = indefinido)"
    )
    
    # Referencia al prescriptor
    prescriptor_id = Column(
        BigInteger,
        nullable=True,
        comment="ID del profesional que prescribe el medicamento"
    )
    
    estado = Column(
        Text,
        default="activo",
        nullable=False,
        comment="Estado de la prescripción (activo, suspendido, completado, cancelado)"
    )
    
    notas = Column(
        Text,
        nullable=True,
        comment="Notas adicionales sobre la prescripción"
    )
    
    # Campos de auditoría ya definidos en AuditMixin
    # Campos FHIR ya definidos en FHIRResourceMixin
    
    def __repr__(self) -> str:
        """Representación string del modelo"""
        return (
            f"<MedicationRequestORM("
            f"documento_id={self.documento_id}, "
            f"medicamento_id={self.medicamento_id}, "
            f"nombre='{self.nombre_medicamento}', "
            f"dosis='{self.dosis}', "
            f"estado='{self.estado}'"
            f")>"
        )
    
    @property
    def is_active(self) -> bool:
        """
        Verifica si la prescripción está activa
        
        Returns:
            True si el estado es 'activo'
        """
        return self.estado == "activo"
    
    @property
    def duration_days(self) -> int:
        """
        Calcula la duración del tratamiento en días
        
        Returns:
            Días de duración o días desde inicio si está activo
        """
        from datetime import date
        
        if not self.fecha_inicio:
            return 0
        
        end_date = self.fecha_fin if self.fecha_fin else date.today()
        return (end_date - self.fecha_inicio).days
    
    def get_dosage_display(self) -> str:
        """
        Obtiene la dosificación formateada para mostrar
        
        Returns:
            Dosificación completa legible
        """
        parts = []
        
        if self.dosis:
            parts.append(self.dosis)
        
        if self.via_administracion:
            parts.append(f"vía {self.via_administracion}")
        
        if self.frecuencia:
            parts.append(self.frecuencia)
        
        return ", ".join(parts) if parts else "Dosificación no especificada"
    
    def get_status_display(self) -> str:
        """
        Obtiene el estado formateado
        
        Returns:
            Estado capitalizado
        """
        status_map = {
            'activo': 'Activo',
            'suspendido': 'Suspendido',
            'completado': 'Completado',
            'cancelado': 'Cancelado'
        }
        
        return status_map.get(self.estado, self.estado.capitalize())
    
    @classmethod
    def get_by_paciente(cls, session, documento_id: int, paciente_id: int):
        """
        Obtiene todas las prescripciones de un paciente
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            paciente_id: ID del paciente
        
        Returns:
            Query de SQLAlchemy con las prescripciones
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.paciente_id == paciente_id
        ).order_by(cls.fecha_inicio.desc())
    
    @classmethod
    def get_active_medications(cls, session, documento_id: int, paciente_id: int):
        """
        Obtiene medicaciones activas de un paciente
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            paciente_id: ID del paciente
        
        Returns:
            Query con medicaciones activas
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.paciente_id == paciente_id,
            cls.estado == "activo"
        ).order_by(cls.fecha_inicio.desc())
    
    @classmethod
    def get_by_prescriptor(cls, session, prescriptor_id: int):
        """
        Obtiene prescripciones por prescriptor
        
        Args:
            session: Sesión de SQLAlchemy
            prescriptor_id: ID del prescriptor
        
        Returns:
            Query de SQLAlchemy con las prescripciones
        """
        return session.query(cls).filter(
            cls.prescriptor_id == prescriptor_id
        ).order_by(cls.fecha_inicio.desc())
    
    @classmethod
    def search_by_medication(cls, session, documento_id: int, termino: str):
        """
        Busca prescripciones por nombre de medicamento
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            termino: Término a buscar
        
        Returns:
            Query de SQLAlchemy con las prescripciones
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.nombre_medicamento.ilike(f"%{termino}%")
        ).order_by(cls.fecha_inicio.desc())
    
    @classmethod
    def get_by_codigo(cls, session, codigo_medicamento: str):
        """
        Obtiene prescripciones por código de medicamento
        
        Args:
            session: Sesión de SQLAlchemy
            codigo_medicamento: Código del medicamento
        
        Returns:
            Query de SQLAlchemy con las prescripciones
        """
        return session.query(cls).filter(
            cls.codigo_medicamento == codigo_medicamento
        ).order_by(cls.fecha_inicio.desc())
    
    @classmethod
    def get_by_date_range(cls, session, documento_id: int, 
                         fecha_inicio=None, fecha_fin=None):
        """
        Obtiene prescripciones por rango de fechas
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            fecha_inicio: Fecha inicio del rango (opcional)
            fecha_fin: Fecha fin del rango (opcional)
        
        Returns:
            Query de SQLAlchemy con las prescripciones
        """
        query = session.query(cls).filter(cls.documento_id == documento_id)
        
        if fecha_inicio:
            query = query.filter(cls.fecha_inicio >= fecha_inicio)
        
        if fecha_fin:
            query = query.filter(cls.fecha_inicio <= fecha_fin)
        
        return query.order_by(cls.fecha_inicio.desc())
    
    @classmethod
    def get_long_term_medications(cls, session, documento_id: int, paciente_id: int, 
                                 min_duration_days: int = 90):
        """
        Obtiene medicaciones de largo plazo
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            paciente_id: ID del paciente
            min_duration_days: Duración mínima en días
        
        Returns:
            Lista de medicaciones de largo plazo
        """
        medications = cls.get_by_paciente(session, documento_id, paciente_id).all()
        long_term_meds = []
        
        for medication in medications:
            if medication.duration_days >= min_duration_days:
                long_term_meds.append(medication)
        
        return long_term_meds
    
    def to_dict(self) -> dict:
        """
        Convierte el modelo a diccionario
        
        Returns:
            Diccionario con los campos del modelo
        """
        return {
            "documento_id": self.documento_id,
            "medicamento_id": self.medicamento_id,
            "paciente_id": self.paciente_id,
            "codigo_medicamento": self.codigo_medicamento,
            "nombre_medicamento": self.nombre_medicamento,
            "dosis": self.dosis,
            "via_administracion": self.via_administracion,
            "frecuencia": self.frecuencia,
            "fecha_inicio": self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            "fecha_fin": self.fecha_fin.isoformat() if self.fecha_fin else None,
            "prescriptor_id": self.prescriptor_id,
            "estado": self.estado,
            "notas": self.notas,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "fhir_id": self.fhir_id,
            "fhir_version": self.fhir_version,
            "fhir_last_updated": self.fhir_last_updated.isoformat() if self.fhir_last_updated else None,
            "is_active": self.is_active,
            "duration_days": self.duration_days,
            "dosage_display": self.get_dosage_display(),
            "status_display": self.get_status_display()
        }


# Aliases para compatibilidad
MedicationRequest = MedicationRequestORM

# Exportaciones del módulo
__all__ = [
    "MedicationRequestORM",
    "MedicationRequest"
]