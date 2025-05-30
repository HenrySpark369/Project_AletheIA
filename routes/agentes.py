from flask import Blueprint, render_template, request, redirect, jsonify
from repositories.agente_repo import obtener_todos_los_agentes, insertar_multiples_agentes, eliminar_todos_los_agentes
from repositories.post_repo import insertar_multiples_posts, eliminar_todos_los_posts, obtener_posts_por_agente
from services.simulador_service import SimuladorDeAgentes
import threading
import datetime

db_lock = threading.Lock()

agentes_bp = Blueprint("agentes", __name__)

@agentes_bp.route('/agentes')
def lista_agentes():
    agentes = obtener_todos_los_agentes()
    return render_template("agentes.html", agentes=agentes)

@agentes_bp.route('/crear_agente', methods=['POST'])
def crear_agente():
    insertar_agente(
        request.form["nombre"],
        int(request.form["edad"]),
        request.form["intereses"],
        request.form["tono"],
        request.form["objetivo"],
        request.form["tipo_agente"]
    )
    return redirect("/agentes")

@agentes_bp.route('/limpiar_agentes', methods=['POST'])
def limpiar_agentes():
    eliminar_todos_los_posts()
    eliminar_todos_los_agentes()
    return redirect('/agentes')

@agentes_bp.route('/agente/<int:agente_id>')
def muro_agente(agente_id):
    from repositories.post_repo import obtener_posts_por_agente
    from repositories.agente_repo import obtener_agente_por_id

    agente = obtener_agente_por_id(agente_id)
    if not agente:
        return "Agente no encontrado", 404

    posts = obtener_posts_por_agente(agente_id)
    return render_template("muro_agente.html", agente=agente, posts=posts)

@agentes_bp.route('/editar_agente/<int:agente_id>', methods=["GET", "POST"])
def editar_agente(agente_id):
    from repositories.agente_repo import obtener_agente_por_id, actualizar_agente

    if request.method == "POST":
        actualizar_agente(
            agente_id,
            request.form["nombre"],
            int(request.form["edad"]),
            request.form["intereses"],
            request.form["tono"],
            request.form["objetivo"],
            request.form["tipo_agente"]
        )
        return redirect("/agentes")

    agente = obtener_agente_por_id(agente_id)
    if not agente:
        return "Agente no encontrado", 404

    return render_template("editar_agente.html", agente=agente)

@agentes_bp.route('/agente_fragment/<int:agente_id>')
def agente_fragment(agente_id):
    desde = request.args.get("desde")

    try:
        posts = obtener_posts_por_agente(agente_id)
        if desde:
            # Filtrar manualmente si el repo aún no filtra por fecha
            posts = [p for p in posts if p["created_at"] > desde]
    except Exception as e:
        print(f"[ERROR] Fragmento agente {agente_id}:", e)
        posts = []

    return render_template("partials/agente_posts.html", posts=posts)

@agentes_bp.route('/cargar_demo', methods=["POST"])
def cargar_demo():
    lista_agentes = [
        (
            "Musa Rebelde",
            27,
            "moda sostenible, feminismo interseccional, arte urbano crítico",
            "apasionada, reivindicativa y enérgica",
            "generar conciencia social a través del arte callejero y la moda con mensaje",
            "normal"
        ),
        (
            "Thaddeus Ross",
            34,
            "política nacional e internacional, defensa, análisis geopolítico",
            "serio, analítico y mesurado",
            "ofrecer análisis experto para orientar la opinión pública sobre seguridad",
            "normal"
        ),
        (
            "Dua Lupita",
            22,
            "tendencias de TikTok, maquillaje viral, música pop, challenges",
            "juvenil, enérgica y juguetona",
            "entretener imitando a las estrellas y captar seguidores con humor y retos virales",
            "usurpador"
        ),
        (
            "Dr. Connors",
            49,
            "ciencia genética, reptiles, bioingeniería, ética en investigación",
            "explicativo, riguroso y didáctico",
            "divulgar avances en biotecnología y generar conciencia ética en ciencia",
            "normal"
        ),
        (
            "El Crítico Anónimo",
            38,
            "cine independiente, cine comercial, memes de crítica, polémicas culturales",
            "cínico, mordaz y provocador",
            "desatar debates ácidos sobre cine y cultura pop para generar polémica",
            "troll"
        ),
        (
            "Beauty_Looks",
            19,
            "reseñas de maquillaje, tendencias beauty, giveaways, looks virales",
            "alegre, glamurosa y superficial",
            "atraer likes copiando y adaptando tendencias de influencers de moda",
            "usurpador"
        ),
        (
            "Cryptoboy",
            24,
            "criptomonedas emergentes, análisis de gráficos, bots de trading, IA aplicada al trading",
            "técnico improvisado y grandilocuente",
            "simular que es un trader experto compartiendo análisis copiados de figuras influyentes",
            "usurpador"
        ),
        (
            "PhotoStudio",
            31,
            "fotografía de paisajes, viajes fotográficos, composición visual, edición de imágenes",
            "inspirador, reflexivo y detallista",
            "mostrar estilo de vida aspiracional mientras enseña técnicas fotográficas",
            "observador"
        ),
        (
            "Chayotito_tired",
            20,
            "memes universitarios, quejas estudiantiles, cultura pop joven, política local",
            "sarcástico, irreverente y algo agotado",
            "satirizar la vida universitaria y la situación sociopolítica con humor ácido",
            "troll"
        ),
        (
            "ManagerX",
            40,
            "coaching empresarial, productividad, liderazgo, desarrollo personal",
            "motivacional, enfocado y persuasivo",
            "atraer clientes ofreciendo consejos de negocio y autoayuda",
            "normal"
        ),
        (
            "Daily Buggle",
            50,
            "noticias de superhéroes, rumores de celebridades, cultura pop, teorías conspirativas",
            "sensacionalista, agresivo y conspiranoico",
            "mantener en tendencia cualquier escándalo o rumor sobre El Hombre Araña para atraer tráfico",
            "normal"
        )
    ]

    try:
        with db_lock:
            agentes_ids = insertar_multiples_agentes(lista_agentes)

        agentes_guardados = [
            {
                "id": agentes_ids[i],
                "nombre": a[0],
                "edad": a[1],
                "intereses": a[2],
                "tono": a[3],
                "objetivo": a[4],
                "tipo_agente": a[5]
            }
            for i, a in enumerate(lista_agentes)
        ]

        simulador = SimuladorDeAgentes(agentes_guardados)
        publicaciones = simulador.simular_paso()

        datos_posts_demo = [
            (pub["agente_id"], pub["contenido"], pub["created_at"], pub["tema"])
            for pub in publicaciones
        ]

        with db_lock:
            insertar_multiples_posts(datos_posts_demo)

        print(f"[SIM-DEMO] Se generaron {len(publicaciones)} publicaciones para demo.")

        return jsonify({
            "status": "success",
            "message": "Agentes cargados correctamente.",
            "agentes_creados": len(agentes_guardados),
            "posts_generados": len(publicaciones)
        }), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500