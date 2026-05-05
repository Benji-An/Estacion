"""CRUD para la tabla archivos_csv."""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.archivo_csv import ArchivoCSV


def create(
    db: Session,
    nombre_archivo: str,
    total_registros: int,
    usuario_id: int | None = None,
) -> ArchivoCSV:
    """Registra un nuevo archivo CSV en la BD."""
    archivo = ArchivoCSV(
        nombre_archivo=nombre_archivo,
        fecha_carga=datetime.utcnow(),
        total_registros=total_registros,
        usuario_id=usuario_id,
    )
    db.add(archivo)
    db.commit()
    db.refresh(archivo)
    return archivo


def get(db: Session, archivo_id: int) -> ArchivoCSV | None:
    """Obtiene un archivo por su ID."""
    return db.query(ArchivoCSV).filter(ArchivoCSV.id == archivo_id).first()


def get_multi(db: Session, skip: int = 0, limit: int = 50) -> list[ArchivoCSV]:
    """Lista todos los archivos cargados, paginados."""
    return (
        db.query(ArchivoCSV)
        .order_by(ArchivoCSV.fecha_carga.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
