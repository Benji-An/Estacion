"""SQLAlchemy model para registrar archivos CSV cargados al sistema."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class ArchivoCSV(Base):
    __tablename__ = "archivos_csv"

    id = Column(Integer, primary_key=True, index=True)
    nombre_archivo = Column(String, nullable=False)
    fecha_carga = Column(DateTime, default=datetime.utcnow, nullable=False)
    total_registros = Column(Integer, nullable=False, default=0)
    # FK opcional al usuario que lo subió
    usuario_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    # Relación inversa: todas las mediciones de este archivo
    mediciones = relationship("MedicionEstacion", back_populates="archivo", cascade="all, delete-orphan")
