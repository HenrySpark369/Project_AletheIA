import random
import numpy as np
from datetime import datetime, timedelta
from utils.generador_contenido import generar_post
from services.tendencias_service import obtener_tema, obtener_tema_en_tendencia_desde_cache

class SimuladorDeAgentes:
    def __init__(self, agentes,
                 generar_post_fn=generar_post,
                 obtener_tema_fn=obtener_tema,
                 obtener_tema_cache_fn=obtener_tema_en_tendencia_desde_cache):
        self.agentes = agentes
        self.estado_agentes = {a['id']: 'inactivo' for a in agentes}
        self.hora_simulada = datetime.now()

        self.generar_post = generar_post_fn
        self.obtener_tema = obtener_tema_fn
        self.obtener_tema_cache = obtener_tema_cache_fn

        self.probabilidades = {
            "troll": 0.6,
            "normal": 0.3,
            "usurpador": 0.4,
            "observador": 0.1
        }

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
                prob_post = self.probabilidades.get(tipo)
                if prob_post is None or random.random() >= prob_post:
                    continue

                try:
                    if tipo == "usurpador":
                        tema, promedio, ultimo_valor = self.obtener_tema_cache(tipo)

                        try:
                            promedio = float(promedio) if promedio is not None else None
                        except Exception:
                            promedio = None
                        try:
                            ultimo_valor = float(ultimo_valor) if ultimo_valor is not None else None
                        except Exception:
                            ultimo_valor = None

                        es_tendencia = (
                            promedio is not None and 
                            ultimo_valor is not None and 
                            ultimo_valor > promedio
                        )

                        if not es_tendencia:
                            tema, contexto = self.imitar_agente(agente)
                        else:
                            contexto = {
                                "tema": tema,
                                "promedio": promedio,
                                "ultimo_valor": ultimo_valor,
                                "es_tendencia": es_tendencia
                            }

                    elif tipo == "normal":
                        tema, promedio, ultimo_valor = self.obtener_tema_cache(tipo)

                        try:
                            promedio = float(promedio) if promedio is not None else None
                        except Exception:
                            promedio = None
                        try:
                            ultimo_valor = float(ultimo_valor) if ultimo_valor is not None else None
                        except Exception:
                            ultimo_valor = None

                        es_tendencia = (
                            promedio is not None and 
                            ultimo_valor is not None and 
                            ultimo_valor > promedio
                        )

                        contexto = {
                            "tema": tema,
                            "promedio": promedio,
                            "ultimo_valor": ultimo_valor,
                            "es_tendencia": es_tendencia
                        }
                    else:
                        tema = self.obtener_tema(tipo)
                        contexto = {"tema": tema}

                    contenido = self.generar_post(agente, contexto)

                    publicaciones.append({
                        "agente_id": agente_id,
                        "contenido": contenido,
                        "created_at": self.hora_simulada.isoformat(),
                        "tema": tema
                    })
                except Exception as e:
                    print(f"[SIMULADOR ERROR con agente {agente_id}]: {e}")

        self.hora_simulada += timedelta(seconds=random.randint(60, 150))
        return publicaciones

    def imitar_agente(self, usurpador):
        candidatos = [a for a in self.agentes if a["tipo_agente"] != "usurpador"]
        if not candidatos:
            return None, {"tema": "tema_general"}

        elegido = random.choice(candidatos)

        # Suponemos que puedes acceder a sus publicaciones históricas
        from repositories.post_repo import obtener_ultimos_posts_de_agente
        posts = obtener_ultimos_posts_de_agente(elegido["id"], limite=1)

        if posts:
            tema = posts[0]["tema"]
            contexto = {"tema": tema}
            return tema, contexto
        else:
            return None, {"tema": "tema_general"}