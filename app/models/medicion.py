"""SQLAlchemy model para cada fila de medición de la estación HOBO."""
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class MedicionEstacion(Base):
    __tablename__ = "mediciones"

    id = Column(Integer, primary_key=True, index=True)
    archivo_id = Column(Integer, ForeignKey("archivos_csv.id"), nullable=False, index=True)

    # Fecha y hora de la medición (con zona horaria GMT-05)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Campos del sensor — todos nullable por tolerancia a datos faltantes
    contenido_agua = Column(Float, nullable=True)   # m³/m³  (LBL: pluviometro)
    rad_solar      = Column(Float, nullable=True)   # W/m²   (LBL: Radiacion)
    temp_c         = Column(Float, nullable=True)   # °C     (LBL: Temp)
    humedad_pct    = Column(Float, nullable=True)   # %      (LBL: Humedad)
    vel_viento     = Column(Float, nullable=True)   # m/s    (LBL: Velocidad)
    vel_rafagas    = Column(Float, nullable=True)   # m/s    (LBL: Vel_rafagas)
    dir_viento     = Column(Float, nullable=True)   # °      (LBL: DirecV)
    lluvia_mm      = Column(Float, nullable=False, default=0.0)  # mm (LBL: Precipitacion)

    # Relación con el archivo fuente
    archivo = relationship("ArchivoCSV", back_populates="mediciones")
