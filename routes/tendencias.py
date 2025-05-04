from flask import Blueprint, render_template, request
from services.tendencias_service import tendencias
from repositories.tendencias_repo import insertar_o_actualizar_tendencia, obtener_tendencias_recientes

tendencias_bp = Blueprint("tendencias", __name__)

@tendencias_bp.route("/tendencias", methods=["GET", "POST"])
def ver_tendencias():
    resultados = None
    mensaje = None
    tendencias_por_tipo = {}

    if request.method == "POST":
        tema = request.form.get("tema", "").strip()
        geo = request.form.get("geo", "MX-DIF").strip()

        if not tema:
            mensaje = "Por favor ingresa un tema para buscar."
        else:
            try:
                resultados = tendencias(tema, geo)
                insertar_o_actualizar_tendencia("general", tema, resultados)
            except Exception as e:
                print("[ERROR en tendencias POST]:", e)
                mensaje = "Error consultando tendencias externas."

    if request.method == "GET" or not resultados:
        filas = obtener_tendencias_recientes(ttl_horas=1)
        for row in filas:
            tipo = row["tipo_agente"]
            tendencias_por_tipo.setdefault(tipo, []).append(row)

    return render_template("tendencias.html",
                           resultados=resultados,
                           tendencias=tendencias_por_tipo,
                           mensaje=mensaje)