"""
Schemas Pydantic para los endpoints de cálculo hidrológico.
Definen el formato de entrada (requests) y salida (responses) para:
  - Método Racional: Q = C × I × A
  - Curvas IDF (Intensidad-Duración-Frecuencia)
  - Intensidades máximas por duración
"""
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────
# Método Racional  Q = C × I × A
# ─────────────────────────────────────────────────────────────────

class EscorrentiaRequest(BaseModel):
    """Parámetros de entrada para calcular Q = C × I × A."""
    C: float = Field(..., ge=0.0, le=1.0, description="Coeficiente de escorrentía (0-1)")
    I: float = Field(..., gt=0, description="Intensidad de lluvia (mm/h)")
    A: float = Field(..., gt=0, description="Área de la cuenca (hectáreas)")

    model_config = {
        "json_schema_extra": {
            "example": {"C": 0.60, "I": 50.0, "A": 1.0}
        }
    }


class EscorrentiaResponse(BaseModel):
    """Resultado del cálculo Q = C × I × A / 360."""
    Q_m3s: float       # Caudal en m³/s
    Q_Ls: float        # Caudal en L/s
    C: float
    I_mmh: float
    A_ha: float
    formula: str
    unidades: dict
    nota: str


# ─────────────────────────────────────────────────────────────────
# Intensidades máximas por duración
# ─────────────────────────────────────────────────────────────────

class IntensidadDuracion(BaseModel):
    """Intensidad máxima observada para una ventana de tiempo."""
    duracion_min: int          # Duración en minutos (5, 10, 15, 30, 60, 120)
    intensidad_max_mmh: float  # Intensidad máxima (mm/h)
    n_muestras: int            # Cantidad de ventanas analizadas


class IntensidadesResponse(BaseModel):
    """Intensidades máximas por duración — datos base para construir curvas IDF."""
    archivo_id: int
    total_registros_analizados: int
    intensidades: list[IntensidadDuracion]


# ─────────────────────────────────────────────────────────────────
# Curvas IDF (Intensidad-Duración-Frecuencia)
# ─────────────────────────────────────────────────────────────────

class FilaIDF(BaseModel):
    """
    Intensidades para una duración específica en todos los períodos de retorno.
    Formato optimizado para graficar: una fila por duración.
    """
    duracion_min: int
    T2:  float   # mm/h para período de retorno de 2 años
    T5:  float   # mm/h para período de retorno de 5 años
    T10: float   # mm/h para período de retorno de 10 años
    T25: float   # mm/h para período de retorno de 25 años
    T50: float   # mm/h para período de retorno de 50 años


class IDFResponse(BaseModel):
    """
    Curvas IDF completas para el frontend.

    La matriz está diseñada para dos modos de visualización:
    1. Por período de retorno: graficar I vs Duración para cada T
    2. Por duración: graficar I vs T para cada duración

    Ejemplo de uso en Chart.js:
        labels = response.duraciones_min
        datasets = [{label: f"T={T} años", data: response.por_periodo[str(T)]}
                    for T in response.periodos_retorno]
    """
    archivo_id: int
    duraciones_min: list[int]       # Eje X típico: [5, 10, 15, 30, 60, 120]
    periodos_retorno: list[int]     # [2, 5, 10, 25, 50]
    # Matriz principal: filas por duración
    tabla: list[FilaIDF]
    # Formato alternativo para graficar fácilmente por período:
    # {"2": [I_5min, I_10min, ...], "5": [...], ...}
    por_periodo: dict[str, list[float]]
    advertencia: str | None = None  # Mensaje si hay pocos datos para Gumbel
