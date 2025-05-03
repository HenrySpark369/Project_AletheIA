from flask import Blueprint, jsonify
from repositories.post_repo import insertar_multiples_posts
from repositories.agente_repo import obtener_todos_los_agentes
from services.simulador_service import SimuladorDeAgentes
import threading

simulador_bp = Blueprint("simulador", __name__)
db_lock = threading.Lock()

@simulador_bp.route('/actividad_automatica', methods=["POST"])
def actividad_automatica():
    try:
        agentes = obtener_todos_los_agentes()
        simulador = SimuladorDeAgentes(agentes)
        publicaciones = simulador.simular_paso()

        datos_posts = [
            (post["agente_id"], post["contenido"], post["created_at"], post["tema"] )
            for post in publicaciones
        ]

        with db_lock:
            insertar_multiples_posts(datos_posts)

        return jsonify({
            "status": "ok",
            "posts_generados": len(publicaciones)
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "mensaje": str(e)
        }), 500