from fastapi import APIRouter
from app.api.v1.endpoints import upload, auth

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# Mantenemos upload en la raiz o podemos moverlo
api_router.include_router(upload.router, prefix="", tags=["upload"])
