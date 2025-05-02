# utils/init_db.py
import sqlite3

def init_db():
    with sqlite3.connect("database.db", timeout=60) as conn:
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

        # Índices útiles
        c.execute("CREATE INDEX IF NOT EXISTS idx_posts_agente_id ON posts(agente_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tendencias_tipo_agente ON tendencias_cache(tipo_agente);")

        # Modo WAL para concurrencia
        c.execute("PRAGMA journal_mode=WAL;")
        conn.commit()