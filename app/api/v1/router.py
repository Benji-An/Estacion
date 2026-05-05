from fastapi import APIRouter
from app.api.v1.endpoints import auth, datos, calculo

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(datos.router, prefix="/datos", tags=["datos"])
api_router.include_router(calculo.router, prefix="/calculo", tags=["cálculos hidrológicos"])
