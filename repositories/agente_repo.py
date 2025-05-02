# repositories/agente_repo.py
import sqlite3
import os
from config import config
from models.agente import Agente

# Obtener el path correcto según entorno (dev/prod)
entorno = os.getenv("FLASK_ENV", "development")
DB_PATH = config[entorno].DB_PATH

def obtener_conexion():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn

def obtener_todos_los_agentes():
    with obtener_conexion() as conn:
        filas = conn.execute("SELECT * FROM agentes").fetchall()
        return [Agente(**fila).to_dict() for fila in filas]

def insertar_multiples_agentes(lista_agentes):
    with obtener_conexion() as conn:
        c = conn.cursor()
        c.executemany("""
            INSERT INTO agentes (nombre, edad, intereses, tono, objetivo, tipo_agente)
            VALUES (?, ?, ?, ?, ?, ?)
        """, lista_agentes)
        conn.commit()

        # Recuperar últimos N IDs insertados
        c.execute("SELECT id FROM agentes ORDER BY id DESC LIMIT ?", (len(lista_agentes),))
        rows = c.fetchall()
        ids = [row[0] for row in rows][::-1]  # Revertimos para conservar el orden original
        return ids

def eliminar_todos_los_agentes():
    with obtener_conexion() as conn:
        conn.execute("DELETE FROM agentes")
        conn.commit()

def obtener_agente_por_id(agente_id):
    with obtener_conexion() as conn:
        fila = conn.execute("SELECT * FROM agentes WHERE id = ?", (agente_id,)).fetchone()
        return dict(fila) if fila else None

def actualizar_agente(agente_id, nombre, edad, intereses, tono, objetivo, tipo_agente):
    with obtener_conexion() as conn:
        conn.execute("""
            UPDATE agentes
            SET nombre = ?, edad = ?, intereses = ?, tono = ?, objetivo = ?, tipo_agente = ?
            WHERE id = ?
        """, (nombre, edad, intereses, tono, objetivo, tipo_agente, agente_id))
        conn.commit()