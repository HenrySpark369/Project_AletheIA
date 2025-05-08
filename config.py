# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # Carga variables desde .env


class Config:
    DEBUG = False
    TESTING = False

    # Para uso con ORMs como SQLAlchemy (opcional)
    DATABASE_URI = "sqlite:///database.db"

    # Para uso directo con sqlite3
    DB_PATH = os.getenv("DB_PATH", "database.db")

    # APIs
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SERPAPI_KEY = os.getenv("SERPAPI_KEY")

    # Región por defecto para Google Trends
    GEO_DEFAULT = os.getenv("GEO_DEFAULT", "MX-DIF")

    # SECRET KEY FLASH
    SECRET_KEY = os.getenv("SECRET_KEY", "clave-fallback")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DATABASE_URI = os.getenv("DATABASE_URL", Config.DATABASE_URI)
    DB_PATH = os.getenv("DB_PATH", "database.db")


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
