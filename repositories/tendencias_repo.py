import sqlite3
from datetime import datetime, timedelta

def insertar_o_actualizar_tendencia(tipo_agente, tema, resultado):
    try:
        ahora = datetime.now().isoformat()
        with sqlite3.connect("database.db", timeout=60) as conn:
            c = conn.cursor()

            # Si ya existe, actualiza solo el campo resultado y actualizado_en
            c.execute("""
                UPDATE tendencias_cache
                SET resultado = ?, actualizado_en = ?
                WHERE tipo_agente = ? AND tema = ?
            """, (str(resultado), ahora, tipo_agente, tema))

            if c.rowcount == 0:
                # Si no existe, inserta una nueva (sin tocar promedio ni ultimo_valor si no los tienes)
                c.execute("""
                    INSERT INTO tendencias_cache (tipo_agente, tema, resultado, actualizado_en)
                    VALUES (?, ?, ?, ?)
                """, (tipo_agente, tema, str(resultado), ahora))

            conn.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] No se pudo insertar/actualizar tendencia: {e}")

def obtener_tendencias_recientes(ttl_horas=1):
    limite = datetime.now() - timedelta(hours=ttl_horas)
    limite_iso = limite.isoformat()

    with sqlite3.connect("database.db", timeout=60) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        filas = c.execute("""
            SELECT tipo_agente, tema, promedio, ultimo_valor, actualizado_en
            FROM tendencias_cache
            WHERE actualizado_en > ? AND promedio IS NOT NULL
            ORDER BY tipo_agente, promedio DESC, actualizado_en DESC
        """, (limite_iso,)).fetchall()
        return filas