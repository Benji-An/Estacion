"""
Endpoints de cálculo hidrológico — Método Racional y Curvas IDF.
Todos son públicos (sin autenticación).

Rutas:
  POST /api/v1/calculo/escorrentia    — Q = C × I × A
  GET  /api/v1/calculo/intensidades   — Intensidades máximas por duración
  GET  /api/v1/calculo/idf            — Curvas IDF completas
  GET  /api/v1/calculo/coeficientes   — Tabla de coeficientes C de referencia
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import archivo as crud_archivo
from app.crud import medicion as crud_medicion
from app.schemas.calculo import (
    EscorrentiaRequest,
    EscorrentiaResponse,
    IDFResponse,
    FilaIDF,
    IntensidadesResponse,
    IntensidadDuracion,
)
from app.services.hydro_service import calcular_escorrentia, COEFICIENTES_REFERENCIA
from app.services.idf_service import calcular_curvas_idf, calcular_intensidades_maximas, DURACIONES_MIN

router = APIRouter()


# ─────────────────────────────────────────────────────────────────
# POST /escorrentia  — Q = C × I × A
# ─────────────────────────────────────────────────────────────────

@router.post(
    "/escorrentia",
    response_model=EscorrentiaResponse,
    summary="Calcular escorrentía — Método Racional",
    description=(
        "Calcula el caudal pico Q usando el Método Racional: **Q = C × I × A / 360**\n\n"
        "- **C**: Coeficiente de escorrentía (0-1)\n"
        "- **I**: Intensidad de lluvia de diseño (mm/h)\n"
        "- **A**: Área de la cuenca (hectáreas)\n\n"
        "Retorna Q en **m³/s** y **L/s**."
    ),
)
def calcular_escorrentia_endpoint(body: EscorrentiaRequest) -> Any:
    try:
        resultado = calcular_escorrentia(C=body.C, I=body.I, A=body.A)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return resultado


# ─────────────────────────────────────────────────────────────────
# GET /coeficientes  — Tabla de referencia de C
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/coeficientes",
    summary="Tabla de coeficientes de escorrentía C de referencia",
    description="Lista los valores típicos de C para diferentes tipos de superficie (IDEAM).",
)
def tabla_coeficientes() -> Any:
    return {
        "fuente": "IDEAM — Manual de Hidrología e Hidráulica Urbana",
        "nota": "Usar como referencia. Ajustar según condiciones específicas del sitio.",
        "coeficientes": COEFICIENTES_REFERENCIA,
    }


# ─────────────────────────────────────────────────────────────────
# GET /intensidades  — Intensidades máximas por duración
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/intensidades",
    response_model=IntensidadesResponse,
    summary="Intensidades máximas por duración",
    description=(
        "Analiza los registros de lluvia de un archivo y calcula la intensidad máxima "
        "observada para cada ventana de tiempo estándar: 5, 10, 15, 30, 60 y 120 minutos."
    ),
)
def intensidades_por_duracion(
    archivo_id: int = Query(..., description="ID del archivo CSV"),
    db: Session = Depends(get_db),
) -> Any:
    archivo = crud_archivo.get(db, archivo_id)
    if not archivo:
        raise HTTPException(status_code=404, detail=f"Archivo {archivo_id} no encontrado.")

    total = crud_medicion.get_total_by_archivo(db, archivo_id=archivo_id)
    serie = crud_medicion.get_serie_temporal(db, archivo_id=archivo_id, campo="lluvia_mm")

    # Convertir a formato que espera idf_service
    from datetime import datetime
    datos = []
    for punto in serie:
        ts = punto["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        val = punto["valor"]
        datos.append({"timestamp": ts, "lluvia_mm": val if val is not None else 0.0})

    intensidades_raw = calcular_intensidades_maximas(datos)

    intensidades = [
        IntensidadDuracion(
            duracion_min=dur,
            intensidad_max_mmh=info["intensidad_max_mmh"],
            n_muestras=info["n_muestras"],
        )
        for dur, info in sorted(intensidades_raw.items())
    ]

    return IntensidadesResponse(
        archivo_id=archivo_id,
        total_registros_analizados=total,
        intensidades=intensidades,
    )


# ─────────────────────────────────────────────────────────────────
# GET /idf  — Curvas IDF completas
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/idf",
    response_model=IDFResponse,
    summary="Curvas IDF — Intensidad-Duración-Frecuencia",
    description=(
        "Genera las curvas IDF completas a partir de los datos de precipitación "
        "del archivo especificado. Usa distribución de **Gumbel** para estimar "
        "intensidades en períodos de retorno T = 2, 5, 10, 25 y 50 años.\n\n"
        "La respuesta incluye dos formatos:\n"
        "- **tabla**: Filas por duración (ideal para tablas HTML)\n"
        "- **por_periodo**: Dict por T (ideal para Chart.js / Recharts)"
    ),
)
def curvas_idf(
    archivo_id: int = Query(..., description="ID del archivo CSV"),
    db: Session = Depends(get_db),
) -> Any:
    archivo = crud_archivo.get(db, archivo_id)
    if not archivo:
        raise HTTPException(status_code=404, detail=f"Archivo {archivo_id} no encontrado.")

    serie = crud_medicion.get_serie_temporal(db, archivo_id=archivo_id, campo="lluvia_mm")

    from datetime import datetime
    datos = []
    for punto in serie:
        ts = punto["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        val = punto["valor"]
        datos.append({"timestamp": ts, "lluvia_mm": val if val is not None else 0.0})

    resultado = calcular_curvas_idf(datos)

    tabla_tipada = [FilaIDF(**fila) for fila in resultado["tabla"]]

    return IDFResponse(
        archivo_id=archivo_id,
        duraciones_min=resultado["duraciones_min"],
        periodos_retorno=resultado["periodos_retorno"],
        tabla=tabla_tipada,
        por_periodo=resultado["por_periodo"],
        advertencia=resultado.get("advertencia"),
    )
