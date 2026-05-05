"""
Servicio del Método Racional — Q = C × I × A / 360

Calcula el caudal de escorrentía superficial a partir de:
  - C: coeficiente de escorrentía (adimensional, 0-1)
  - I: intensidad de lluvia (mm/h)
  - A: área de la cuenca (hectáreas)

El divisor 360 convierte las unidades: (mm/h × ha) → m³/s
"""

from dataclasses import dataclass


# Valores típicos de C para diferentes tipos de superficie (referencia IDEAM)
COEFICIENTES_REFERENCIA = {
    "tejados_impermeables":   {"C": 0.90, "descripcion": "Tejados y superficies impermeables"},
    "pavimento_asfalto":      {"C": 0.85, "descripcion": "Pavimento de asfalto y concreto"},
    "areas_comerciales":      {"C": 0.75, "descripcion": "Zonas comerciales y de negocios"},
    "residencial_alta_densidad": {"C": 0.65, "descripcion": "Residencial alta densidad (lotes < 500 m²)"},
    "residencial_baja_densidad": {"C": 0.35, "descripcion": "Residencial baja densidad (lotes > 2000 m²)"},
    "zonas_industriales":     {"C": 0.65, "descripcion": "Zonas industriales"},
    "parques_jardines":       {"C": 0.20, "descripcion": "Parques, jardines y zonas verdes"},
    "bosque_natural":         {"C": 0.10, "descripcion": "Bosque natural y selva"},
    "pasto_suave":            {"C": 0.30, "descripcion": "Praderas y pastizales (suelo suave)"},
    "cultivos":               {"C": 0.40, "descripcion": "Tierras de cultivo"},
    "mixto_urbano":           {"C": 0.60, "descripcion": "Mixto urbano (valor por defecto)"},
}


def calcular_escorrentia(C: float, I: float, A: float) -> dict:
    """
    Calcula el caudal pico de escorrentía usando el Método Racional.

    Q = (C × I × A) / 360

    Parámetros:
        C: Coeficiente de escorrentía (0.0 – 1.0, adimensional)
        I: Intensidad de lluvia de diseño (mm/h)
        A: Área de la cuenca o superficie (hectáreas)

    Retorna:
        dict con Q_m3s, parámetros de entrada y unidades

    Raises:
        ValueError: Si los parámetros están fuera de rango
    """
    # Validaciones
    if not (0.0 <= C <= 1.0):
        raise ValueError(f"C debe estar entre 0 y 1. Recibido: {C}")
    if I <= 0:
        raise ValueError(f"La intensidad I debe ser mayor a 0. Recibido: {I}")
    if A <= 0:
        raise ValueError(f"El área A debe ser mayor a 0. Recibido: {A}")

    Q = (C * I * A) / 360.0

    return {
        "Q_m3s": round(Q, 6),
        "Q_Ls": round(Q * 1000, 4),          # También en litros/segundo
        "C":    C,
        "I_mmh": I,
        "A_ha": A,
        "formula": "Q = (C × I × A) / 360",
        "unidades": {
            "Q_m3s": "m³/s",
            "Q_Ls":  "L/s",
            "C":     "adimensional",
            "I":     "mm/h",
            "A":     "hectáreas",
        },
        "nota": "Método Racional — válido para cuencas < 1300 ha (IDEAM)",
    }


def intensidad_desde_datos(lluvia_mm: list[float], intervalo_minutos: float) -> float:
    """
    Calcula la intensidad horaria promedio a partir de mediciones de lluvia acumulada.

    Parámetros:
        lluvia_mm: Lista de valores de lluvia (mm) en intervalos regulares
        intervalo_minutos: Intervalo entre mediciones en minutos

    Retorna:
        Intensidad en mm/h
    """
    if not lluvia_mm or intervalo_minutos <= 0:
        return 0.0

    lluvia_total = sum(v for v in lluvia_mm if v is not None and v > 0)
    duracion_horas = (len(lluvia_mm) * intervalo_minutos) / 60.0

    if duracion_horas == 0:
        return 0.0

    return round(lluvia_total / duracion_horas, 4)
