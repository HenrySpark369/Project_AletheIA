# tendencias_service.py
import random
import os
from config import config
from db import get_db_connection
entorno = os.getenv("FLASK_ENV", "development")
DB_PATH = config[entorno].DB_PATH

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
    "usurpador": [
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
            conn = get_db_connection()
            c = conn.cursor()
            ahora = datetime.now()
            limite = ahora - timedelta(hours=ttl_horas)

            # Consultar temas en caché, ordenados por ultimo_valor (más relevantes primero)
            c.execute('''
                SELECT resultado, promedio, ultimo_valor FROM tendencias_cache
                WHERE tipo_agente = ? AND actualizado_en > ?
                ORDER BY ultimo_valor DESC, promedio DESC, actualizado_en DESC
                LIMIT ?
            ''', (tipo_agente, limite.isoformat(), max_cache_temas))
            rows = c.fetchall()

            if rows:
                tema_elegido, promedio, ultimo_valor = rows[0]
                promedio = float(promedio) if promedio is not None else None
                ultimo_valor = float(ultimo_valor) if ultimo_valor is not None else None
                print(f"[CACHE] Usando TOP tema en caché para {tipo_agente}: {tema_elegido} (Prom={promedio}, Último={ultimo_valor})")
                conn.close()
                return tema_elegido, promedio, ultimo_valor

            # Si no hay temas recientes, obtener nuevo
            top_tema = tendencias(tipo_agente, geo)
            if not top_tema:
                top_tema = obtener_tema(tipo_agente)

            if isinstance(top_tema, tuple) and len(top_tema) == 3:
                tema, promedio, ultimo_valor = top_tema
                guardar_tema_en_cache(tipo_agente, tema, promedio=promedio, ultimo_valor=ultimo_valor)
            else:
                guardar_tema_en_cache(tipo_agente, top_tema)
            print(f"[CACHE] Tema guardado para {tipo_agente}: {top_tema}")
            conn.close()
            return top_tema, None, None

        except sqlite3.OperationalError as e:
            if "locked" in str(e):
                print(f"[RETRY {attempt+1}] Base de datos bloqueada, esperando...")
                time.sleep(2)
                continue
            else:
                raise e
    raise Exception("Base de datos bloqueada tras varios intentos.")

def TrendReqSeguro(*args, **kwargs):
    from pytrends.request import TrendReq
    from urllib3.util.retry import Retry
    from requests.adapters import HTTPAdapter
    import requests

    retry_strategy = Retry(
        total=kwargs.pop('retries', 3),
        backoff_factor=kwargs.pop('backoff_factor', 0.3),
        allowed_methods=frozenset(['GET', 'POST'])
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    headers = kwargs.pop("requests_args", {}).get("headers", {'User-Agent': 'Mozilla/5.0'})

    pytrends = TrendReq(
        *args,
        requests_args={"headers": headers},
        **kwargs
    )
    pytrends.session = session  # Asigna la sesión directamente
    return pytrends

from pytrends.request import TrendReq
import sqlite3
from datetime import datetime, timedelta
import time

def obtener_tendencias(tema, geo="MX-DIF", usar_cache=True, ttl_horas=1):
    if usar_cache:
        ahora = datetime.now()
        limite = ahora - timedelta(hours=ttl_horas)
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT promedio, ultimo_valor FROM tendencias_cache
            WHERE tema = ? AND actualizado_en > ?
            ORDER BY actualizado_en DESC LIMIT 1
        ''', (tema, limite.isoformat()))
        row = c.fetchone()
        conn.close()
        if row:
            promedio, ultimo_valor = row
            print(f"[CACHE] Tema encontrado en cache: {tema} (Prom={promedio}, Último={ultimo_valor})")
            return tema, float(promedio), float(ultimo_valor)

    # Si no está en caché o no se desea usar
    pytrends = TrendReqSeguro(
        hl='es-MX',
        tz=360,
        timeout=(5, 10),
        retries=3,
        backoff_factor=0.3,
        requests_args={'headers': {'User-Agent': 'Mozilla/5.0'}}
    )

    try:
        pytrends.build_payload([tema], cat=0, timeframe='now 7-d', geo=geo, gprop='')
        df = pytrends.interest_over_time()

        if not df.empty and tema in df.columns:
            promedio = float(df[tema].mean())
            ultimo_valor = float(df[tema].iloc[-1])

            # Guardar en caché
            guardar_tema_en_cache("general", tema, promedio, ultimo_valor)

            print(f"[PYTRENDS] Tema consultado: {tema} (Prom={promedio}, Último={ultimo_valor})")
            return tema, promedio, ultimo_valor

        else:
            print(f"[WARN] Sin datos relevantes para: {tema}")
            return None

    except Exception as e:
        print(f"[ERROR] en obtener_tendencias({tema}): {e}")
        return None

import requests
import json

from pytrends.request import TrendReq
import time

import traceback

def consultar_bloque(pytrends, bloque, geo, max_retries=3):
    for intento in range(max_retries):
        try:
            pytrends.build_payload(bloque, cat=0, timeframe='now 7-d', geo=geo, gprop='')
            interes_tiempo = pytrends.interest_over_time()
            if interes_tiempo.empty:
                raise Exception(f"Respuesta vacía para bloque {bloque}")
            return interes_tiempo
        except Exception as e:
            espera = 10 * (intento + 1)
            print(f"[RETRY {intento+1}] Esperando {espera} segundos por: {e}")
            time.sleep(espera)
    print(f"[ERROR] Fallo definitivo al consultar bloque {bloque} después de {max_retries} intentos.")
    traceback.print_exc()
    return None

def guardar_tema_en_cache(tipo_agente, tema, promedio=None, ultimo_valor=None):
    if promedio is None or ultimo_valor is None:
        print(f"[CACHE] No se guarda tema por datos incompletos: {tema} (Prom={promedio}, Último={ultimo_valor})")
        return  # Salir sin guardar

    try:
        ahora = datetime.now().isoformat()
        promedio = float(promedio)
        ultimo_valor = float(ultimo_valor)

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO tendencias_cache 
            (tipo_agente, tema, resultado, actualizado_en, promedio, ultimo_valor)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            tipo_agente,
            tema,
            tema,  # Si se necesita, se puede hacer JSON aquí
            ahora,
            promedio,
            ultimo_valor
        ))
        conn.commit()
        conn.close()
        print(f"[CACHE] Tema guardado: {tema} (Prom={promedio}, Último={ultimo_valor})")
    except sqlite3.Error as e:
        print(f"[ERROR] No se pudo guardar el tema en cache: {e}")

def tendencias(tipo_agente=None, geo="MX", max_bloques=5):
    pytrends = TrendReqSeguro(
        hl='es-MX',
        tz=360,
        timeout=(5, 10),
        retries=3,
        backoff_factor=0.3,
        requests_args={'headers': {'User-Agent': 'Mozilla/5.0'}}
    )
    ranking = {}

    temas_tipo = temas_por_tipo.get(tipo_agente, [])
    lista_temas = list(set(temas_comunes + temas_tipo))  # Sin duplicados
    random.shuffle(lista_temas)

    bloques_procesados = 0
    for i in range(0, len(lista_temas), 5):
        if bloques_procesados >= max_bloques:
            break

        bloque = lista_temas[i:i+5]
        interes_tiempo = consultar_bloque(pytrends, bloque, geo)

        if interes_tiempo is None:
            continue

        for tema in bloque:
            if tema in interes_tiempo and not interes_tiempo[tema].empty:
                promedio = float(interes_tiempo[tema].mean())
                ultimo_valor = float(interes_tiempo[tema].iloc[-1])
                ranking[tema] = {
                    "promedio": promedio,
                    "ultimo_valor": ultimo_valor
                }
                # Guardar en cache SQLite
                guardar_tema_en_cache(tipo_agente, tema, promedio=promedio, ultimo_valor=ultimo_valor)

        bloques_procesados += 1
        time.sleep(60)  # pausa para evitar bloqueo

    if ranking:
        ranking_ordenado = sorted(ranking.items(), key=lambda x: x[1]["promedio"], reverse=True)
        top_tema, datos = ranking_ordenado[0]
        print(f"[TOP] Tema más relevante: {top_tema} (Promedio={datos['promedio']:.2f}, Último valor={datos['ultimo_valor']})")
        return top_tema, datos['promedio'], datos['ultimo_valor']
    else:
        print("[FALLBACK] No se obtuvieron datos relevantes. Usando tema aleatorio.")
        return obtener_tema(tipo_agente)