from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from app.services.csv_service import parse_csv_rows
from typing import Any, Dict

router = APIRouter()

@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), delimiter: str = Form(",")) -> Dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos CSV.")

    try:
        raw_content = await file.read()
        text_content = raw_content.decode("utf-8-sig")
        rows = parse_csv_rows(text_content, delimiter)
        
        return {
            "message": "Archivo procesado exitosamente",
            "filename": file.filename,
            "total_rows": len(rows),
            "data": rows[:50] # Retornamos un máximo de 50 para no saturar la respuesta, ajustable
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
