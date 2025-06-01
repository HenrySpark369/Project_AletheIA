import sqlite3  # Keep for row_factory if needed
from db import get_db_connection
import os
from config import config

entorno = os.getenv("FLASK_ENV", "development")
DB_PATH = config[entorno].DB_PATH

def crear_tabla_clones():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS clones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            username TEXT,
            correo TEXT,
            ruta_imagen TEXT,
            contenido TEXT,
            url TEXT,
            score_similitud REAL,
            fuente TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def guardar_resultado(nombre, username, correo, ruta_imagen, resultado, score, fuente, url):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO clones (nombre, username, correo, ruta_imagen, contenido, url, score_similitud, fuente)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (nombre, username, correo, ruta_imagen, str(resultado), url, f"{score*100:.2f}", fuente))
    conn.commit()
    conn.close()

def obtener_historial():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM clones ORDER BY fecha DESC LIMIT 100')
    rows = c.fetchall()
    conn.close()
    return rows