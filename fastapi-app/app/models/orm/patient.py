"""
Patient ORM Model - Mapeo a tabla 'paciente'
Modelo SQLAlchemy para la entidad Patient del esquema FHIR
"""

from sqlalchemy import (
    Column, BigInteger, Text, Date, String, 
    PrimaryKeyConstraint, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import text

from .base import (
    DistributedModel, UUIDMixin, AuditMixin, FHIRResourceMixin,
    CitusTableConfig, get_table_comment
)


class PatientORM(DistributedModel, UUIDMixin, AuditMixin, FHIRResourceMixin):
    """
    Modelo ORM para la tabla 'paciente'
    
    Tabla distribuida por documento_id en Citus para co-localizar
    todos los datos relacionados con un paciente específico.
    """
    
    __tablename__ = "paciente"
    __table_args__ = (
        # Primary Key compuesta requerida por Citus (incluye columna de distribución)
        PrimaryKeyConstraint("documento_id", "paciente_id"),
        
        # Índices para optimizar consultas comunes
        Index("idx_paciente_nombre", "nombre", "apellido"),
        Index("idx_paciente_documento_fecha", "documento_id", "created_at"),
        Index("idx_paciente_sexo", "sexo"),
        Index("idx_paciente_fecha_nacimiento", "fecha_nacimiento"),
        Index("idx_paciente_ciudad", "ciudad"),
        Index("idx_paciente_id", "id", unique=True),
        
        # Constraints de validación
        CheckConstraint(
            "sexo IN ('masculino', 'femenino', 'otro', 'desconocido')",
            name="chk_paciente_sexo"
        ),
        CheckConstraint(
            "fecha_nacimiento <= CURRENT_DATE",
            name="chk_paciente_fecha_nacimiento"
        ),
        
        # Comentario de tabla
        {"comment": get_table_comment("Patient", is_distributed=True)}
    )
    
    # Campos específicos de la tabla paciente
    
    # Primary Key fields
    paciente_id = Column(
        BigInteger,
        nullable=False,
        comment="ID único del paciente dentro del documento"
    )
    
    # Campo documento_id ya definido en DistributedModel
    
    # Campos de información básica del paciente
    nombre = Column(
        Text,
        nullable=True,
        comment="Nombre(s) del paciente"
    )
    
    apellido = Column(
        Text,
        nullable=True,
        comment="Apellido(s) del paciente"
    )
    
    sexo = Column(
        String(10),
        nullable=True,
        comment="Sexo administrativo del paciente (masculino, femenino, otro, desconocido)"
    )
    
    fecha_nacimiento = Column(
        Date,
        nullable=True,
        comment="Fecha de nacimiento del paciente"
    )
    
    contacto = Column(
        Text,
        nullable=True,
        comment="Información de contacto del paciente (JSON o texto)"
    )
    
    ciudad = Column(
        Text,
        nullable=True,
        comment="Ciudad de residencia del paciente"
    )
    
    # Campo UUID ya definido en UUIDMixin
    # Campos de auditoría ya definidos en AuditMixin
    # Campos FHIR ya definidos en FHIRResourceMixin
    
    def __repr__(self) -> str:
        """Representación string del modelo"""
        return (
            f"<PatientORM("
            f"documento_id={self.documento_id}, "
            f"paciente_id={self.paciente_id}, "
            f"nombre='{self.nombre}', "
            f"apellido='{self.apellido}', "
            f"sexo='{self.sexo}'"
            f")>"
        )
    
    def get_full_name(self) -> str:
        """
        Obtiene el nombre completo del paciente
        
        Returns:
            Nombre completo o string vacío si no hay nombre
        """
        parts = []
        if self.nombre:
            parts.append(self.nombre)
        if self.apellido:
            parts.append(self.apellido)
        return " ".join(parts)
    
    def is_adult(self) -> bool:
        """
        Verifica si el paciente es mayor de edad
        
        Returns:
            True si es mayor de 18 años, False en caso contrario
        """
        if not self.fecha_nacimiento:
            return False
        
        from datetime import date
        today = date.today()
        age = today.year - self.fecha_nacimiento.year
        
        # Ajustar si aún no ha cumplido años este año
        if today.month < self.fecha_nacimiento.month or \
           (today.month == self.fecha_nacimiento.month and today.day < self.fecha_nacimiento.day):
            age -= 1
        
        return age >= 18
    
    def get_age(self) -> int:
        """
        Calcula la edad actual del paciente
        
        Returns:
            Edad en años o 0 si no hay fecha de nacimiento
        """
        if not self.fecha_nacimiento:
            return 0
        
        from datetime import date
        today = date.today()
        age = today.year - self.fecha_nacimiento.year
        
        # Ajustar si aún no ha cumplido años este año
        if today.month < self.fecha_nacimiento.month or \
           (today.month == self.fecha_nacimiento.month and today.day < self.fecha_nacimiento.day):
            age -= 1
        
        return age
    
    @classmethod
    def get_by_documento_id(cls, session, documento_id: int):
        """
        Obtiene el paciente por documento_id
        
        Args:
            session: Sesión de SQLAlchemy
            documento_id: ID del documento del paciente
        
        Returns:
            Instancia de PatientORM o None si no se encuentra
        """
        return session.query(cls).filter(
            cls.documento_id == documento_id
        ).first()
    
    @classmethod
    def search_by_name(cls, session, nombre: str = None, apellido: str = None):
        """
        Busca pacientes por nombre y/o apellido
        
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
    def get_by_age_range(cls, session, min_age: int = None, max_age: int = None):
        """
        Obtiene pacientes por rango de edad
        
        Args:
            session: Sesión de SQLAlchemy
            min_age: Edad mínima (opcional)
            max_age: Edad máxima (opcional)
        
        Returns:
            Query de SQLAlchemy con los resultados
        """
        from datetime import date, timedelta
        
        query = session.query(cls).filter(cls.fecha_nacimiento.is_not(None))
        
        if min_age is not None:
            max_birth_date = date.today() - timedelta(days=min_age * 365.25)
            query = query.filter(cls.fecha_nacimiento <= max_birth_date)
        
        if max_age is not None:
            min_birth_date = date.today() - timedelta(days=(max_age + 1) * 365.25)
            query = query.filter(cls.fecha_nacimiento > min_birth_date)
        
        return query
    
    @classmethod
    def get_by_ciudad(cls, session, ciudad: str):
        """
        Obtiene pacientes por ciudad
        
        Args:
            session: Sesión de SQLAlchemy
            ciudad: Ciudad a buscar
        
        Returns:
            Query de SQLAlchemy con los resultados
        """
        return session.query(cls).filter(
            cls.ciudad.ilike(f"%{ciudad}%")
        )
    
    def to_dict(self) -> dict:
        """
        Convierte el modelo a diccionario
        
        Returns:
            Diccionario con los campos del modelo
        """
        return {
            "documento_id": self.documento_id,
            "paciente_id": self.paciente_id,
            "id": str(self.id) if self.id else None,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "sexo": self.sexo,
            "fecha_nacimiento": self.fecha_nacimiento.isoformat() if self.fecha_nacimiento else None,
            "contacto": self.contacto,
            "ciudad": self.ciudad,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "fhir_id": self.fhir_id,
            "fhir_version": self.fhir_version,
            "fhir_last_updated": self.fhir_last_updated.isoformat() if self.fhir_last_updated else None,
            "full_name": self.get_full_name(),
            "age": self.get_age(),
            "is_adult": self.is_adult()
        }


# Aliases para compatibilidad
Patient = PatientORM

# Exportaciones del módulo
__all__ = [
    "PatientORM",
    "Patient"
]