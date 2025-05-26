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
      
    def similitud_semantica_agentes(self, agente_id_a, agente_id_b, ventana_dias=30):  
        """Calcula similitud semántica entre dos agentes"""  
        posts_a = self._obtener_posts_agente(agente_id_a, ventana_dias)  
        posts_b = self._obtener_posts_agente(agente_id_b, ventana_dias)  
          
        if not posts_a or not posts_b:  
            return 0.0  
              
        embeddings_a = self.calcular_embeddings_posts(posts_a)  
        embeddings_b = self.calcular_embeddings_posts(posts_b)  
          
        if embeddings_a.size == 0 or embeddings_b.size == 0:  
            return 0.0  
              
        # Calcular similitud promedio entre todos los pares  
        similarities = []  
        for emb_a in embeddings_a:  
            for emb_b in embeddings_b:  
                sim = cosine_similarity([emb_a], [emb_b])[0][0]  
                if isinstance(sim, (int, float)) and not np.isnan(sim):
                    similarities.append(sim)

        if not similarities:
            return 0.0

        promedio = np.mean(similarities)
        return float(promedio) if not np.isnan(promedio) else 0.0  
      
    def _obtener_posts_agente(self, agente_id, ventana_dias):  
        """Obtiene posts recientes de un agente específico"""  
        fecha_limite = (datetime.now() - timedelta(days=ventana_dias)).isoformat()  
          
        with self.obtener_conexion() as conn:  
            cursor = conn.cursor()  
            cursor.execute("""  
                SELECT contenido, tema, created_at   
                FROM posts   
                WHERE agente_id = ? AND created_at > ?  
                ORDER BY created_at DESC  
            """, (agente_id, fecha_limite))  
              
            return [dict(row) for row in cursor.fetchall()]