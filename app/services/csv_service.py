"""
Servicio de parseo de CSV.

Contiene dos funciones:
  - parse_csv_rows(): función genérica existente (no tocar, usada por /upload).
  - parse_estacion_hobo(): parseo especializado para el CSV de la estación HOBO
    (S/N: 22462775). Mapea headers largos usando la etiqueta LBL: del sensor.
"""
import csv
import io
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from app.models.medicion import MedicionEstacion

# ─────────────────────────────────────────────────────────────────
# Función genérica (mantener para compatibilidad con /upload)
# ─────────────────────────────────────────────────────────────────

def parse_csv_rows(text_content: str, delimiter: str) -> List[Dict[str, Any]]:
    """Parseo genérico de CSV. Detecta delimitador automáticamente."""
    sample = text_content[:4096]
    detected_delimiter = delimiter or ","

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        detected_delimiter = dialect.delimiter
    except csv.Error:
        pass

    reader = csv.reader(io.StringIO(text_content), delimiter=detected_delimiter)
    raw_rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not raw_rows:
        return []

    header_index = 0
    for index, row in enumerate(raw_rows[:10]):
        if sum(1 for cell in row if cell.strip()) >= 2:
            header_index = index
            break

    headers = [header.strip() for header in raw_rows[header_index]]
    rows: List[Dict[str, Any]] = []

    for raw_row in raw_rows[header_index + 1 :]:
        row = {
            header: raw_row[index].strip() if index < len(raw_row) else ""
            for index, header in enumerate(headers)
        }
        rows.append(row)

    return rows


# ─────────────────────────────────────────────────────────────────
# Parseo especializado HOBO
# ─────────────────────────────────────────────────────────────────

# Zona horaria GMT-05 (Colombia)
TZ_COL = timezone(timedelta(hours=-5))

# Mapeo: valor de LBL → nombre del campo en MedicionEstacion
LBL_MAP: dict[str, str] = {
    "pluviometro": "contenido_agua",
    "Radiacion":   "rad_solar",
    "Temp":        "temp_c",
    "Humedad":     "humedad_pct",
    "Velocidad":   "vel_viento",
    "Vel_rafagas": "vel_rafagas",
    "DirecV":      "dir_viento",
    "Precipitacion": "lluvia_mm",
}

_LBL_RE = re.compile(r"LBL:\s*(\S+)\)", re.IGNORECASE)


def _extraer_lbl(header: str) -> str | None:
    """Extrae el valor de LBL: de un header largo del CSV HOBO."""
    m = _LBL_RE.search(header)
    return m.group(1) if m else None


def _parse_float(valor: str, default: float | None = None) -> float | None:
    """Convierte string a float. Retorna default si está vacío o es inválido."""
    v = valor.strip()
    if not v:
        return default
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return default


def _parse_timestamp(valor: str) -> datetime:
    """
    Parsea la fecha del CSV HOBO: '3/03/2026 10:56' → datetime con TZ GMT-05.
    Soporta formatos: d/mm/yyyy HH:MM y dd/mm/yyyy HH:MM
    """
    v = valor.strip()
    for fmt in ("%d/%m/%Y %H:%M", "%-d/%m/%Y %H:%M"):
        try:
            dt = datetime.strptime(v, fmt)
            return dt.replace(tzinfo=TZ_COL)
        except ValueError:
            continue
    raise ValueError(f"No se pudo parsear la fecha: '{v}'")


def parse_estacion_hobo(text_content: str) -> list[dict]:
    """
    Parsea el CSV exportado por el registrador HOBO (S/N: 22462775).

    Reglas:
      - Separador: ; (siempre)
      - Fila 0: título del equipo → se salta
      - Fila 1: headers reales de columnas
      - Mapeo de columnas: se extrae el valor de LBL: del header
      - Columna 'Lluvia, mm' vacía → 0.0
      - Columna 'N.º' → ignorada

    Retorna:
        Lista de dicts con campos ya mapeados:
        {timestamp, contenido_agua, rad_solar, temp_c, humedad_pct,
         vel_viento, vel_rafagas, dir_viento, lluvia_mm}
    """
    reader = csv.reader(io.StringIO(text_content), delimiter=";")
    all_rows = [row for row in reader]

    # Necesitamos al menos la fila de título + headers + 1 dato
    if len(all_rows) < 3:
        return []

    # Fila 0 = título del equipo → saltar
    # Fila 1 = headers reales
    raw_headers = [h.strip() for h in all_rows[1]]

    # Construir mapa: índice de columna → campo en BD
    col_map: dict[int, str] = {}
    fecha_col: int | None = None

    for idx, header in enumerate(raw_headers):
        if header.startswith("Fecha Tiempo"):
            fecha_col = idx
            continue
        lbl = _extraer_lbl(header)
        if lbl and lbl in LBL_MAP:
            col_map[idx] = LBL_MAP[lbl]

    if fecha_col is None:
        raise ValueError("No se encontró la columna 'Fecha Tiempo' en el CSV.")

    resultados: list[dict] = []

    # Filas de datos = desde la fila 2 en adelante
    for row in all_rows[2:]:
        if not any(cell.strip() for cell in row):
            continue  # saltar filas completamente vacías

        fila: dict[str, Any] = {}

        # Timestamp
        try:
            fila["timestamp"] = _parse_timestamp(row[fecha_col])
        except (ValueError, IndexError):
            continue  # saltar filas con fecha inválida

        # Campos de sensor
        for col_idx, campo in col_map.items():
            raw = row[col_idx] if col_idx < len(row) else ""
            if campo == "lluvia_mm":
                # Vacío → 0.0 (primera fila del sensor puede estar vacía)
                fila[campo] = _parse_float(raw, default=0.0)
            else:
                fila[campo] = _parse_float(raw, default=None)

        resultados.append(fila)

    return resultados


def dicts_a_mediciones(
    datos: list[dict],
    archivo_id: int,
) -> list[MedicionEstacion]:
    """
    Convierte la lista de dicts de parse_estacion_hobo() en
    objetos MedicionEstacion listos para insertar en BD.
    """
    return [
        MedicionEstacion(
            archivo_id=archivo_id,
            timestamp=d["timestamp"],
            contenido_agua=d.get("contenido_agua"),
            rad_solar=d.get("rad_solar"),
            temp_c=d.get("temp_c"),
            humedad_pct=d.get("humedad_pct"),
            vel_viento=d.get("vel_viento"),
            vel_rafagas=d.get("vel_rafagas"),
            dir_viento=d.get("dir_viento"),
            lluvia_mm=d.get("lluvia_mm", 0.0),
        )
        for d in datos
    ]
