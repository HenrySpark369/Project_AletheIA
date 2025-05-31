# app.py
import os
from flask import Flask
from routes.agentes import agentes_bp
from routes.feed import feed_bp
from routes.tendencias import tendencias_bp
from config import config
from datetime import datetime
from routes.simulador import simulador_bp
from routes.admin import admin_bp
from routes.clones import bp as clones_bp
from routes.usurpador_analysis import usurpador_analysis_bp

def create_app():
    entorno = os.getenv("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config[entorno])

    # Filtro personalizado
    @app.template_filter("datetimeformat")
    def datetimeformat(value, formato="%Y-%m-%d %H:%M"):
        try:
            dt = datetime.fromisoformat(value) if isinstance(value, str) else value
            return dt.strftime(formato)
        except Exception:
            return value

    # Blueprints
    app.register_blueprint(agentes_bp)
    app.register_blueprint(feed_bp)
    app.register_blueprint(tendencias_bp)
    app.register_blueprint(simulador_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(clones_bp)
    app.register_blueprint(usurpador_analysis_bp)

    # Ruta de salud
    @app.route("/health")
    def health_check():
        return "OK", 200

    return app

if __name__ == "__main__":
    app = create_app()

    is_gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")

    if not is_gunicorn:
        # Ejecutar tareas solo si no es Gunicorn (modo desarrollo)
        if os.getenv("INIT_DB", "false").lower() == "true":
            from utils.init_db import init_db
            init_db()

        from services.simulador_scheduler import iniciar_scheduler
        iniciar_scheduler()

        app.run(host="0.0.0.0", debug=app.config["DEBUG"])

elif os.getenv("RUN_MAIN") == "true" and "gunicorn" not in os.environ.get("SERVER_SOFTWARE", ""):
    # Protección para reinicios de Flask autoreload que ejecutan __main__ varias veces
    from services.simulador_scheduler import iniciar_scheduler
    iniciar_scheduler()