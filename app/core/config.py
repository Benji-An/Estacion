from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Estacion CSV Demo"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/estacion_db"
    SECRET_KEY: str = "secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
