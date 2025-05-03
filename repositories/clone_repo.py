import sqlite3
import os
from config import config

entorno = os.getenv("FLASK_ENV", "development")
DB_PATH = config[entorno].DB_PATH

def crear_tabla_clones():
    with sqlite3.connect(DB_PATH) as conn:
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

def guardar_resultado(nombre, username, correo, ruta_imagen, resultado, score, fuente, url):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO clones (nombre, username, correo, ruta_imagen, resultado, url, score_similitud, fuente)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (nombre, username, correo, ruta_imagen, str(resultado), url, score, fuente))
    conn.commit()
    conn.close()

def obtener_historial():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM clones ORDER BY fecha DESC LIMIT 100')
        return c.fetchall()