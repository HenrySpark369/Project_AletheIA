import random
import numpy as np
from datetime import datetime, timedelta
from agents import generar_post
from trends import obtener_tema, obtener_temas_distintos, obtener_tema_en_tendencia_desde_cache

class SimuladorDeAgentes:
    def __init__(self, agentes):
        self.agentes = agentes
        self.estado_agentes = {a['id']: 'inactivo' for a in agentes}
        self.hora_simulada = datetime.now()

        # Probabilidades de publicar por tipo de agente
        self.probabilidades = {
            "troll": 0.6,
            "normal": 0.3,
            "imitador": 0.4,
            "observador": 0.1
        }

        # Transiciones Markov simples: estados de comportamiento
        self.transiciones = {
            "inactivo": {"leyendo": 0.6, "posteando": 0.4},
            "leyendo": {"posteando": 0.5, "inactivo": 0.5},
            "posteando": {"inactivo": 1.0}
        }

    def siguiente_estado(self, estado_actual):
        estados, probs = zip(*self.transiciones[estado_actual].items())
        return np.random.choice(estados, p=probs)

    def simular_paso(self):
        publicaciones = []

        for agente in self.agentes:
            agente_id = agente["id"]
            tipo = agente["tipo_agente"]
            estado_actual = self.estado_agentes[agente_id]
            nuevo_estado = self.siguiente_estado(estado_actual)
            self.estado_agentes[agente_id] = nuevo_estado

            if nuevo_estado == "posteando":
                prob_post = self.probabilidades.get(tipo, 0.2)
                if random.random() < prob_post:
                    if tipo in ["normal", "imitador"]:  # Puedes decidir quién usa tendencias reales
                        tema = obtener_tema_en_tendencia_desde_cache(tipo)
                    else:
                        tema = obtener_tema(tipo)
                    contenido = generar_post(agente, tema)
                    publicaciones.append({
                        "agente_id": agente_id,
                        "contenido": contenido,
                        "tema": tema,
                        "timestamp": self.hora_simulada.isoformat()
                    })

        # Avanza el reloj simulado
        self.hora_simulada += timedelta(seconds=random.randint(60, 150))
        return publicaciones