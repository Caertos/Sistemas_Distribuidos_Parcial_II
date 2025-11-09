"""
Observation ORM Model - Mapeo a tabla 'observacion'
Modelo SQLAlchemy para la entidad Observation del esquema FHIR
"""

from sqlalchemy import (
    Column, BigInteger, Text, DateTime, String,
    PrimaryKeyConstraint, Index, CheckConstraint, ForeignKey
)
from sqlalchemy.sql import func

from .base import (
    DistributedModel, AuditMixin, FHIRResourceMixin,
    CitusTableConfig, get_table_comment, FHIRStatus
)


class ObservationORM(DistributedModel, AuditMixin, FHIRResourceMixin):
    """
    Modelo ORM para la tabla 'observacion'
    
    Tabla distribuida por documento_id en Citus.
    Contiene observaciones clínicas y mediciones de pacientes.
    """
    
    __tablename__ = "observacion"
    __table_args__ = (
        # Primary Key compuesta requerida por Citus
        PrimaryKeyConstraint("documento_id", "observacion_id"),
        
        # Índices para optimizar consultas comunes
        Index("idx_observacion_documento_fecha", "documento_id", "fecha"),
        Index("idx_observacion_paciente", "paciente_id"),
        Index("idx_observacion_tipo", "tipo"),
        Index("idx_observacion_fecha", "fecha"),
        Index("idx_observacion_encuentro", "referencia_encuentro"),
        Index("idx_observacion_unidad", "unidad"),
        Index("idx_observacion_created", "created_at"),
        
        # Foreign Keys (permitidas porque ambas tablas están distribuidas por documento_id)
        ForeignKey(
            ["documento_id", "paciente_id"], 
            ["paciente.documento_id", "paciente.paciente_id"],
            name="fk_observacion_paciente"
        ),
        ForeignKey(
            ["documento_id", "referencia_encuentro"], 
            ["encuentro.documento_id", "encuentro.encuentro_id"],
            name="fk_observacion_encuentro"
        ),
        
        # Combinar configuración de Citus con comentario
        {
            **CitusTableConfig.get_distributed_table_args(),
            "comment": get_table_comment("Observation", is_distributed=True)
        }
    )
    
    # Primary Key fields
    observacion_id = Column(
        BigInteger,
        nullable=False,
        comment="ID único de la observación"
    )
    
    # Campo documento_id ya definido en DistributedModel
    
    # Referencia al paciente
    paciente_id = Column(
        BigInteger,
        nullable=False,
        comment="ID del paciente al que pertenece la observación"
    )
    
    # Información de la observación
    tipo = Column(
        Text,
        nullable=False,
        comment="Tipo de observación (código LOINC o similar)"
    )
    
    valor = Column(
        Text,
        nullable=True,
        comment="Valor de la observación (puede ser numérico, texto, booleano)"
    )
    
    unidad = Column(
        Text,
        nullable=True,
        comment="Unidad de medida del valor (UCUM preferido)"
    )
    
    fecha = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Fecha y hora de la observación"
    )
    
    # Referencia opcional al encuentro/consulta
    referencia_encuentro = Column(
        BigInteger,
        nullable=True,
        comment="ID del encuentro donde se realizó la observación"
    )
    
    # Campos de auditoría ya definidos en AuditMixin
    # Campos FHIR ya definidos en FHIRResourceMixin
    
    def __repr__(self) -> str:
        """Representación string del modelo"""
        return (
            f"<ObservationORM("
            f"documento_id={self.documento_id}, "
            f"observacion_id={self.observacion_id}, "
            f"tipo='{self.tipo}', "
            f"valor='{self.valor}', "
            f"unidad='{self.unidad}'"
            f")>"
        )
    
    def get_display_value(self) -> str:
        """
        Obtiene el valor formateado para mostrar
        
        Returns:
            Valor con unidad si está disponible
        """
        if not self.valor:
            return "Sin valor"
        
        if self.unidad:
            return f"{self.valor} {self.unidad}"
        else:
            return str(self.valor)
    
    def is_numeric_value(self) -> bool:
        """
        Verifica si el valor es numérico
        
        Returns:
            True si el valor puede convertirse a float
        """
        if not self.valor:
            return False
        
        try:
            float(self.valor)
            return True
        except (ValueError, TypeError):
            return False
    
    def get_numeric_value(self) -> float:
        """
        Obtiene el valor numérico
        
        Returns:
            Valor como float o None si no es numérico
        """
        if not self.is_numeric_value():
            return None
        
        try:
            return float(self.valor)
        except (ValueError, TypeError):
            return None
    
    @classmethod
    def get_by_paciente(cls, session, documento_id: int, paciente_id: int):
        """
        Obtiene todas las observaciones de un paciente
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            paciente_id: ID del paciente
        
        Returns:
            Query de SQLAlchemy con las observaciones
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.paciente_id == paciente_id
        ).order_by(cls.fecha.desc())
    
    @classmethod
    def get_by_tipo(cls, session, documento_id: int, tipo: str):
        """
        Obtiene observaciones por tipo
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            tipo: Tipo de observación a buscar
        
        Returns:
            Query de SQLAlchemy con las observaciones
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.tipo.ilike(f"%{tipo}%")
        ).order_by(cls.fecha.desc())
    
    @classmethod
    def get_by_encuentro(cls, session, documento_id: int, encuentro_id: int):
        """
        Obtiene observaciones de un encuentro específico
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            encuentro_id: ID del encuentro
        
        Returns:
            Query de SQLAlchemy con las observaciones
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.referencia_encuentro == encuentro_id
        ).order_by(cls.fecha.asc())
    
    @classmethod
    def get_by_date_range(cls, session, documento_id: int, 
                         fecha_inicio=None, fecha_fin=None):
        """
        Obtiene observaciones por rango de fechas
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            fecha_inicio: Fecha inicio del rango (opcional)
            fecha_fin: Fecha fin del rango (opcional)
        
        Returns:
            Query de SQLAlchemy con las observaciones
        """
        query = session.query(cls).filter(cls.documento_id == documento_id)
        
        if fecha_inicio:
            query = query.filter(cls.fecha >= fecha_inicio)
        
        if fecha_fin:
            query = query.filter(cls.fecha <= fecha_fin)
        
        return query.order_by(cls.fecha.desc())
    
    @classmethod
    def get_latest_by_tipo(cls, session, documento_id: int, paciente_id: int, tipo: str):
        """
        Obtiene la observación más reciente de un tipo específico
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            paciente_id: ID del paciente
            tipo: Tipo de observación
        
        Returns:
            ObservationORM o None si no se encuentra
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.paciente_id == paciente_id,
            cls.tipo == tipo
        ).order_by(cls.fecha.desc()).first()
    
    @classmethod
    def get_vital_signs(cls, session, documento_id: int, paciente_id: int):
        """
        Obtiene observaciones de signos vitales
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            paciente_id: ID del paciente
        
        Returns:
            Query con observaciones de signos vitales
        """
        vital_signs_types = [
            'presion-arterial', 'frecuencia-cardiaca', 'frecuencia-respiratoria',
            'temperatura', 'saturacion-oxigeno', 'peso', 'talla', 'imc'
        ]
        
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.paciente_id == paciente_id,
            cls.tipo.in_(vital_signs_types)
        ).order_by(cls.fecha.desc())
    
    def to_dict(self) -> dict:
        """
        Convierte el modelo a diccionario
        
        Returns:
            Diccionario con los campos del modelo
        """
        return {
            "documento_id": self.documento_id,
            "observacion_id": self.observacion_id,
            "paciente_id": self.paciente_id,
            "tipo": self.tipo,
            "valor": self.valor,
            "unidad": self.unidad,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "referencia_encuentro": self.referencia_encuentro,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "fhir_id": self.fhir_id,
            "fhir_version": self.fhir_version,
            "fhir_last_updated": self.fhir_last_updated.isoformat() if self.fhir_last_updated else None,
            "display_value": self.get_display_value(),
            "is_numeric": self.is_numeric_value(),
            "numeric_value": self.get_numeric_value()
        }


# Aliases para compatibilidad
Observation = ObservationORM

# Exportaciones del módulo
__all__ = [
    "ObservationORM",
    "Observation"
]