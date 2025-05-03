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
                resultado TEXT,
                url TEXT,
                score_similitud REAL,
                fuente TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        # Modo WAL para concurrencia
        c.execute("PRAGMA journal_mode=WAL;")
        conn.commit()