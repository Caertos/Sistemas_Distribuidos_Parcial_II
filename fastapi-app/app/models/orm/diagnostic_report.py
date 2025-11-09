"""
DiagnosticReport ORM Model - Mapeo a tabla 'resultado_laboratorio'
Modelo SQLAlchemy para la entidad DiagnosticReport del esquema FHIR
"""

from sqlalchemy import (
    Column, BigInteger, Text, DateTime, String, Numeric,
    PrimaryKeyConstraint, Index, CheckConstraint, ForeignKey
)
from sqlalchemy.sql import func

from .base import (
    DistributedModel, AuditMixin, FHIRResourceMixin,
    CitusTableConfig, get_table_comment
)


class DiagnosticReportORM(DistributedModel, AuditMixin, FHIRResourceMixin):
    """
    Modelo ORM para la tabla 'resultado_laboratorio'
    
    Tabla distribuida por documento_id en Citus.
    Contiene reportes diagnósticos y resultados de laboratorio.
    """
    
    __tablename__ = "resultado_laboratorio"
    __table_args__ = (
        # Primary Key compuesta requerida por Citus
        PrimaryKeyConstraint("documento_id", "resultado_id"),
        
        # Índices para optimizar consultas comunes
        Index("idx_resultado_documento_fecha", "documento_id", "fecha_resultado"),
        Index("idx_resultado_paciente", "paciente_id"),
        Index("idx_resultado_codigo", "codigo_examen"),
        Index("idx_resultado_nombre", "nombre_examen"),
        Index("idx_resultado_estado", "estado"),
        Index("idx_resultado_profesional", "profesional_id"),
        Index("idx_resultado_laboratorio", "laboratorio"),
        Index("idx_resultado_fecha_muestra", "fecha_muestra"),
        Index("idx_resultado_fecha_resultado", "fecha_resultado"),
        Index("idx_resultado_valor_numerico", "valor_numerico"),
        Index("idx_resultado_created", "created_at"),
        
        # Foreign Keys
        ForeignKey(
            ["documento_id", "paciente_id"], 
            ["paciente.documento_id", "paciente.paciente_id"],
            name="fk_resultado_paciente"
        ),
        ForeignKey(
            "profesional_id", 
            "profesional.profesional_id",
            name="fk_resultado_profesional"
        ),
        
        # Constraints de validación
        CheckConstraint(
            "estado IN ('registrado', 'preliminar', 'final', 'corregido', 'cancelado')",
            name="chk_resultado_estado"
        ),
        CheckConstraint(
            "fecha_resultado >= fecha_muestra OR fecha_muestra IS NULL",
            name="chk_resultado_fechas"
        ),
        
        # Combinar configuración de Citus con comentario
        {
            **CitusTableConfig.get_distributed_table_args(),
            "comment": get_table_comment("DiagnosticReport", is_distributed=True)
        }
    )
    
    # Primary Key fields
    resultado_id = Column(
        BigInteger,
        nullable=False,
        comment="ID único del resultado de laboratorio"
    )
    
    # Campo documento_id ya definido en DistributedModel
    
    # Referencia al paciente
    paciente_id = Column(
        BigInteger,
        nullable=False,
        comment="ID del paciente al que pertenece el resultado"
    )
    
    # Información del examen
    codigo_examen = Column(
        Text,
        nullable=True,
        comment="Código del examen (LOINC, CPT, etc.)"
    )
    
    nombre_examen = Column(
        Text,
        nullable=False,
        comment="Nombre del examen o prueba diagnóstica"
    )
    
    # Valores del resultado
    valor_numerico = Column(
        Numeric(15, 6),
        nullable=True,
        comment="Valor numérico del resultado"
    )
    
    valor_texto = Column(
        Text,
        nullable=True,
        comment="Valor textual del resultado"
    )
    
    unidad = Column(
        Text,
        nullable=True,
        comment="Unidad de medida del resultado"
    )
    
    rango_referencia = Column(
        Text,
        nullable=True,
        comment="Rango de referencia normal para el examen"
    )
    
    # Estado y fechas
    estado = Column(
        Text,
        default="final",
        nullable=False,
        comment="Estado del resultado (registrado, preliminar, final, corregido, cancelado)"
    )
    
    fecha_muestra = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha y hora de toma de muestra"
    )
    
    fecha_resultado = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha y hora del resultado"
    )
    
    # Referencias
    profesional_id = Column(
        BigInteger,
        nullable=True,
        comment="ID del profesional responsable del resultado"
    )
    
    laboratorio = Column(
        Text,
        nullable=True,
        comment="Nombre del laboratorio donde se procesó"
    )
    
    # Campos de auditoría ya definidos en AuditMixin
    # Campos FHIR ya definidos en FHIRResourceMixin
    
    def __repr__(self) -> str:
        """Representación string del modelo"""
        return (
            f"<DiagnosticReportORM("
            f"documento_id={self.documento_id}, "
            f"resultado_id={self.resultado_id}, "
            f"nombre='{self.nombre_examen}', "
            f"valor='{self.get_display_value()}', "
            f"estado='{self.estado}'"
            f")>"
        )
    
    def get_display_value(self) -> str:
        """
        Obtiene el valor formateado para mostrar
        
        Returns:
            Valor con unidad si está disponible
        """
        if self.valor_numerico is not None:
            value = str(self.valor_numerico)
            if self.unidad:
                return f"{value} {self.unidad}"
            return value
        elif self.valor_texto:
            return self.valor_texto
        else:
            return "Sin resultado"
    
    def is_numeric_result(self) -> bool:
        """
        Verifica si el resultado es numérico
        
        Returns:
            True si tiene valor numérico
        """
        return self.valor_numerico is not None
    
    def is_abnormal(self) -> bool:
        """
        Determina si el resultado está fuera del rango normal
        (Implementación básica, puede mejorarse con parsing del rango)
        
        Returns:
            True si puede determinarse que está fuera de rango
        """
        # Esta es una implementación básica
        # En producción se necesitaría un parser más sofisticado
        if not self.is_numeric_result() or not self.rango_referencia:
            return False
        
        # Intentar parsear rangos simples como "10-20" o "< 5"
        try:
            if "-" in self.rango_referencia:
                parts = self.rango_referencia.split("-")
                if len(parts) == 2:
                    min_val = float(parts[0].strip())
                    max_val = float(parts[1].strip())
                    return not (min_val <= float(self.valor_numerico) <= max_val)
        except (ValueError, TypeError):
            pass
        
        return False
    
    def get_status_display(self) -> str:
        """
        Obtiene el estado formateado
        
        Returns:
            Estado capitalizado
        """
        status_map = {
            'registrado': 'Registrado',
            'preliminar': 'Preliminar',
            'final': 'Final',
            'corregido': 'Corregido',
            'cancelado': 'Cancelado'
        }
        
        return status_map.get(self.estado, self.estado.capitalize())
    
    @property
    def processing_time_hours(self) -> float:
        """
        Calcula el tiempo de procesamiento en horas
        
        Returns:
            Horas entre toma de muestra y resultado
        """
        if not self.fecha_muestra or not self.fecha_resultado:
            return 0.0
        
        delta = self.fecha_resultado - self.fecha_muestra
        return delta.total_seconds() / 3600
    
    @classmethod
    def get_by_paciente(cls, session, documento_id: int, paciente_id: int):
        """
        Obtiene todos los resultados de un paciente
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            paciente_id: ID del paciente
        
        Returns:
            Query de SQLAlchemy con los resultados
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.paciente_id == paciente_id
        ).order_by(cls.fecha_resultado.desc())
    
    @classmethod
    def get_by_codigo_examen(cls, session, documento_id: int, codigo_examen: str):
        """
        Obtiene resultados por código de examen
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            codigo_examen: Código del examen
        
        Returns:
            Query de SQLAlchemy con los resultados
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.codigo_examen == codigo_examen
        ).order_by(cls.fecha_resultado.desc())
    
    @classmethod
    def search_by_exam_name(cls, session, documento_id: int, termino: str):
        """
        Busca resultados por nombre de examen
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            termino: Término a buscar
        
        Returns:
            Query de SQLAlchemy con los resultados
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.nombre_examen.ilike(f"%{termino}%")
        ).order_by(cls.fecha_resultado.desc())
    
    @classmethod
    def get_by_estado(cls, session, documento_id: int, estado: str):
        """
        Obtiene resultados por estado
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            estado: Estado a filtrar
        
        Returns:
            Query de SQLAlchemy con los resultados
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id,
            cls.estado == estado
        ).order_by(cls.fecha_resultado.desc())
    
    @classmethod
    def get_by_laboratorio(cls, session, laboratorio: str):
        """
        Obtiene resultados por laboratorio
        
        Args:
            session: Sesión de SQLAlchemy
            laboratorio: Nombre del laboratorio
        
        Returns:
            Query de SQLAlchemy con los resultados
        """
        return session.query(cls).filter(
            cls.laboratorio.ilike(f"%{laboratorio}%")
        ).order_by(cls.fecha_resultado.desc())
    
    @classmethod
    def get_by_date_range(cls, session, documento_id: int, 
                         fecha_inicio=None, fecha_fin=None):
        """
        Obtiene resultados por rango de fechas
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            fecha_inicio: Fecha inicio del rango (opcional)
            fecha_fin: Fecha fin del rango (opcional)
        
        Returns:
            Query de SQLAlchemy con los resultados
        """
        query = session.query(cls).filter(cls.documento_id == documento_id)
        
        if fecha_inicio:
            query = query.filter(cls.fecha_resultado >= fecha_inicio)
        
        if fecha_fin:
            query = query.filter(cls.fecha_resultado <= fecha_fin)
        
        return query.order_by(cls.fecha_resultado.desc())
    
    @classmethod
    def get_abnormal_results(cls, session, documento_id: int, paciente_id: int):
        """
        Obtiene resultados anormales de un paciente
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento
            paciente_id: ID del paciente
        
        Returns:
            Lista de resultados potencialmente anormales
        """
        results = cls.get_by_paciente(session, documento_id, paciente_id).all()
        return [result for result in results if result.is_abnormal()]
    
    def to_dict(self) -> dict:
        """
        Convierte el modelo a diccionario
        
        Returns:
            Diccionario con los campos del modelo
        """
        return {
            "documento_id": self.documento_id,
            "resultado_id": self.resultado_id,
            "paciente_id": self.paciente_id,
            "codigo_examen": self.codigo_examen,
            "nombre_examen": self.nombre_examen,
            "valor_numerico": float(self.valor_numerico) if self.valor_numerico else None,
            "valor_texto": self.valor_texto,
            "unidad": self.unidad,
            "rango_referencia": self.rango_referencia,
            "estado": self.estado,
            "fecha_muestra": self.fecha_muestra.isoformat() if self.fecha_muestra else None,
            "fecha_resultado": self.fecha_resultado.isoformat() if self.fecha_resultado else None,
            "profesional_id": self.profesional_id,
            "laboratorio": self.laboratorio,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "fhir_id": self.fhir_id,
            "fhir_version": self.fhir_version,
            "fhir_last_updated": self.fhir_last_updated.isoformat() if self.fhir_last_updated else None,
            "display_value": self.get_display_value(),
            "is_numeric": self.is_numeric_result(),
            "is_abnormal": self.is_abnormal(),
            "status_display": self.get_status_display(),
            "processing_time_hours": self.processing_time_hours
        }


# Aliases para compatibilidad
DiagnosticReport = DiagnosticReportORM

# Exportaciones del módulo
__all__ = [
    "DiagnosticReportORM",
    "DiagnosticReport"
]