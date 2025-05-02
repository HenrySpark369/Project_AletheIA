from flask import Blueprint, render_template, redirect, url_for, flash
from services.simulador_scheduler import ejecutar_simulacion_periodica, precachear_tendencias
from repositories.post_repo import obtener_feed

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin")
def panel_admin():
    posts = obtener_feed(limit=10)
    return render_template("admin.html", posts=posts)

@admin_bp.route("/admin/forzar_simulacion")
def forzar_simulacion():
    publicaciones = ejecutar_simulacion_periodica()
    if publicaciones is None:
        flash("No se generaron publicaciones.")
    else:
        flash(f"{len(publicaciones)} publicaciones generadas manualmente.")
    return redirect(url_for("admin.panel_admin"))

@admin_bp.route("/admin/forzar_precache")
def forzar_precache():
    precachear_tendencias()
    flash("Precarga de tendencias ejecutada.")
    return redirect(url_for("admin.panel_admin"))