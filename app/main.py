from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Backend para análisis de datos de precipitación — "
        "Universidad Cooperativa de Colombia, Santa Marta.\n\n"
        "Implementa el **Método Racional Q = C × I × A** y "
        "genera **Curvas IDF** a partir de datos de la estación HOBO/IDEAM."
    ),
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
)

# CORS — permite que el frontend consuma la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
