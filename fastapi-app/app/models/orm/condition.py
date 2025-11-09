"""
Condition ORM Model - Mapeo a tabla 'condicion'
Modelo SQLAlchemy para la entidad Condition del esquema FHIR
"""

from sqlalchemy import (
    Column, BigInteger, Text, Date, String,
    PrimaryKeyConstraint, Index, CheckConstraint, ForeignKey
)

from .base import (
    DistributedModel, AuditMixin, FHIRResourceMixin,
    CitusTableConfig, get_table_comment
)


class ConditionORM(DistributedModel, AuditMixin, FHIRResourceMixin):
    """
    Modelo ORM para la tabla 'condicion'
    
    Tabla distribuida por documento_id en Citus.
    Contiene condiciones médicas, diagnósticos y problemas de salud.
    """
    
    __tablename__ = "condicion"
    __table_args__ = (
        # Primary Key compuesta requerida por Citus
        PrimaryKeyConstraint("documento_id", "condicion_id"),
        
        # Índices para optimizar consultas comunes
        Index("idx_condicion_documento_fecha", "documento_id", "fecha_inicio"),
        Index("idx_condicion_paciente", "paciente_id"),
        Index("idx_condicion_codigo", "codigo"),
        Index("idx_condicion_gravedad", "gravedad"),
        Index("idx_condicion_fecha_inicio", "fecha_inicio"),
        Index("idx_condicion_fecha_fin", "fecha_fin"),
        Index("idx_condicion_activa", "fecha_fin", postgresql_where="fecha_fin IS NULL"),
        Index("idx_condicion_created", "created_at"),
        
        # Foreign Key a paciente (co-localizada)
        ForeignKey(
            ["documento_id", "paciente_id"], 
            ["paciente.documento_id", "paciente.paciente_id"],
            name="fk_condicion_paciente"
        ),
        
        # Constraints de validación
        CheckConstraint(
            "gravedad IN ('leve', 'moderada', 'severa', 'critica') OR gravedad IS NULL",
            name="chk_condicion_gravedad"
        ),
        CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin >= fecha_inicio",
            name="chk_condicion_fechas"
        ),
        
        # Combinar configuración de Citus con comentario
        {
            **CitusTableConfig.get_distributed_table_args(),
            "comment": get_table_comment("Condition", is_distributed=True)
        }
    )
    
    # Primary Key fields
    condicion_id = Column(
        BigInteger,
        nullable=False,
        comment="ID único de la condición"
    )
    
    # Campo documento_id ya definido en DistributedModel
    
    # Referencia al paciente
    paciente_id = Column(
        BigInteger,
        nullable=False,
        comment="ID del paciente al que pertenece la condición"
    )
    
    # Información de la condición
    codigo = Column(
        Text,
        nullable=True,
        comment="Código de la condición (ICD-10, SNOMED-CT, etc.)"
    )
    
    descripcion = Column(
        Text,
        nullable=False,
        comment="Descripción de la condición/diagnóstico"
    )
    
    gravedad = Column(
        Text,
        nullable=True,
        comment="Gravedad de la condición (leve, moderada, severa, critica)"
    )
    
    fecha_inicio = Column(
        Date,
        nullable=True,
        comment="Fecha de inicio de la condición"
    )
    
    fecha_fin = Column(
        Date,
        nullable=True,
        comment="Fecha de resolución de la condición (NULL = activa)"
    )
    
    # Campos de auditoría ya definidos en AuditMixin
    # Campos FHIR ya definidos en FHIRResourceMixin
    
    def __repr__(self) -> str:
        """Representación string del modelo"""
        return (
            f"<ConditionORM("
            f"documento_id={self.documento_id}, "
            f"condicion_id={self.condicion_id}, "
            f"codigo='{self.codigo}', "
            f"descripcion='{self.descripcion}', "
            f"gravedad='{self.gravedad}'"
            f")>"
        )
    
    @property
    def is_active(self) -> bool:
        """
        Verifica si la condición está activa
        
        Returns:
            True si la condición no tiene fecha de fin (activa)
        """
        return self.fecha_fin is None
    
    @property
    def duration_days(self) -> int:
        """
        Calcula la duración de la condición en días
        
        Returns:
            Días de duración o días desde inicio si está activa
        """
        from datetime import date
        
        if not self.fecha_inicio:
            return 0
        
        end_date = self.fecha_fin if self.fecha_fin else date.today()
        return (end_date - self.fecha_inicio).days
    
    def get_status_display(self) -> str:
        """
        Obtiene el estado para mostrar
        
        Returns:
            Estado legible de la condición
        """
        if self.is_active:
            return "Activa"
        else:
            return "Resuelta"
    
    def get_severity_display(self) -> str:
        """
        Obtiene la gravedad formateada
        
        Returns:
            Gravedad capitalizada o "No especificada"
        """
        if not self.gravedad:
            return "No especificada"
        
        severity_map = {
            'leve': 'Leve',
            'moderada': 'Moderada', 
            'severa': 'Severa',
            'critica': 'Crítica'
        }
        
        return severity_map.get(self.gravedad.lower(), self.gravedad.capitalize())
    
    @classmethod
    def get_by_paciente(cls, session, documento_id: int, paciente_id: int):
        """
        Obtiene todas las condiciones de un paciente
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            paciente_id: ID del paciente
        
        Returns:
            Query de SQLAlchemy con las condiciones
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.paciente_id == paciente_id
        ).order_by(cls.fecha_inicio.desc())
    
    @classmethod
    def get_active_conditions(cls, session, documento_id: int, paciente_id: int):
        """
        Obtiene condiciones activas de un paciente
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            paciente_id: ID del paciente
        
        Returns:
            Query con condiciones activas
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.paciente_id == paciente_id,
            cls.fecha_fin.is_(None)
        ).order_by(cls.fecha_inicio.desc())
    
    @classmethod
    def get_by_codigo(cls, session, documento_id: int, codigo: str):
        """
        Obtiene condiciones por código
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            codigo: Código de la condición
        
        Returns:
            Query de SQLAlchemy con las condiciones
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.codigo == codigo
        ).order_by(cls.fecha_inicio.desc())
    
    @classmethod
    def search_by_description(cls, session, documento_id: int, termino: str):
        """
        Busca condiciones por descripción
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            termino: Término a buscar en la descripción
        
        Returns:
            Query de SQLAlchemy con las condiciones
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.descripcion.ilike(f"%{termino}%")
        ).order_by(cls.fecha_inicio.desc())
    
    @classmethod
    def get_by_severity(cls, session, documento_id: int, gravedad: str):
        """
        Obtiene condiciones por gravedad
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            gravedad: Gravedad a filtrar
        
        Returns:
            Query de SQLAlchemy con las condiciones
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.gravedad == gravedad
        ).order_by(cls.fecha_inicio.desc())
    
    @classmethod
    def get_by_date_range(cls, session, documento_id: int, 
                         fecha_inicio=None, fecha_fin=None):
        """
        Obtiene condiciones por rango de fechas de inicio
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            fecha_inicio: Fecha inicio del rango (opcional)
            fecha_fin: Fecha fin del rango (opcional)
        
        Returns:
            Query de SQLAlchemy con las condiciones
        """
        query = session.query(cls).filter(cls.documento_id == documento_id)
        
        if fecha_inicio:
            query = query.filter(cls.fecha_inicio >= fecha_inicio)
        
        if fecha_fin:
            query = query.filter(cls.fecha_inicio <= fecha_fin)
        
        return query.order_by(cls.fecha_inicio.desc())
    
    @classmethod
    def get_chronic_conditions(cls, session, documento_id: int, paciente_id: int, 
                              min_duration_days: int = 90):
        """
        Obtiene condiciones crónicas (duración >= min_duration_days)
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            paciente_id: ID del paciente
            min_duration_days: Duración mínima en días para considerar crónica
        
        Returns:
            Lista de condiciones crónicas
        """
        from datetime import date, timedelta
        
        conditions = cls.get_by_paciente(session, documento_id, paciente_id).all()
        chronic_conditions = []
        
        for condition in conditions:
            if condition.fecha_inicio:
                end_date = condition.fecha_fin if condition.fecha_fin else date.today()
                duration = (end_date - condition.fecha_inicio).days
                
                if duration >= min_duration_days:
                    chronic_conditions.append(condition)
        
        return chronic_conditions
    
    def to_dict(self) -> dict:
        """
        Convierte el modelo a diccionario
        
        Returns:
            Diccionario con los campos del modelo
        """
        return {
            "documento_id": self.documento_id,
            "condicion_id": self.condicion_id,
            "paciente_id": self.paciente_id,
            "codigo": self.codigo,
            "descripcion": self.descripcion,
            "gravedad": self.gravedad,
            "fecha_inicio": self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            "fecha_fin": self.fecha_fin.isoformat() if self.fecha_fin else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "fhir_id": self.fhir_id,
            "fhir_version": self.fhir_version,
            "fhir_last_updated": self.fhir_last_updated.isoformat() if self.fhir_last_updated else None,
            "is_active": self.is_active,
            "duration_days": self.duration_days,
            "status_display": self.get_status_display(),
            "severity_display": self.get_severity_display()
        }


# Aliases para compatibilidad
Condition = ConditionORM

# Exportaciones del módulo
__all__ = [
    "ConditionORM",
    "Condition"
]