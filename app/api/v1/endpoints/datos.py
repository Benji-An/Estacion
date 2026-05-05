"""
Endpoints de datos — carga y consulta de mediciones de la estación HOBO.

Rutas:
  POST /api/v1/datos/upload       — Subir CSV (requiere auth JWT)
  GET  /api/v1/datos/mediciones   — Listar mediciones paginadas (público)
  GET  /api/v1/datos/resumen      — Estadísticas agregadas (público)
  GET  /api/v1/datos/series       — Serie temporal para gráficas (público)
  GET  /api/v1/datos/archivos     — Listar archivos cargados (público)
"""
from typing import Any
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import archivo as crud_archivo
from app.crud import medicion as crud_medicion
from app.models.user import User
from app.schemas.medicion import (
    ArchivoResponse,
    PaginatedMedicionResponse,
    ResumenResponse,
    SerieTemporalResponse,
    PuntoSerie,
    UNIDADES_CAMPO,
    MedicionResponse,
)
from app.services.csv_service import parse_estacion_hobo, dicts_a_mediciones

router = APIRouter()

CAMPOS_VALIDOS = list(UNIDADES_CAMPO.keys())


# ─────────────────────────────────────────────────────────────────
# POST /upload  — Requiere autenticación JWT
# ─────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=ArchivoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir archivo CSV de la estación HOBO",
    description=(
        "Parsea el CSV de la estación HOBO (S/N: 22462775), "
        "guarda todas las mediciones en la base de datos y "
        "retorna los metadatos del archivo cargado."
    ),
)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .csv")

    try:
        raw_bytes = await file.read()
        text_content = raw_bytes.decode("utf-8-sig")
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el archivo. Verifica la codificación (UTF-8).")

    try:
        datos_parseados = parse_estacion_hobo(text_content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Error parseando el CSV: {e}")

    if not datos_parseados:
        raise HTTPException(status_code=422, detail="El CSV no contiene datos válidos.")

    # Registrar el archivo
    archivo = crud_archivo.create(
        db=db,
        nombre_archivo=file.filename,
        total_registros=len(datos_parseados),
        usuario_id=current_user.id,
    )

    # Convertir dicts a objetos ORM e insertar en bloque
    mediciones = dicts_a_mediciones(datos_parseados, archivo_id=archivo.id)
    crud_medicion.create_bulk(db=db, mediciones=mediciones)

    return archivo


# ─────────────────────────────────────────────────────────────────
# GET /archivos  — Público
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/archivos",
    response_model=list[ArchivoResponse],
    summary="Listar archivos CSV cargados",
)
def listar_archivos(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Any:
    return crud_archivo.get_multi(db=db, skip=skip, limit=limit)


# ─────────────────────────────────────────────────────────────────
# GET /mediciones  — Público
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/mediciones",
    response_model=PaginatedMedicionResponse,
    summary="Listar mediciones paginadas de un archivo",
)
def listar_mediciones(
    archivo_id: int = Query(..., description="ID del archivo CSV"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> Any:
    archivo = crud_archivo.get(db, archivo_id)
    if not archivo:
        raise HTTPException(status_code=404, detail=f"Archivo {archivo_id} no encontrado.")

    mediciones = crud_medicion.get_by_archivo(db, archivo_id=archivo_id, skip=skip, limit=limit)
    total = crud_medicion.get_total_by_archivo(db, archivo_id=archivo_id)

    return PaginatedMedicionResponse(
        total=total,
        skip=skip,
        limit=limit,
        archivo_id=archivo_id,
        data=[MedicionResponse.model_validate(m) for m in mediciones],
    )


# ─────────────────────────────────────────────────────────────────
# GET /resumen  — Público
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/resumen",
    response_model=ResumenResponse,
    summary="Estadísticas agregadas de un archivo",
    description="Retorna KPIs como lluvia total, temperatura promedio/max/min, humedad, viento, etc.",
)
def resumen_archivo(
    archivo_id: int = Query(..., description="ID del archivo CSV"),
    db: Session = Depends(get_db),
) -> Any:
    archivo = crud_archivo.get(db, archivo_id)
    if not archivo:
        raise HTTPException(status_code=404, detail=f"Archivo {archivo_id} no encontrado.")

    stats = crud_medicion.get_resumen(db, archivo_id=archivo_id)
    return ResumenResponse(archivo_id=archivo_id, **stats)


# ─────────────────────────────────────────────────────────────────
# GET /series  — Público
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/series",
    response_model=SerieTemporalResponse,
    summary="Serie temporal de un campo para gráficas",
    description=(
        "Retorna [{timestamp, valor}] de un campo específico. "
        f"Campos válidos: {', '.join(CAMPOS_VALIDOS)}"
    ),
)
def serie_temporal(
    archivo_id: int = Query(..., description="ID del archivo CSV"),
    campo: str = Query("lluvia_mm", description=f"Campo a graficar. Opciones: {', '.join(CAMPOS_VALIDOS)}"),
    db: Session = Depends(get_db),
) -> Any:
    if campo not in UNIDADES_CAMPO:
        raise HTTPException(
            status_code=400,
            detail=f"Campo '{campo}' no válido. Opciones: {', '.join(CAMPOS_VALIDOS)}",
        )

    archivo = crud_archivo.get(db, archivo_id)
    if not archivo:
        raise HTTPException(status_code=404, detail=f"Archivo {archivo_id} no encontrado.")

    puntos_raw = crud_medicion.get_serie_temporal(db, archivo_id=archivo_id, campo=campo)
    puntos = [PuntoSerie(timestamp=p["timestamp"], valor=p["valor"]) for p in puntos_raw]

    return SerieTemporalResponse(
        archivo_id=archivo_id,
        campo=campo,
        unidad=UNIDADES_CAMPO[campo],
        total_puntos=len(puntos),
        data=puntos,
    )
