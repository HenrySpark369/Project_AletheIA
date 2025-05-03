from flask import Blueprint, request, render_template
from services.clone_service import procesar_busqueda_clones
from repositories.clone_repo import obtener_historial

bp = Blueprint("clones", __name__)

@bp.route("/clones", methods=["GET", "POST"])
def identificar_clones():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        username = request.form.get("username")
        correo = request.form.get("correo")
        imagen = request.files.get("imagen")

        ruta_imagen = None
        if imagen:
            ruta_imagen = f"static/uploads/{imagen.filename}"
            imagen.save(ruta_imagen)

        clones_detectados = procesar_busqueda_clones(nombre, username, correo, ruta_imagen)
        return render_template("clones/resultados.html", clones=clones_detectados)

    return render_template("clones/formulario.html")

@bp.route("/clones/historial")
def historial():
    resultados = obtener_historial()
    return render_template("clones/historial.html", resultados=resultados)