# services/semantic_similarity_service.py  
import sqlite3  
import numpy as np  
from sentence_transformers import SentenceTransformer  
from sklearn.metrics.pairwise import cosine_similarity  
from collections import defaultdict  
from datetime import datetime, timedelta  
import os  
from config import config  
  
class SemanticSimilarityService:  
    def __init__(self, db_path=None):  
        if db_path is None:  
            entorno = os.getenv("FLASK_ENV", "development")  
            self.db_path = config[entorno].DB_PATH  
        else:  
            self.db_path = db_path  
              
        # Modelo multilingüe optimizado para español  
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')  
          
    def obtener_conexion(self):  
        """Reutiliza el patrón de conexión existente del proyecto"""  
        conn = sqlite3.connect(self.db_path, timeout=120)  
        conn.row_factory = sqlite3.Row  
        return conn  
      
    def calcular_embeddings_posts(self, posts):  
        """Calcula embeddings para una lista de posts"""  
        if not posts:  
            return np.array([])  
              
        contenidos = [post["contenido"] for post in posts if post.get("contenido")]  
        if not contenidos:  
            return np.array([])  
              
        return self.model.encode(contenidos)  
      
    def similitud_semantica_agentes(self, agente_id_a, agente_id_b, ventana_dias=30, fecha_inicio_contenido=None):
        posts_a, fecha_a = self._obtener_posts_agente(agente_id_a, ventana_dias, fecha_inicio_contenido)
        posts_b, fecha_b = self._obtener_posts_agente(agente_id_b, ventana_dias, fecha_inicio_contenido)

        if not posts_a or not posts_b:
            # print(f"⚠️ Sin posts: A={len(posts_a)}, B={len(posts_b)}")
            fecha_mas_reciente = max(filter(None, [fecha_a, fecha_b]), default=None)
            return 0.0, fecha_mas_reciente

        # Filtramos textos útiles
        textos_a = [
            p["contenido"] for p in posts_a
            if isinstance(p, dict) and p.get("contenido") and "[Error generando post]" not in p["contenido"]
        ]
        textos_b = [
            p["contenido"] for p in posts_b
            if isinstance(p, dict) and p.get("contenido") and "[Error generando post]" not in p["contenido"]
        ]

        if not textos_a or not textos_b:
            # print(f"⚠️ Sin textos válidos: A={len(textos_a)}, B={len(textos_b)}")
            fecha_mas_reciente = max(filter(None, [fecha_a, fecha_b]), default=None)
            return 0.0, fecha_mas_reciente

        try:
            embeddings_a = self.model.encode(textos_a)
            embeddings_b = self.model.encode(textos_b)
        except Exception as e:
            print(f"❌ Error generando embeddings: {e}")
            fecha_mas_reciente = max(filter(None, [fecha_a, fecha_b]), default=None)
            return 0.0, fecha_mas_reciente

        if embeddings_a.size == 0 or embeddings_b.size == 0:
            # print(f"⚠️ Embeddings vacíos: A={embeddings_a.shape}, B={embeddings_b.shape}")
            fecha_mas_reciente = max(filter(None, [fecha_a, fecha_b]), default=None)
            return 0.0, fecha_mas_reciente

        similarities = []
        for emb_a in embeddings_a:
            sim = cosine_similarity([emb_a], embeddings_b).flatten()
            valid_sims = sim[~np.isnan(sim)]
            similarities.extend(valid_sims.tolist())

        if not similarities:
            # print("⚠️ No se encontraron similitudes válidas.")
            fecha_mas_reciente = max(filter(None, [fecha_a, fecha_b]), default=None)
            return 0.0, fecha_mas_reciente

        promedio = np.mean(similarities)
        fecha_mas_reciente = max(filter(None, [fecha_a, fecha_b]), default=None)
        return float(promedio) if not np.isnan(promedio) else 0.0, fecha_mas_reciente
      
    def _obtener_posts_agente(self, agente_id, ventana_dias, fecha_inicio=None):  
        """Obtiene posts recientes del agente y devuelve la fecha más reciente."""
        fecha_limite = (datetime.now() - timedelta(days=ventana_dias)).isoformat()
        fecha_corte = max(fecha_inicio, fecha_limite) if fecha_inicio else fecha_limite

        query = """  
            SELECT contenido, tema, created_at   
            FROM posts   
            WHERE agente_id = ? AND created_at > ?
            ORDER BY created_at DESC
        """
        params = [agente_id, fecha_corte]

        with self.obtener_conexion() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            resultados = [dict(row) for row in rows]

        fecha_mas_reciente = resultados[0]["created_at"] if resultados else None
        return resultados, fecha_mas_reciente