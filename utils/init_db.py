import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from db import get_db_connection
DB_PATH = Config.DB_PATH

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    c = conn.cursor()

    # Activar integridad referencial
    c.execute("PRAGMA foreign_keys = ON;")

    # Tabla de agentes
    c.execute("""
        CREATE TABLE IF NOT EXISTS agentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            edad INTEGER,
            intereses TEXT,
            tono TEXT,
            objetivo TEXT,
            tipo_agente TEXT
        )
    """)

    # Tabla de publicaciones
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agente_id INTEGER,
            contenido TEXT,
            created_at TEXT,
            tema TEXT,
            FOREIGN KEY (agente_id) REFERENCES agentes(id)
        )
    """)

    # Tabla de cache de tendencias
    c.execute("""
        CREATE TABLE IF NOT EXISTS tendencias_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_agente TEXT,
            tema TEXT,
            resultado TEXT,
            actualizado_en TEXT,
            promedio REAL,
            ultimo_valor REAL,
            UNIQUE(tipo_agente, tema)
        )
    """)

    # Tabla de resultados de clones detectados
    c.execute("""
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
    """)

    # Tabla de resultados de usurpadores detectados
    c.execute("""
        CREATE TABLE IF NOT EXISTS deteccion_usurpadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agente_a_id INTEGER,
            agente_b_id INTEGER,
            score_semantico REAL,
            score_temas REAL,
            score_total REAL,
            posible_usurpador_id INTEGER,
            fecha_analisis TEXT,
            FOREIGN KEY (agente_a_id) REFERENCES agentes(id),
            FOREIGN KEY (agente_b_id) REFERENCES agentes(id),
            FOREIGN KEY (posible_usurpador_id) REFERENCES agentes(id)
        )
    """)

    # Índices útiles
    c.execute("CREATE INDEX IF NOT EXISTS idx_posts_agente_id ON posts(agente_id);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tendencias_tipo_agente ON tendencias_cache(tipo_agente);")

    # Búsqueda por campos clave - para buscar clones por username, correo, o nombre
    c.execute("CREATE INDEX IF NOT EXISTS idx_clones_username ON clones(username);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_clones_correo ON clones(correo);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_clones_nombre ON clones(nombre);")
    # Ordenamiento por fecha - visualización de resultados recientes, ordenados por fecha
    c.execute("CREATE INDEX IF NOT EXISTS idx_clones_fecha ON clones(fecha);")
    # Filtrado por fuente o score_similitud - análisis por fuente (Yandex, DuckDuckGo, Sherlock, etc.), o para rankear por score
    c.execute("CREATE INDEX IF NOT EXISTS idx_clones_fuente ON clones(fuente);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_clones_score_similitud ON clones(score_similitud);")
    # Búsqueda compuesta - optimizar una consulta que use username + fuente
    c.execute("CREATE INDEX IF NOT EXISTS idx_clones_username_fuente ON clones(username, fuente);")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("[INIT_DB] Base de datos inicializada correctamente en:", DB_PATH)