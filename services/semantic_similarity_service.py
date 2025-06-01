# services/semantic_similarity_service.py  
import sqlite3  
import numpy as np  
from sentence_transformers import SentenceTransformer  
import logging
import pickle
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict  
from datetime import datetime, timedelta  
import os  
from config import config  

# Configuración de logger a nivel de módulo
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(name)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
  
class SemanticSimilarityService:  
    def __init__(self, db_path=None):  
        if db_path is None:  
            entorno = os.getenv("FLASK_ENV", "development")  
            self.db_path = config[entorno].DB_PATH  
        else:  
            self.db_path = db_path  
              
        # Modelo multilingüe optimizado para español  
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')  
        # Asegurar la tabla de embeddings cache
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embeddings_posts (
                    post_id TEXT PRIMARY KEY,
                    embedding BLOB
                )
            """)
            conn.commit()
          
    def obtener_conexion(self):  
        """Reutiliza el patrón de conexión existente del proyecto"""  
        conn = sqlite3.connect(self.db_path, timeout=120)  
        conn.row_factory = sqlite3.Row  
        return conn  

    def _get_cached_embedding(self, post_id):
        """Recupera el embedding almacenado para un post_id, o None si no existe."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT embedding FROM embeddings_posts WHERE post_id = ?", (post_id,))
            row = cursor.fetchone()
        if row:
            return pickle.loads(row[0])
        return None

    def _cache_embedding(self, post_id, embedding):
        """Guarda el embedding serializado para un post_id."""
        blob = pickle.dumps(embedding)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO embeddings_posts (post_id, embedding)
                VALUES (?, ?)
            """, (post_id, blob))
            conn.commit()
      
    def calcular_embeddings_posts(self, posts):
        """Calcula embeddings para una lista de posts, usando cache si está disponible."""
        if not posts:
            return np.array([]), []

        contenidos = []
        ids = []
        for post in posts:
            contenido = post.get("contenido")
            post_id = str(post.get("id", post.get("created_at")))
            if contenido:
                ids.append(post_id)
                contenidos.append(contenido)

        if not contenidos:
            return np.array([]), []

        embeddings = []
        missing_indices = []
        for idx, post_id in enumerate(ids):
            cached = self._get_cached_embedding(post_id)
            if cached is not None:
                embeddings.append(cached)
            else:
                missing_indices.append(idx)
                embeddings.append(None)

        # Calcular embeddings sólo para los contenidos faltantes
        if missing_indices:
            textos_faltantes = [contenidos[i] for i in missing_indices]
            nuevos_embs = self.model.encode(textos_faltantes)
            for j, idx in enumerate(missing_indices):
                embeddings[idx] = nuevos_embs[j]
                self._cache_embedding(ids[idx], nuevos_embs[j])

        return np.vstack(embeddings), ids
      
    def similitud_semantica_agentes(self, agente_id_a, agente_id_b, ventana_dias=30, fecha_inicio_contenido=None):
        posts_a, fecha_a = self._obtener_posts_agente(agente_id_a, ventana_dias, fecha_inicio_contenido)
        posts_b, fecha_b = self._obtener_posts_agente(agente_id_b, ventana_dias, fecha_inicio_contenido)

        logger.debug(f"Obtenidos posts A={len(posts_a)}, B={len(posts_b)}; fechas más recientes A={fecha_a}, B={fecha_b}")

        if not posts_a or not posts_b:
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

        # logger.debug(f"Textos válidos A: {textos_a}")
        # logger.debug(f"Textos válidos B: {textos_b}")

        if not textos_a or not textos_b:
            fecha_mas_reciente = max(filter(None, [fecha_a, fecha_b]), default=None)
            return 0.0, fecha_mas_reciente

        try:
            embeddings_a, ids_a = self.calcular_embeddings_posts(posts_a)
            embeddings_b, ids_b = self.calcular_embeddings_posts(posts_b)
        except Exception as e:
            logger.error(f"Error generando embeddings: {e}")
            fecha_mas_reciente = max(filter(None, [fecha_a, fecha_b]), default=None)
            return 0.0, fecha_mas_reciente

        logger.debug(f"Embeddings A: shape={embeddings_a.shape}, contains NaN? {np.isnan(embeddings_a).any()}")
        logger.debug(f"Embeddings B: shape={embeddings_b.shape}, contains NaN? {np.isnan(embeddings_b).any()}")

        if embeddings_a.size == 0 or embeddings_b.size == 0:
            fecha_mas_reciente = max(filter(None, [fecha_a, fecha_b]), default=None)
            return 0.0, fecha_mas_reciente

        # Cálculo vectorizado de todas las similitudes
        matriz_sim = cosine_similarity(embeddings_a, embeddings_b)
        # Ignorar NaNs
        matriz_sim = np.where(np.isnan(matriz_sim), 0.0, matriz_sim)
        promedio = float(np.mean(matriz_sim))
        fecha_mas_reciente = max(filter(None, [fecha_a, fecha_b]), default=None)
        logger.debug(f"Promedio similitud semántica: {promedio}")
        return (promedio if not np.isnan(promedio) else 0.0), fecha_mas_reciente
      
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
        # Convertir created_at a string ISO si es datetime
        for row in resultados:
            fecha = row.get("created_at")
            # Asumiendo que created_at ya está almacenado en UTC ISO 8601
            # Si fuera datetime, convertir a ISO:
            # if isinstance(fecha, datetime):
            #     row["created_at"] = fecha.astimezone(timezone.utc).isoformat()

        fecha_mas_reciente = resultados[0]["created_at"] if resultados else None
        return resultados, fecha_mas_reciente