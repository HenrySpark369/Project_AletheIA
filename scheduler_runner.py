

import os
from app import create_app
from services.simulador_scheduler import iniciar_scheduler

# Activar explícitamente el scheduler
os.environ["ENABLE_SCHEDULER"] = "true"

# Crear app (necesaria si el scheduler depende del contexto de Flask)
app = create_app()

# Iniciar tareas programadas
iniciar_scheduler()

# Mantener el proceso vivo si se desea como demonio simple
try:
    import time
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print("Scheduler detenido manualmente.")