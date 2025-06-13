from apscheduler.schedulers.background import BackgroundScheduler
from services.simulador_service import SimuladorDeAgentes
from repositories.agente_repo import obtener_todos_los_agentes
from repositories.post_repo import insertar_multiples_posts
from services.tendencias_service import obtener_tema_en_tendencia_desde_cache
import threading
import logging
from datetime import datetime

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

db_lock = threading.Lock()

def ejecutar_simulacion_periodica():
    try:
        agentes = obtener_todos_los_agentes()
        simulador = SimuladorDeAgentes(agentes)
        publicaciones = simulador.simular_paso()
        datos = [
            (
                p["agente_id"],
                p["contenido"],
                p["created_at"].isoformat() if hasattr(p["created_at"], "isoformat") else str(p["created_at"]),
                p["tema"]
            )
            for p in publicaciones
        ]

        with db_lock:
            insertar_multiples_posts(datos)

        print(f"[SIMULADOR] {len(publicaciones)} publicaciones generadas.")
    except Exception as e:
        print(f"[SIMULADOR ERROR]: {e}")

def precachear_tendencias():
    tipos = ["normal", "usurpador", "troll", "observador"]
    for tipo in tipos:
        try:
            tema = obtener_tema_en_tendencia_desde_cache(tipo_agente=tipo, ttl_horas=1)
            print(f"[PRECACHE] Tema precargado para {tipo}: {tema}")
        except Exception as e:
            print(f"[PRECACHE ERROR] {tipo}: {e}")

def iniciar_scheduler():
    import os
    if os.environ.get("ENABLE_SCHEDULER", "false").lower() != "true":
        print("[SCHEDULER] No iniciado (ENABLE_SCHEDULER no está activo).")
        return

    scheduler = BackgroundScheduler()
    scheduler.add_job(ejecutar_simulacion_periodica, 'interval', seconds=6, max_instances=2)
    scheduler.add_job(precachear_tendencias, 'interval', hours=1)
    scheduler.start()
    print("[SCHEDULER] Simulación automática activada cada 60 segundos.")
    print(f"[SCHEDULER] Precarga de tendencias activada cada 1 hora.")
