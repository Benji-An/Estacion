import csv
import io
from typing import Any, List, Dict

def parse_csv_rows(text_content: str, delimiter: str) -> List[Dict[str, Any]]:
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
