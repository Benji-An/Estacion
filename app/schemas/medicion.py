"""
Schemas Pydantic para mediciones de la estación HOBO y archivos CSV.
Definen el formato exacto de las respuestas JSON que recibe el frontend.
"""
from datetime import datetime
from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────────
# Schemas de Archivos CSV
# ─────────────────────────────────────────────────────────────────

class ArchivoResponse(BaseModel):
    """Metadata de un archivo CSV cargado al sistema."""
    id: int
    nombre_archivo: str
    fecha_carga: datetime
    total_registros: int
    usuario_id: int | None = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────
# Schemas de Mediciones
# ─────────────────────────────────────────────────────────────────

class MedicionResponse(BaseModel):
    """Una fila de medición de la estación."""
    id: int
    archivo_id: int
    timestamp: datetime
    contenido_agua: float | None = None   # m³/m³
    rad_solar: float | None = None        # W/m²
    temp_c: float | None = None           # °C
    humedad_pct: float | None = None      # %
    vel_viento: float | None = None       # m/s
    vel_rafagas: float | None = None      # m/s
    dir_viento: float | None = None       # °
    lluvia_mm: float = 0.0               # mm

    model_config = {"from_attributes": True}


class PaginatedMedicionResponse(BaseModel):
    """Lista paginada de mediciones con metadatos de paginación."""
    total: int
    skip: int
    limit: int
    archivo_id: int
    data: list[MedicionResponse]


# ─────────────────────────────────────────────────────────────────
# Schema de Resumen Estadístico
# ─────────────────────────────────────────────────────────────────

class ResumenResponse(BaseModel):
    """Estadísticas agregadas de un archivo CSV — para tarjetas/KPIs en el frontend."""
    archivo_id: int
    lluvia_total_mm: float
    lluvia_max_mm: float
    temp_promedio_c: float
    temp_max_c: float
    temp_min_c: float
    humedad_promedio_pct: float
    vel_viento_promedio_ms: float
    vel_rafagas_max_ms: float
    rad_solar_promedio_wm2: float
    total_registros: int


# ─────────────────────────────────────────────────────────────────
# Schema de Serie Temporal (para gráficas)
# ─────────────────────────────────────────────────────────────────

class PuntoSerie(BaseModel):
    """Un punto en la serie temporal: timestamp ISO 8601 + valor numérico."""
    timestamp: str   # ISO 8601 string — fácil de parsear en Chart.js/Recharts
    valor: float | None


class SerieTemporalResponse(BaseModel):
    """
    Serie temporal de un campo específico.
    El frontend puede graficar directamente usando timestamps[] y valores[].
    """
    archivo_id: int
    campo: str
    unidad: str
    total_puntos: int
    data: list[PuntoSerie]


# Mapa de unidades por campo para incluir en la respuesta
UNIDADES_CAMPO = {
    "lluvia_mm":      "mm",
    "temp_c":         "°C",
    "humedad_pct":    "%",
    "rad_solar":      "W/m²",
    "vel_viento":     "m/s",
    "vel_rafagas":    "m/s",
    "dir_viento":     "°",
    "contenido_agua": "m³/m³",
}
