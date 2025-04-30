from flask import Flask, render_template, request, redirect, jsonify
from trends import obtener_tema, obtener_temas_distintos
from datetime import datetime, timedelta
from simulador import SimuladorDeAgentes
from agents import generar_post
import threading
import signal
import sqlite3
import agents
import random
import time
import os
import sys
from dotenv import load_dotenv
load_dotenv()

db_lock = threading.Lock()

def init_db():
    with sqlite3.connect("database.db", timeout=60) as conn:
        c = conn.cursor()

        # Tabla agentes
        c.execute("""
            CREATE TABLE IF NOT EXISTS agentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                edad INTEGER,
                intereses TEXT,
                tono TEXT,
                objetivo TEXT,
                tipo_agente TEXT NOT NULL
            );
        """)

        # Tabla posts
        c.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agente_id INTEGER,
                contenido TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agente_id) REFERENCES agentes(id)
            );
        """)

        # Tabla tendencias_cache extendida
        c.execute("""
            CREATE TABLE IF NOT EXISTS tendencias_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_agente TEXT NOT NULL,
                tema TEXT NOT NULL,
                resultado TEXT,
                actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                promedio REAL,              -- Nuevo campo: score promedio
                ultimo_valor REAL           -- Nuevo campo: valor más reciente
            );
        """)

        # Restricción opcional para evitar duplicados por tipo_agente + tema
        c.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_tendencia_unica 
            ON tendencias_cache (tipo_agente, tema);
        """)

        # Índices para acelerar búsqueda y ordenamiento
        c.execute("CREATE INDEX IF NOT EXISTS idx_posts_agente_id ON posts (agente_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts (created_at);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tendencias_tipo ON tendencias_cache (tipo_agente);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tendencias_fecha ON tendencias_cache (actualizado_en);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_posts_fecha_agente ON posts (created_at, agente_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_agentes_tipo ON agentes (tipo_agente);")

        conn.commit()
    print("[INFO] Base de datos verificada e inicializada correctamente.")
    
def signal_handler(sig, frame):
    print("\n[INFO] Ctrl+C detectado. Deteniendo hilo de actividad automática...")
    stop_event.set()
    if hilo and hilo.is_alive():
        hilo.join(timeout=5)
        print("[INFO] Hilo finalizado correctamente.")
    else:
        print("[INFO] Hilo ya había terminado.")
    sys.exit(0)

stop_event = threading.Event()
signal.signal(signal.SIGINT, signal_handler)


def actividad_automatica():
    while not stop_event.is_set():
        with db_lock:
            try:
                with sqlite3.connect("database.db", timeout=60) as conn:
                    conn.row_factory = sqlite3.Row
                    c = conn.cursor()

                    agentes = c.execute("SELECT * FROM agentes").fetchall()

                    if not agentes:
                        print("[INFO] No hay agentes aún. Esperando...")
                        time.sleep(60)
                        continue

                    agentes_dicts = [dict(a) for a in agentes]
                    simulador = SimuladorDeAgentes(agentes_dicts)

                    publicaciones = simulador.simular_paso()

                    datos_a_insertar = [
                        (pub["agente_id"], pub["contenido"], pub["timestamp"])
                        for pub in publicaciones
                    ]

                    c.executemany(
                        "INSERT INTO posts (agente_id, contenido, created_at) VALUES (?, ?, ?)",
                        datos_a_insertar
                    )
                    conn.commit()

                    for pub in publicaciones:
                        print(f"[SIM] Agente {pub['agente_id']} publicó sobre '{pub['tema']}'")

                delay = random.randint(20, 60)
                for _ in range(delay):
                    if stop_event.is_set():
                        break
                    time.sleep(1)

            except Exception as e:
                print("[ERROR en simulador]:", e)
                time.sleep(60)

app = Flask(__name__)

@app.template_filter('datetimeformat')
def datetimeformat(value, formato="%d de %B de %Y, %I:%M %p"):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value  # por si viene en otro formato no parseable
    return value.strftime(formato)

@app.route('/')
def index():
    return redirect('/feed')

@app.route('/feed')
def feed_global():
    try:
        pagina = int(request.args.get("page", 1))
        por_pagina = 10
        offset = (pagina - 1) * por_pagina

        with sqlite3.connect("database.db", timeout=60) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            total_posts = c.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
            total_paginas = (total_posts + por_pagina - 1) // por_pagina

            posts = c.execute("""
                SELECT posts.contenido, agentes.nombre, posts.created_at
                FROM posts
                JOIN agentes ON posts.agente_id = agentes.id
                ORDER BY posts.created_at DESC
                LIMIT ? OFFSET ?
            """, (por_pagina, offset)).fetchall()

        return render_template(
            "feed.html",
            posts=posts,
            pagina=pagina,
            total_paginas=total_paginas
        )

    except Exception as e:
        print("[ERROR en paginación /feed]:", e)
        return "<p><em>Error cargando el feed.</em></p>"

@app.route('/crear_agente', methods=['GET', 'POST'])
def crear_agente():
    if request.method == 'POST':
        datos = (
            request.form['nombre'],
            int(request.form['edad']),
            request.form['intereses'],
            request.form['tono'],
            request.form['objetivo'],
            request.form['tipo_agente']
        )
        with sqlite3.connect("database.db", timeout=60) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO agentes (nombre, edad, intereses, tono, objetivo, tipo_agente) VALUES (?, ?, ?, ?, ?, ?)", datos)
            agente_id = c.lastrowid
            agente = {
                "nombre": datos[0],
                "edad": datos[1],
                "intereses": datos[2],
                "tono": datos[3],
                "objetivo": datos[4],
                "tipo_agente": datos[5]
            }
            post = agents.generar_post(agente, "Tendencias actuales en redes sociales")
            c.execute("INSERT INTO posts (agente_id, contenido) VALUES (?, ?)", (agente_id, post))
            conn.commit()
        return redirect('/')

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"status": "ok"})
    else:
        return render_template('crear_agente.html')

@app.route('/agentes')
def ver_agentes():
    with sqlite3.connect("database.db", timeout=60) as conn:
        c = conn.cursor()
        agentes = c.execute("SELECT id, nombre, edad, intereses, tono, objetivo, tipo_agente FROM agentes").fetchall()
    return render_template("agentes.html", agentes=agentes)

@app.route('/eliminar_agente/<int:agente_id>', methods=['POST'])
def eliminar_agente(agente_id):
    with sqlite3.connect("database.db", timeout=60) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM posts WHERE agente_id = ?", (agente_id,))
        c.execute("DELETE FROM agentes WHERE id = ?", (agente_id,))
        conn.commit()
    return redirect('/agentes')

@app.route('/editar_agente/<int:agente_id>', methods=['GET', 'POST'])
def editar_agente(agente_id):
    with sqlite3.connect("database.db", timeout=60) as conn:
        c = conn.cursor()
        if request.method == 'POST':
            datos = (
                request.form['nombre'],
                int(request.form['edad']),
                request.form['intereses'],
                request.form['tono'],
                request.form['objetivo'],
                request.form['tipo_agente'],
                agente_id
            )
            c.execute("""
                UPDATE agentes
                SET nombre=?, edad=?, intereses=?, tono=?, objetivo=?, tipo_agente=?
                WHERE id=?
            """, datos)
            conn.commit()
            return redirect('/agentes')
        else:
            agente = c.execute("SELECT * FROM agentes WHERE id = ?", (agente_id,)).fetchone()
            return render_template("editar_agente.html", agente=agente)

@app.route('/agente/<int:agente_id>', methods=['GET', 'POST'])
def muro_agente(agente_id):
    with sqlite3.connect("database.db", timeout=60) as conn:
        c = conn.cursor()

        # Obtener info del agente
        agente = c.execute("SELECT * FROM agentes WHERE id = ?", (agente_id,)).fetchone()

        # Si se da clic en "generar post"
        if request.method == 'POST':
            agente_dict = {
                "nombre": agente[1],
                "edad": agente[2],
                "intereses": agente[3],
                "tono": agente[4],
                "objetivo": agente[5],
                "tipo_agente": agente[6]
            }
            
            nuevo_post = generar_post(agente_dict, "Generar contenido nuevo")
            c.execute("INSERT INTO posts (agente_id, contenido) VALUES (?, ?)", (agente_id, nuevo_post))
            conn.commit()

        # Obtener posts del agente
        posts = c.execute("""
            SELECT contenido, created_at 
            FROM posts 
            WHERE agente_id = ? 
            ORDER BY id DESC
            """, (agente_id,)).fetchall()
    return render_template("muro_agente.html", agente=agente, posts=posts)

@app.route('/agente_fragment/<int:agente_id>')
def agente_fragment(agente_id):
    with sqlite3.connect("database.db", timeout=60) as conn:
        posts = conn.execute("""
            SELECT contenido, created_at 
            FROM posts 
            WHERE agente_id = ? 
            ORDER BY id DESC
        """, (agente_id,)).fetchall()
    return render_template("partials/agente_posts.html", posts=posts)

@app.route('/cargar_agentes_demo', methods=['POST'])
def cargar_agentes_demo():
    with db_lock:
        lista_agentes = [
            ("Musa Rebelde", 27, "moda, feminismo, arte urbano", "apasionado", "generar conciencia", "normal"),
            ("Thaddeus Ross", 60, "Seguridad nacional, control militar, captura de Hulk, poder, disciplina", "Autoritario, severo, inflexible, patriótico", "Proteger a México a toda costa, controlar o destruir a Hulk, mantener el orden mediante la fuerza", "observador"),
            ("Dua Lupita", 22, "Dua, maquillaje, tutoriales, tiktok", "juvenil", "entretener y ganar seguidores", "imitador"),
            ("Dr. Curt Connors", 49, "Ciencia, regeneración celular, genética, curación de enfermedades humanas, redención personal", "Trágico, racional, obsesivo, científico", "Sanar su propio cuerpo (recuperar su brazo perdido) y ayudar a la humanidad, aunque a veces se desvía por su transformación en el Lagarto", "normal"),
            ("El Crítico Anónimo", 38, "cine, política, redes sociales", "cínico", "causar controversia", "troll"),
            ("Beauty_Looks", 19, "influencers, moda, giveaways", "superficial", "atraer likes", "imitador"),
            ("Cryptoboy", 0, "criptomonedas, inteligencia artificial, tendencias", "técnico", "simular actividad real", "imitador"),
            ("PhotoStudio", 31, "fotografía, viajes, diseño", "inspirador", "mostrar estilo de vida", "observador"),
            ("Chayotito_tired", 20, "memes, universidad, quejas", "sarcástico", "hacer de mexico un lugar mejor", "troll"),
            ("ManagerX", 40, "coaching, negocios, empoderamiento", "motivacional", "atraer clientes", "normal"),
            ("Daily Buggle", 50, "Noticias sensacionalistas, escándalos, fotografía de Spider-Man, opinión pública, control mediático", "Sensacionalista, agresivo, amarillista, influyente", "Vender noticias, moldear la percepción pública (especialmente en contra de Spider-Man), mantener relevancia mediática", "troll")
        ]
        agentes_guardados = []
        try:
            with sqlite3.connect("database.db", timeout=60) as conn:
                c = conn.cursor()
                for a in lista_agentes:
                    c.execute("INSERT INTO agentes (nombre, edad, intereses, tono, objetivo, tipo_agente) VALUES (?, ?, ?, ?, ?, ?)", a)
                    agente_id = c.lastrowid

                    # Crear post usando OpenAI
                    agente_dict = {
                        "id": agente_id,
                        "nombre": a[0],
                        "edad": a[1],
                        "intereses": a[2],
                        "tono": a[3],
                        "objetivo": a[4],
                        "tipo_agente": a[5]
                    }
                    agentes_guardados.append(agente_dict)

                # Usar simulador para generar publicaciones iniciales
                simulador = SimuladorDeAgentes(agentes_guardados)
                publicaciones = simulador.simular_paso()
                
                # Agrupar e insertar todas las publicaciones
                datos_posts_demo = [
                    (pub["agente_id"], pub["contenido"], pub["timestamp"])
                    for pub in publicaciones
                ]

                c.executemany(
                    "INSERT INTO posts (agente_id, contenido, created_at) VALUES (?, ?, ?)",
                    datos_posts_demo
                )

                for pub in publicaciones:
                    print(f"[SIM-DEMO] {pub['agente_id']} publicó '{pub['tema']}'")
                conn.commit()
            return jsonify({
                "status": "success",
                "message": "Agentes de demostración cargados correctamente.",
                "agentes_creados": len(agentes_guardados),
                "posts_generados": len(publicaciones)
            }), 201
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/limpiar_agentes', methods=['POST'])
def limpiar_agentes():
    with sqlite3.connect("database.db", timeout=60) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM posts")
        c.execute("DELETE FROM agentes")
        conn.commit()
    return redirect('/agentes')

@app.route('/feed_fragment')
def feed_fragment():
    with db_lock:
        try:
            desde = request.args.get("desde")
            with sqlite3.connect("database.db", timeout=60) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()

                query = """
                    SELECT posts.contenido, agentes.nombre, posts.created_at
                    FROM posts
                    JOIN agentes ON posts.agente_id = agentes.id
                """
                params = []
                if desde:
                    query += " WHERE posts.created_at > ?"
                    params.append(desde)

                query += " ORDER BY posts.created_at DESC LIMIT 10"
                posts = c.execute(query, params).fetchall()

            if not posts:
                return ""  # ← Importante: no insertar nada si no hay nuevos posts

            return render_template("partials/feed_items.html", posts=posts)

        except sqlite3.Error as e:
            print("[ERROR en feed_fragment]:", e)
            return ""

from trends import tendencias

@app.route("/tendencias", methods=["GET", "POST"])
def ver_tendencias():
    resultados = None
    tendencias_por_tipo = {}
    mensaje = None

    if request.method == "POST":
        tema = request.form.get("tema", "").strip()
        geo = request.form.get("geo", "MX-DIF").strip()

        if not tema:
            mensaje = "Por favor ingresa un tema para buscar."
        else:
            resultados = tendencias(tema, geo)
            with sqlite3.connect("database.db", timeout=60) as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT OR REPLACE INTO tendencias_cache (tipo_agente, tema, resultado, actualizado_en)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, ("general", tema, str(resultados)))
                conn.commit()
    else:
        # GET → mostrar el dashboard de tendencias más recientes
        with sqlite3.connect("database.db", timeout=60) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            filas = c.execute('''
                SELECT tipo_agente, tema, promedio, ultimo_valor, actualizado_en
                FROM tendencias_cache
                WHERE actualizado_en >= datetime('now', '-6 hours')
                ORDER BY tipo_agente, promedio DESC, actualizado_en DESC
            ''').fetchall()

        for row in filas:
            tipo = row["tipo_agente"]
            tendencias_por_tipo.setdefault(tipo, []).append(row)

    return render_template("tendencias.html", resultados=resultados, tendencias=tendencias_por_tipo, mensaje=mensaje)

if __name__ == '__main__':
    init_db()
    hilo = threading.Thread(target=actividad_automatica, daemon=True)
    hilo.start()
    app.run(host="0.0.0.0", debug=True, use_reloader=True)