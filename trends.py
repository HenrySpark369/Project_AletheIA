# temas.py
import random

temas_comunes = [
    "tecnología", "crisis política", "tendencias", "moda", "deportes",
    "redes sociales", "cultura pop", "educación", "opinión pública",
    "cambio climático", "influencers en redes sociales", "inteligencia artificial",
    "salud mental", "economía en México", "noticias deportivas",
    "tendencias de moda", "desigualdad social", "educación pública",
    "uso de criptomonedas", "memes virales", "feminismo",
    "censura en redes", "emprendimiento digital", "rumores de celebridades"
]

temas_por_tipo = {
    "troll": [
        "rumores de celebridades", "memes virales", "censura en redes",
        "teorías conspirativas", "polémicas en redes", "cancelaciones públicas",
        "provocaciones políticas", "fanatismos", "ataques a influencers",
        "divisiones sociales", "trolleo mediático", "noticias falsas",
        "comentarios sarcásticos", "odio digital"
    ],
    "imitador": [
        "influencers en redes sociales", "giveaways", "tendencias de TikTok",
        "moda viral", "estilo de vida en Instagram", "reviews de gadgets",
        "viajes soñados", "videos de maquillaje", "estética minimalista",
        "fitness digital", "frases motivacionales", "hashtags populares",
        "poses virales", "contenidos aspiracionales"
    ],
    "normal": [
        "salud mental", "educación pública", "cambio climático", "igualdad de género",
        "desigualdad social", "movimientos sociales", "economía en México",
        "uso de criptomonedas", "emprendimiento digital", "noticias internacionales",
        "elecciones", "violencia de género", "trabajo remoto", "vacunación",
        "salud preventiva", "programas gubernamentales"
    ],
    "observador": [
        "fotografía", "arte urbano", "diseño gráfico", "viajes culturales",
        "recomendaciones de libros", "películas de autor", "documentales sociales",
        "estilo de vida alternativo", "gastronomía", "reflexiones personales",
        "cambios en el consumo", "eventos culturales", "espacios públicos",
        "arquitectura", "moda sustentable", "hobbies creativos"
    ]
}

def obtener_tema(tipo_agente=None):
    if tipo_agente in temas_por_tipo:
        return random.choice(temas_por_tipo[tipo_agente])
    return random.choice(temas_comunes)

def obtener_temas_distintos(tipo_agente=None, cantidad=3):
    if tipo_agente in temas_por_tipo:
        base = temas_por_tipo[tipo_agente]
    else:
        base = temas_comunes
    return random.sample(base, min(cantidad, len(base)))

def obtener_tema_en_tendencia(tipo_agente=None, geo="MX-DIF"):
    base = obtener_tema(tipo_agente)  # Usa tu lógica actual como base
    resultados = tendencias(base, geo)

    ranked = resultados.get("busquedas_relacionadas", {}).get("ranked_list", [])
    if ranked and "query" in ranked[0]:
        queries = ranked[0]["query"]
        if queries:
            return queries[0]["query"]  # Top 1 búsqueda relacionada

    return base  # Fallback si no hay datos

import sqlite3
from datetime import datetime, timedelta
import time

def obtener_tema_en_tendencia_desde_cache(tipo_agente, geo="MX-DIF", ttl_horas=1, max_cache_temas=5):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with sqlite3.connect("database.db", timeout=60) as conn:
                c = conn.cursor()
                ahora = datetime.now()
                limite = ahora - timedelta(hours=ttl_horas)

                # Consultar varios temas recientes en caché
                c.execute('''
                    SELECT resultado FROM tendencias_cache
                    WHERE tipo_agente = ? AND actualizado_en > ?
                    ORDER BY actualizado_en DESC LIMIT ?
                ''', (tipo_agente, limite.isoformat(), max_cache_temas))
                rows = c.fetchall()

                if rows:
                    temas_disponibles = [row[0] for row in rows]
                    tema_elegido = random.choice(temas_disponibles)
                    print(f"[CACHE] Usando tema en caché para {tipo_agente}: {tema_elegido}")
                    return tema_elegido

                # No hay temas en caché, buscar uno nuevo
                top_tema = tendencias(tipo_agente, geo)
                if not top_tema:
                    top_tema = obtener_tema(tipo_agente)

                # Guardar en caché el nuevo tema
                c.execute('''
                    INSERT INTO tendencias_cache (tipo_agente, tema, resultado, actualizado_en)
                    VALUES (?, ?, ?, ?)
                ''', (tipo_agente, top_tema, top_tema, ahora.isoformat()))
                conn.commit()

                print(f"[CACHE] Tema guardado para {tipo_agente}: {top_tema}")
                return top_tema

        except sqlite3.OperationalError as e:
            if "locked" in str(e):
                print(f"[RETRY {attempt+1}] Base de datos bloqueada, esperando...")
                time.sleep(2)
                continue
            else:
                raise e
    raise Exception("Base de datos bloqueada tras varios intentos.")

# Serpapi y google trends


from serpapi import GoogleSearch
import os

API_KEY = os.getenv("SERPAPI_KEY")  # Usa una variable de entorno por seguridad

def obtener_tendencias(tema, geo="MX-DIF"):
    if not API_KEY:
        print("[ERROR] SERPAPI_KEY no configurada.")
        return {}  # Retorna vacío si no hay clave

    try:
        params = {
            "engine": "google_trends",
            "q": tema,
            "geo": geo,
            "api_key": API_KEY
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        return {
            "interes_tiempo": results.get("interest_over_time", {}),
            "por_region": results.get("interest_by_region", {}),
            "temas_relacionados": results.get("related_topics", {}),
            "busquedas_relacionadas": results.get("related_queries", {})
        }
    except Exception as e:
        print(f"[ERROR en obtener_tendencias]: {e}")
        return {}  # ← fallback si SerpAPI truena o no hay conexión

import requests
import json

from pytrends.request import TrendReq
import time

def consultar_bloque(pytrends, bloque, geo, max_retries=3):
    for intento in range(max_retries):
        try:
            pytrends.build_payload(bloque, cat=0, timeframe='now 7-d', geo=geo, gprop='')
            interes_tiempo = pytrends.interest_over_time()
            if interes_tiempo.empty:
                raise Exception("Respuesta vacía")
            return interes_tiempo
        except Exception as e:
            if "429" in str(e) or "Rate limit" in str(e) or "timed out" in str(e) or "vacía" in str(e):
                espera = 10 * (intento + 1)
                print(f"[RETRY {intento+1}] Esperando {espera} segundos por límite o error temporal...")
                time.sleep(espera)
            else:
                print(f"[ERROR] Error inesperado al consultar bloque {bloque}: {e}")
                break
    print(f"[ERROR] Fallo definitivo al consultar bloque {bloque} después de {max_retries} intentos.")
    return None

def tendencias(tipo_agente=None, geo="MX"):
    pytrends = TrendReq(
        hl='es-MX',
        tz=360,
        retries=3,
        backoff_factor=0.3,
        requests_args={'headers': {'User-Agent': 'Mozilla/5.0'}}
    )
    ranking = {}
    
    # Combina temas comunes y los del tipo de agente
    temas_tipo = temas_por_tipo.get(tipo_agente, [])
    lista_temas = list(set(temas_comunes + temas_tipo))  # Sin duplicados

    for i in range(0, len(lista_temas), 5):
        bloque = lista_temas[i:i+5]
        interes_tiempo = consultar_bloque(pytrends, bloque, geo)

        if interes_tiempo is None:
            continue

        for tema in bloque:
            if tema in interes_tiempo:
                promedio = interes_tiempo[tema].mean()
                ultimo_valor = interes_tiempo[tema].iloc[-1]
                ranking[tema] = {
                    "promedio": promedio,
                    "ultimo_valor": ultimo_valor
                }
        time.sleep(5)  # Pausa general entre bloques exitosos.

    if ranking:
        ranking_ordenado = sorted(ranking.items(), key=lambda x: x[1]["promedio"], reverse=True)
        top_tema, datos = ranking_ordenado[0]
        print(f"[TOP] Tema más relevante: {top_tema} (Promedio={datos['promedio']:.2f}, Último valor={datos['ultimo_valor']})")
        return top_tema
    else:
        print("[INFO] No se obtuvieron datos relevantes. Usando tema de respaldo.")
        return obtener_tema(tipo_agente)  # Fallback si todo falla