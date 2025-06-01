# db.py

import os
import sqlite3
from config import config

# Obtener la ruta de la base de datos a partir del entorno
ENTORNO = os.getenv("FLASK_ENV", "development")
DB_PATH = config[ENTORNO].DB_PATH

def get_db_connection():
    """
    Crea y devuelve una conexión SQLite configurada en modo WAL y con synchronous=NORMAL.
    Todas las operaciones de lectura/escritura deben usar este helper para evitar corrupción.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cursor = conn.cursor()
    # Activar WAL (Write-Ahead Logging) para concurrencia
    cursor.execute("PRAGMA journal_mode=WAL;")
    # Nivel de sincronización equilibrado (menor riesgo de corrupción, buen rendimiento)
    cursor.execute("PRAGMA synchronous=NORMAL;")
    return conn