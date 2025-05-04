import sqlite3
from datetime import datetime

def insertar_o_actualizar_tendencia(tipo_agente, tema, resultado):
    with sqlite3.connect("database.db", timeout=60) as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO tendencias_cache (tipo_agente, tema, resultado, actualizado_en)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (tipo_agente, tema, str(resultado)))
        conn.commit()

def obtener_tendencias_recientes(ttl_horas=1):
    with sqlite3.connect("database.db", timeout=60) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        filas = c.execute("""
            SELECT tipo_agente, tema, promedio, ultimo_valor, actualizado_en
            FROM tendencias_cache
            WHERE actualizado_en >= datetime('now', ?)
            ORDER BY tipo_agente, promedio DESC, actualizado_en DESC
        """, (f'-{ttl_horas} hours',)).fetchall()
        return filas