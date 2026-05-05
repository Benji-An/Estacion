"""CRUD para la tabla mediciones."""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.medicion import MedicionEstacion


def create_bulk(db: Session, mediciones: list[MedicionEstacion]) -> int:
    """Inserta una lista de mediciones en bloque. Retorna la cantidad insertada."""
    db.bulk_save_objects(mediciones)
    db.commit()
    return len(mediciones)


def get_by_archivo(
    db: Session,
    archivo_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[MedicionEstacion]:
    """Lista mediciones de un archivo, paginadas y ordenadas por timestamp."""
    return (
        db.query(MedicionEstacion)
        .filter(MedicionEstacion.archivo_id == archivo_id)
        .order_by(MedicionEstacion.timestamp.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_total_by_archivo(db: Session, archivo_id: int) -> int:
    """Cuenta el total de mediciones de un archivo."""
    return (
        db.query(func.count(MedicionEstacion.id))
        .filter(MedicionEstacion.archivo_id == archivo_id)
        .scalar()
    )


def get_resumen(db: Session, archivo_id: int) -> dict:
    """
    Calcula estadísticas agregadas de un archivo:
    lluvia total, temperatura promedio/max/min, humedad promedio, etc.
    """
    q = db.query(MedicionEstacion).filter(MedicionEstacion.archivo_id == archivo_id)

    result = db.query(
        func.sum(MedicionEstacion.lluvia_mm).label("lluvia_total_mm"),
        func.max(MedicionEstacion.lluvia_mm).label("lluvia_max_mm"),
        func.avg(MedicionEstacion.temp_c).label("temp_promedio_c"),
        func.max(MedicionEstacion.temp_c).label("temp_max_c"),
        func.min(MedicionEstacion.temp_c).label("temp_min_c"),
        func.avg(MedicionEstacion.humedad_pct).label("humedad_promedio_pct"),
        func.avg(MedicionEstacion.vel_viento).label("vel_viento_promedio_ms"),
        func.max(MedicionEstacion.vel_rafagas).label("vel_rafagas_max_ms"),
        func.avg(MedicionEstacion.rad_solar).label("rad_solar_promedio_wm2"),
        func.count(MedicionEstacion.id).label("total_registros"),
    ).filter(MedicionEstacion.archivo_id == archivo_id).one()

    return {
        "lluvia_total_mm":       round(result.lluvia_total_mm or 0.0, 3),
        "lluvia_max_mm":         round(result.lluvia_max_mm or 0.0, 3),
        "temp_promedio_c":       round(result.temp_promedio_c or 0.0, 3),
        "temp_max_c":            round(result.temp_max_c or 0.0, 3),
        "temp_min_c":            round(result.temp_min_c or 0.0, 3),
        "humedad_promedio_pct":  round(result.humedad_promedio_pct or 0.0, 3),
        "vel_viento_promedio_ms":round(result.vel_viento_promedio_ms or 0.0, 3),
        "vel_rafagas_max_ms":    round(result.vel_rafagas_max_ms or 0.0, 3),
        "rad_solar_promedio_wm2":round(result.rad_solar_promedio_wm2 or 0.0, 3),
        "total_registros":       result.total_registros,
    }


def get_serie_temporal(
    db: Session,
    archivo_id: int,
    campo: str,
) -> list[dict]:
    """
    Retorna una serie temporal [{timestamp, valor}] de un campo específico.
    Usada por el frontend para graficar.
    Campos válidos: lluvia_mm, temp_c, humedad_pct, rad_solar,
                    vel_viento, vel_rafagas, dir_viento, contenido_agua
    """
    CAMPOS_VALIDOS = {
        "lluvia_mm", "temp_c", "humedad_pct", "rad_solar",
        "vel_viento", "vel_rafagas", "dir_viento", "contenido_agua",
    }
    if campo not in CAMPOS_VALIDOS:
        raise ValueError(f"Campo '{campo}' no válido. Opciones: {CAMPOS_VALIDOS}")

    col = getattr(MedicionEstacion, campo)
    rows = (
        db.query(MedicionEstacion.timestamp, col)
        .filter(MedicionEstacion.archivo_id == archivo_id)
        .order_by(MedicionEstacion.timestamp.asc())
        .all()
    )
    return [
        {"timestamp": ts.isoformat(), "valor": val}
        for ts, val in rows
    ]
