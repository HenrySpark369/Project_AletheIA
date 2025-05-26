# services/imitador_detection_service.py  
import sqlite3  
from datetime import datetime  
from collections import Counter  
from .semantic_similarity_service import SemanticSimilarityService  
from repositories.agente_repo import obtener_todos_los_agentes  
import os  
from config import config  
from itertools import combinations, islice  
  
class ImitadorDetectionService:  
    def __init__(self):  
        entorno = os.getenv("FLASK_ENV", "development")  
        self.db_path = config[entorno].DB_PATH  
        self.semantic_service = SemanticSimilarityService(self.db_path)  
          
    def detectar_imitadores_semanticos(self, umbral_similitud=0.75, ventana_dias=30, bloque_tamano=5):  
        """  
        Detecta agentes imitadores usando análisis semántico avanzado  
        Se integra con el sistema existente de agentes  
        """  
        agentes = obtener_todos_los_agentes()  
        resultados_deteccion = []  
          
        # Solo comparar agentes de tipo 'imitador' contra los demás
        imitadores = [a for a in agentes if a.get("tipo_agente") == "imitador"]
        no_imitadores = [a for a in agentes if a.get("tipo_agente") != "imitador"]
        combinaciones = [(imitador, otro) for imitador in imitadores for otro in no_imitadores]
        total = len(combinaciones)
        for offset in range(0, total, bloque_tamano):
            combinaciones_en_bloque = combinaciones[offset:offset + bloque_tamano]
            for agente_a, agente_b in combinaciones_en_bloque:
                similitud_semantica = self.semantic_service.similitud_semantica_agentes(
                    agente_a["id"], agente_b["id"], ventana_dias
                )
                similitud_temas = self._calcular_similitud_temas(
                    agente_a["id"], agente_b["id"], ventana_dias
                )
                score_final = (similitud_semantica * 0.7 + similitud_temas * 0.3)

                if score_final > umbral_similitud:
                    resultado = {
                        "agente_a": agente_a,
                        "agente_b": agente_b,
                        "score_semantico": similitud_semantica,
                        "score_temas": similitud_temas,
                        "score_total": score_final,
                        "fecha_analisis": datetime.now().isoformat(),
                        "posible_imitador": agente_a["id"] if agente_a["id"] > agente_b["id"] else agente_b["id"]
                    }
                    resultados_deteccion.append(resultado)

            self._guardar_resultados_deteccion(resultados_deteccion)
            resultados_deteccion = []
      
    def _calcular_similitud_temas(self, agente_id_a, agente_id_b, ventana_dias):  
        """Calcula similitud basada en temas compartidos"""  
        posts_a = self.semantic_service._obtener_posts_agente(agente_id_a, ventana_dias)  
        posts_b = self.semantic_service._obtener_posts_agente(agente_id_b, ventana_dias)  
          
        if not posts_a or not posts_b:  
            return 0.0  
              
        temas_a = Counter([post["tema"] for post in posts_a if post.get("tema")])  
        temas_b = Counter([post["tema"] for post in posts_b if post.get("tema")])  
          
        if not temas_a or not temas_b:  
            return 0.0  
          
        # Similitud de Jaccard  
        interseccion = sum((temas_a & temas_b).values())  
        union = sum((temas_a | temas_b).values())  
          
        return interseccion / union if union > 0 else 0.0  
      
    def _guardar_resultados_deteccion(self, resultados):  
        """Guarda resultados en base de datos"""  
        with sqlite3.connect(self.db_path) as conn:  
            cursor = conn.cursor()    
              
            # Insertar resultados  
            for resultado in resultados:  
                cursor.execute("""  
                    INSERT INTO deteccion_imitadores   
                    (agente_a_id, agente_b_id, score_semantico, score_temas,   
                     score_total, posible_imitador_id, fecha_analisis)  
                    VALUES (?, ?, ?, ?, ?, ?, ?)  
                """, (  
                    resultado["agente_a"]["id"],  
                    resultado["agente_b"]["id"],  
                    resultado["score_semantico"],  
                    resultado["score_temas"],  
                    resultado["score_total"],  
                    resultado["posible_imitador"],  
                    resultado["fecha_analisis"]  
                ))  
              
            conn.commit()