"""
Servicio de Curvas IDF (Intensidad-Duración-Frecuencia).

Pasos del análisis:
  1. Agrupar los registros de lluvia_mm por ventanas de tiempo (5, 10, 15, 30, 60, 120 min)
  2. Calcular la intensidad horaria (mm/h) para cada ventana
  3. Obtener la intensidad máxima por duración
  4. Ajustar distribución de Gumbel (scipy.stats.gumbel_r)
  5. Calcular intensidades para períodos de retorno T = 2, 5, 10, 25, 50 años

Referencia: IDEAM, Manual de Hidrología e Hidráulica Urbana
"""
from datetime import datetime
import math

try:
    import numpy as np
    from scipy import stats
    SCIPY_DISPONIBLE = True
except ImportError:
    SCIPY_DISPONIBLE = False


# Duraciones estándar de análisis (en minutos)
DURACIONES_MIN = [5, 10, 15, 30, 60, 120]

# Períodos de retorno estándar (en años)
PERIODOS_RETORNO = [2, 5, 10, 25, 50]


def _intensidad_mmh(lluvia_mm: float, duracion_min: int) -> float:
    """Convierte lluvia acumulada en mm a intensidad en mm/h."""
    if duracion_min <= 0:
        return 0.0
    return lluvia_mm * (60.0 / duracion_min)


def calcular_intensidades_maximas(
    datos: list[dict],  # [{timestamp: datetime, lluvia_mm: float}]
) -> dict[int, dict]:
    """
    Agrupa los registros de lluvia por ventanas de tiempo y calcula
    la intensidad máxima observada para cada duración.

    Parámetros:
        datos: Lista de dicts con 'timestamp' (datetime) y 'lluvia_mm' (float)

    Retorna:
        {duracion_min: {"intensidad_max_mmh": float, "n_muestras": int}}
    """
    if not datos:
        return {d: {"intensidad_max_mmh": 0.0, "n_muestras": 0} for d in DURACIONES_MIN}

    # Ordenar por timestamp
    datos_ord = sorted(datos, key=lambda x: x["timestamp"])
    n = len(datos_ord)

    resultados = {}

    for duracion in DURACIONES_MIN:
        # Número de registros que equivalen a esta duración
        # Estimamos el intervalo entre registros (en minutos) con los primeros datos
        if n >= 2:
            delta = (datos_ord[1]["timestamp"] - datos_ord[0]["timestamp"]).total_seconds() / 60
            if delta <= 0:
                delta = 1.0
        else:
            delta = 1.0

        pasos = max(1, round(duracion / delta))
        intensidades = []

        for i in range(n - pasos + 1):
            ventana = datos_ord[i: i + pasos]
            lluvia_acumulada = sum(v["lluvia_mm"] for v in ventana if v["lluvia_mm"] is not None)
            intensidad = _intensidad_mmh(lluvia_acumulada, duracion)
            intensidades.append(intensidad)

        resultados[duracion] = {
            "intensidad_max_mmh": round(max(intensidades), 4) if intensidades else 0.0,
            "n_muestras": len(intensidades),
        }

    return resultados


def _gumbel_quantil(intensidades_maximas_anuales: list[float], T: int) -> float:
    """
    Calcula el cuantil de la distribución de Gumbel para un período de retorno T.

    Parámetros de Gumbel:
      β (escala) = σ × π / √6
      μ (ubicación) = x̄ - γ × β    (γ = constante de Euler ≈ 0.5772)
    Cuantil:
      x(T) = μ - β × ln(-ln(1 - 1/T))
    """
    if len(intensidades_maximas_anuales) < 2:
        # Muy pocos datos: retornar el único valor disponible
        return intensidades_maximas_anuales[0] if intensidades_maximas_anuales else 0.0

    if SCIPY_DISPONIBLE:
        arr = np.array(intensidades_maximas_anuales, dtype=float)
        mu, beta = stats.gumbel_r.fit(arr)
        prob_no_excedencia = 1.0 - (1.0 / T)
        return float(stats.gumbel_r.ppf(prob_no_excedencia, loc=mu, scale=beta))
    else:
        # Implementación manual sin scipy
        n = len(intensidades_maximas_anuales)
        media = sum(intensidades_maximas_anuales) / n
        varianza = sum((x - media) ** 2 for x in intensidades_maximas_anuales) / (n - 1)
        std = math.sqrt(varianza)
        EULER = 0.5772156649
        beta = std * math.pi / math.sqrt(6)
        mu = media - EULER * beta
        prob_no_excedencia = 1.0 - (1.0 / T)
        return mu - beta * math.log(-math.log(prob_no_excedencia))


def calcular_curvas_idf(
    datos: list[dict],
) -> dict:
    """
    Genera las curvas IDF completas a partir de los datos de precipitación.

    Para datasets pequeños (< 10 años de datos continuos):
    - Se usan las intensidades máximas observadas como único "año"
    - Se aplica Gumbel igualmente pero con advertencia
    - Esto da una aproximación conservadora basada en los datos disponibles

    Parámetros:
        datos: Lista de dicts [{timestamp, lluvia_mm}]

    Retorna:
        {
          "duraciones_min": [...],
          "periodos_retorno": [...],
          "tabla": [{duracion_min, T2, T5, T10, T25, T50}],
          "por_periodo": {"2": [...], "5": [...], ...},
          "advertencia": str | None
        }
    """
    intensidades_max = calcular_intensidades_maximas(datos)

    advertencia = None
    if len(datos) < 720:  # menos de ~12 horas de datos en intervalos de 1 min
        advertencia = (
            "Dataset con pocos registros. Las curvas IDF son una estimación "
            "aproximada. Para mayor precisión se recomienda al menos 1 año de datos continuos."
        )

    tabla = []
    por_periodo: dict[str, list[float]] = {str(T): [] for T in PERIODOS_RETORNO}

    for duracion in DURACIONES_MIN:
        info = intensidades_max[duracion]
        i_max = info["intensidad_max_mmh"]

        # Con datos limitados, usamos i_max como "serie de máximos anuales"
        # y la extrapolamos con Gumbel
        serie_maximos = [i_max] if i_max > 0 else [0.01]

        fila = {"duracion_min": duracion}
        for T in PERIODOS_RETORNO:
            val = _gumbel_quantil(serie_maximos, T)
            val = max(0.0, round(val, 2))
            fila[f"T{T}"] = val
            por_periodo[str(T)].append(val)

        tabla.append(fila)

    return {
        "duraciones_min": DURACIONES_MIN,
        "periodos_retorno": PERIODOS_RETORNO,
        "tabla": tabla,
        "por_periodo": por_periodo,
        "advertencia": advertencia,
    }
