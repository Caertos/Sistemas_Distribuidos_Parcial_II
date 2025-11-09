"""
Practitioner ORM Model - Mapeo a tabla 'profesional'
Modelo SQLAlchemy para la entidad Practitioner del esquema FHIR
"""

from sqlalchemy import (
    Column, BigInteger, Text, PrimaryKeyConstraint, Index
)

from .base import (
    ReferenceModel, AuditMixin, FHIRResourceMixin,
    CitusTableConfig, get_table_comment
)


class PractitionerORM(ReferenceModel, AuditMixin, FHIRResourceMixin):
    """
    Modelo ORM para la tabla 'profesional'
    
    Tabla de referencia replicada en todos los nodos de Citus.
    Contiene información de profesionales de la salud.
    """
    
    __tablename__ = "profesional"
    __table_args__ = (
        # Índices para optimizar consultas comunes
        Index("idx_profesional_nombre", "nombre", "apellido"),
        Index("idx_profesional_especialidad", "especialidad"),
        Index("idx_profesional_registro", "registro_medico", unique=True),
        Index("idx_profesional_created", "created_at"),
        
        # Combinar configuración de Citus con comentario
        {
            **CitusTableConfig.get_reference_table_args(),
            "comment": get_table_comment("Practitioner", is_distributed=False)
        }
    )
    
    # Primary Key
    profesional_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ID único del profesional de salud"
    )
    
    # Información básica del profesional
    nombre = Column(
        Text,
        nullable=True,
        comment="Nombre(s) del profesional"
    )
    
    apellido = Column(
        Text,
        nullable=True,
        comment="Apellido(s) del profesional"
    )
    
    especialidad = Column(
        Text,
        nullable=True,
        comment="Especialidad médica del profesional"
    )
    
    registro_medico = Column(
        Text,
        nullable=True,
        unique=True,
        comment="Número de registro médico o licencia profesional"
    )
    
    # Campos de auditoría ya definidos en AuditMixin
    # Campos FHIR ya definidos en FHIRResourceMixin
    
    def __repr__(self) -> str:
        """Representación string del modelo"""
        return (
            f"<PractitionerORM("
            f"profesional_id={self.profesional_id}, "
            f"nombre='{self.nombre}', "
            f"apellido='{self.apellido}', "
            f"especialidad='{self.especialidad}'"
            f")>"
        )
    
    def get_full_name(self) -> str:
        """
        Obtiene el nombre completo del profesional
        
        Returns:
            Nombre completo o string vacío si no hay nombre
        """
        parts = []
        if self.nombre:
            parts.append(self.nombre)
        if self.apellido:
            parts.append(self.apellido)
        return " ".join(parts)
    
    def get_display_name(self) -> str:
        """
        Obtiene el nombre para mostrar con título profesional
        
        Returns:
            Nombre con formato profesional
        """
        full_name = self.get_full_name()
        if not full_name:
            return f"Profesional ID: {self.profesional_id}"
        
        # Agregar título si hay especialidad
        if self.especialidad:
            return f"Dr. {full_name} - {self.especialidad}"
        else:
            return f"Dr. {full_name}"
    
    @classmethod
    def get_by_registro_medico(cls, session, registro_medico: str):
        """
        Obtiene un profesional por su registro médico
        
        Args:
            session: Sesión de SQLAlchemy
            registro_medico: Número de registro médico
        
        Returns:
            Instancia de PractitionerORM o None si no se encuentra
        """
        return session.query(cls).filter(
            cls.registro_medico == registro_medico
        ).first()
    
    @classmethod
    def search_by_name(cls, session, nombre: str = None, apellido: str = None):
        """
        Busca profesionales por nombre y/o apellido
        
        Args:
            session: Sesión de SQLAlchemy
            nombre: Nombre a buscar (opcional)
            apellido: Apellido a buscar (opcional)
        
        Returns:
            Query de SQLAlchemy con los resultados
        """
        query = session.query(cls)
        
        if nombre:
            query = query.filter(cls.nombre.ilike(f"%{nombre}%"))
        
        if apellido:
            query = query.filter(cls.apellido.ilike(f"%{apellido}%"))
        
        return query
    
    @classmethod
    def get_by_especialidad(cls, session, especialidad: str):
        """
        Obtiene profesionales por especialidad
        
        Args:
            session: Sesión de SQLAlchemy
            especialidad: Especialidad a buscar
        
        Returns:
            Query de SQLAlchemy con los resultados
        """
        return session.query(cls).filter(
            cls.especialidad.ilike(f"%{especialidad}%")
        )
    
    @classmethod
    def get_all_especialidades(cls, session):
        """
        Obtiene todas las especialidades únicas
        
        Args:
            session: Sesión de SQLAlchemy
        
        Returns:
            Lista de especialidades
        """
        result = session.query(cls.especialidad).filter(
            cls.especialidad.is_not(None)
        ).distinct().all()
        
        return [row[0] for row in result if row[0]]
    
    def to_dict(self) -> dict:
        """
        Convierte el modelo a diccionario
        
        Returns:
            Diccionario con los campos del modelo
        """
        return {
            "profesional_id": self.profesional_id,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "especialidad": self.especialidad,
            "registro_medico": self.registro_medico,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "fhir_id": self.fhir_id,
            "fhir_version": self.fhir_version,
            "fhir_last_updated": self.fhir_last_updated.isoformat() if self.fhir_last_updated else None,
            "full_name": self.get_full_name(),
            "display_name": self.get_display_name()
        }


# Aliases para compatibilidad
Practitioner = PractitionerORM

# Exportaciones del módulo
__all__ = [
    "PractitionerORM",
    "Practitioner"
]