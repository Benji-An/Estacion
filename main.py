from __future__ import annotations

import csv
import io
import html
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse

app = FastAPI(title="Estacion CSV Demo")


def build_page(message: str = "", table_html: str = "") -> str:
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Subir CSV</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f7fb;
      --panel: #ffffff;
      --text: #102033;
      --muted: #5b6573;
      --accent: #2563eb;
      --border: #d9e2ef;
      --success: #0f7a4f;
      --error: #b42318;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      font-family: Segoe UI, Arial, sans-serif;
      background: linear-gradient(180deg, #eaf1ff 0%, var(--bg) 40%, #eef2f7 100%);
      color: var(--text);
      min-height: 100vh;
    }}

    main {{
      max-width: 960px;
      margin: 0 auto;
      padding: 40px 20px 56px;
    }}

    .card {{
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 24px;
      box-shadow: 0 18px 50px rgba(16, 32, 51, 0.08);
      backdrop-filter: blur(10px);
    }}

    h1 {{ margin: 0 0 8px; font-size: 2rem; }}
    p {{ margin: 0; color: var(--muted); line-height: 1.5; }}

    form {{
      display: grid;
      gap: 14px;
      margin-top: 24px;
      padding: 18px;
      border: 1px dashed var(--border);
      border-radius: 14px;
      background: #fbfcfe;
    }}

    .field {{ display: grid; gap: 8px; }}

    label {{ font-weight: 600; }}

    input[type="file"], input[type="text"] {{
      width: 100%;
      padding: 12px 14px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: white;
    }}

    button {{
      border: 0;
      border-radius: 10px;
      background: var(--accent);
      color: white;
      padding: 12px 16px;
      font-weight: 700;
      cursor: pointer;
      justify-self: start;
    }}

    .message {{
      margin-top: 18px;
      padding: 12px 14px;
      border-radius: 10px;
      background: #eef4ff;
      color: #1d4ed8;
      border: 1px solid #c7d7fe;
    }}

    .message.error {{
      background: #fff1f0;
      color: var(--error);
      border-color: #fecdca;
    }}

    .message.success {{
      background: #effdf5;
      color: var(--success);
      border-color: #abefc6;
    }}

    .table-wrap {{ margin-top: 22px; overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; background: white; }}
    th, td {{
      border: 1px solid var(--border);
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
      font-size: 0.95rem;
    }}
    th {{ background: #f8fbff; }}
    .meta {{ margin-top: 10px; font-size: 0.92rem; color: var(--muted); }}
  </style>
</head>
<body>
  <main>
    <section class="card">
      <h1>Subir CSV</h1>
      <p>Usa este formulario para probar la carga de archivos CSV con FastAPI y ver una vista previa de las primeras filas.</p>

      <form action="/upload" method="post" enctype="multipart/form-data">
        <div class="field">
          <label for="file">Archivo CSV</label>
          <input id="file" name="file" type="file" accept=".csv,text/csv" required>
        </div>
        <div class="field">
          <label for="delimiter">Separador</label>
          <input id="delimiter" name="delimiter" type="text" value="," maxlength="1">
        </div>
        <button type="submit">Cargar CSV</button>
      </form>

      {message}
      {table_html}
    </section>
  </main>
</body>
</html>"""


def rows_to_table(rows: list[dict[str, Any]]) -> tuple[str, str]:
  if not rows:
    return "<div class='message error'>El archivo no contiene filas válidas.</div>", ""

  headers = list(rows[0].keys())
  header_html = "".join(f"<th>{html.escape(str(header))}</th>" for header in headers)

  body_rows = []
  for row in rows:
    cells = "".join(f"<td>{html.escape(str(row.get(header, '')))}</td>" for header in headers)
    body_rows.append(f"<tr>{cells}</tr>")

  table_html = (
    "<div class='table-wrap'><table><thead><tr>"
    f"{header_html}"
    "</tr></thead><tbody>"
    f"{''.join(body_rows)}"
    "</tbody></table></div>"
  )
  message = f"<div class='message success'>Se cargaron {len(rows)} filas y {len(headers)} columnas.</div>"
  return message, table_html


def parse_csv_rows(text_content: str, delimiter: str) -> list[dict[str, Any]]:
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
  rows: list[dict[str, Any]] = []

  for raw_row in raw_rows[header_index + 1 :]:
    row = {
      header: raw_row[index].strip() if index < len(raw_row) else ""
      for index, header in enumerate(headers)
    }
    rows.append(row)

  return rows


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(build_page())


@app.post("/upload", response_class=HTMLResponse)
async def upload_csv(file: UploadFile = File(...), delimiter: str = Form(",")) -> HTMLResponse:
  if not file.filename or not file.filename.lower().endswith(".csv"):
    return HTMLResponse(build_page("<div class='message error'>Solo se aceptan archivos CSV.</div>"), status_code=400)

  raw_content = await file.read()
  text_content = raw_content.decode("utf-8-sig")
  rows = parse_csv_rows(text_content, delimiter)

  message, table_html = rows_to_table(rows[:25])
  return HTMLResponse(build_page(message, table_html))