# services/usurpador_detection_service.py  
import sqlite3  
from datetime import datetime  
from collections import Counter  
from .semantic_similarity_service import SemanticSimilarityService  
from repositories.agente_repo import obtener_todos_los_agentes  
import os  
from config import config  
from itertools import combinations, islice  
import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# If your application does not already configure handlers, add a basic console handler:
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(name)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class UsurpadorDetectionService:  
    def __init__(self):  
        entorno = os.getenv("FLASK_ENV", "development")  
        self.db_path = config[entorno].DB_PATH  
        self.semantic_service = SemanticSimilarityService(self.db_path)
        self._asegurar_indice_posts()
          
    def detectar_usurpadores_semanticos(self, umbral_similitud=0.75, ventana_dias=30, bloque_tamano=5):  
        """  
        Detecta agentes usurpadores usando análisis semántico avanzado  
        Se integra con el sistema existente de agentes  
        """  
        agentes = obtener_todos_los_agentes()  
        resultados_deteccion = []  
          
        # Solo comparar agentes de tipo 'usurpador' contra los demás
        usurpadores = [a for a in agentes if a.get("tipo_agente") == "usurpador"]
        no_usurpadores = [a for a in agentes if a.get("tipo_agente") != "usurpador"]
        combinaciones = [(usurpador, otro) for usurpador in usurpadores for otro in no_usurpadores]
        total = len(combinaciones)
        for offset in range(0, total, bloque_tamano):
            combinaciones_en_bloque = combinaciones[offset:offset + bloque_tamano]
            for agente_a, agente_b in combinaciones_en_bloque:
                posts_a = self.semantic_service._obtener_posts_agente(agente_a["id"], ventana_dias)
                posts_b = self.semantic_service._obtener_posts_agente(agente_b["id"], ventana_dias)
                logger.debug(f"Obtenidos posts: agente {agente_a['id']} → {len(posts_a)} posts; "
                             f"agente {agente_b['id']} → {len(posts_b)} posts")
                similitud_semantica = self.semantic_service.similitud_semantica_agentes(
                    agente_a["id"], agente_b["id"], ventana_dias
                )
                logger.debug(f"Similitud semántica {agente_a['id']} vs {agente_b['id']}: {similitud_semantica}")
                similitud_temas = self._calcular_similitud_temas(
                    agente_a["id"], agente_b["id"], ventana_dias
                )
                logger.debug(f"Similitud temas {agente_a['id']} vs {agente_b['id']}: {similitud_temas}")
                score_final = (similitud_semantica * 0.7 + similitud_temas * 0.3)
                logger.debug(f"Score final {agente_a['id']} vs {agente_b['id']}: {score_final}")

                if score_final > umbral_similitud:
                    resultado = {
                        "agente_a": agente_a,
                        "agente_b": agente_b,
                        "score_semantico": similitud_semantica,
                        "score_temas": similitud_temas,
                        "score_total": score_final,
                        "fecha_analisis": datetime.now().isoformat(),
                        "posible_usurpador": agente_a["id"] if agente_a["id"] > agente_b["id"] else agente_b["id"]
                    }
                    resultados_deteccion.append(resultado)

            self._guardar_resultados_deteccion(resultados_deteccion)
            resultados_deteccion = []
      
    def _calcular_similitud_temas(self, agente_id_a, agente_id_b, ventana_dias):  
        """Calcula similitud basada en temas compartidos"""  
        posts_a = self.semantic_service._obtener_posts_agente(agente_id_a, ventana_dias)  
        posts_b = self.semantic_service._obtener_posts_agente(agente_id_b, ventana_dias)

        logger.debug(f"Temas: agente {agente_id_a} → {len(posts_a)} posts; agente {agente_id_b} → {len(posts_b)} posts")

        if not posts_a or not posts_b:  
            return 0.0  
              
        # Contar temas de forma robusta según el tipo de cada post
        def contar_temas(posts):
            """
            Dado un listado de posts, devuelve un Counter descontando 
            únicamente el valor del campo 'tema' (p.ej. 'educación', 'tecnología', etc.).
            """
            cnt = Counter()
            for post in posts:
                # 1) Si 'post' es un dict con clave 'tema', úsalo directamente
                if isinstance(post, dict):
                    raw_tema = post.get("tema", None)
                # 2) Si es una lista/tupla que contenga un dict adentro
                elif isinstance(post, (list, tuple)):
                    raw_tema = None
                    for elem in post:
                        if isinstance(elem, dict) and "tema" in elem:
                            raw_tema = elem["tema"]
                            break
                else:
                    raw_tema = None
                # 3) Normalizamos el valor de 'tema':
                #    Solo contamos si raw_tema es una cadena no vacía
                if isinstance(raw_tema, str) and raw_tema.strip():
                    cnt[raw_tema.strip()] += 1
            return cnt

        temas_a = contar_temas(posts_a)
        logger.debug(f"Contador temas agente {agente_id_a}: {temas_a}")
        temas_b = contar_temas(posts_b)
        logger.debug(f"Contador temas agente {agente_id_b}: {temas_b}")

        if not temas_a or not temas_b:
            return 0.0
          
        # Similitud de Jaccard  
        interseccion = sum((temas_a & temas_b).values())  
        union = sum((temas_a | temas_b).values())  
        jaccard = interseccion / union if union > 0 else 0.0
        logger.debug(f"Jaccard temas {agente_id_a} vs {agente_id_b}: {jaccard}")
        return jaccard  
      
    def _guardar_resultados_deteccion(self, resultados):  
        """Guarda resultados en base de datos"""  
        with sqlite3.connect(self.db_path) as conn:  
            cursor = conn.cursor()    
              
            # Insertar resultados  
            for resultado in resultados:  
                cursor.execute("""
                    INSERT INTO deteccion_usurpadores
                    (agente_a_id, agente_b_id, score_semantico, score_temas,
                     score_total, posible_usurpador_id, fecha_analisis)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    resultado["agente_a"]["id"],
                    resultado["agente_b"]["id"],
                    resultado["score_semantico"],
                    resultado["score_temas"],
                    resultado["score_total"],
                    resultado["posible_usurpador"],
                    resultado["fecha_analisis"]
                ))
              
            conn.commit()

    def _asegurar_indice_posts(self):
        """Crea índice si no existe para acelerar consultas por agente y rango de fechas."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_posts_agente_fecha 
                ON posts (agente_id, created_at)
            """)
            conn.commit()