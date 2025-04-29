# trends.py

import time
from pytrends.request import TrendReq

pytrends = TrendReq(hl='es-MX', tz=360)

def tendencias_bloque(temas_bloque, geo="MX-DIF"):
    try:
        ranking_total = {}
        # Dividir temas en sublistas de máximo 5
        for i in range(0, len(temas_bloque), 5):
            sub_bloque = temas_bloque[i:i + 5]
            pytrends.build_payload(sub_bloque, geo=geo, timeframe='now 7-d')
            data = pytrends.interest_over_time()
            if data.empty:
                print(f"[INFO] Sin datos para sub-bloque: {sub_bloque}")
                continue

            promedio = data[sub_bloque].mean().to_dict()
            for tema, valor in promedio.items():
                if tema in ranking_total:
                    ranking_total[tema] += valor  # Acumula si aparece en varios bloques
                else:
                    ranking_total[tema] = valor

            time.sleep(2)  # Pausa pequeña para evitar 429

        # Ordenar el ranking total
        ranking = dict(sorted(ranking_total.items(), key=lambda item: item[1], reverse=True))
        print(f"[RANKING FINAL] {ranking}")
        return ranking

    except Exception as e:
        print(f"[ERROR] tendencias_bloque falló: {e}")
        return {}

# precache.py

import sqlite3
from datetime import datetime
from trends import temas_por_tipo

def precachear_tendencias(geo="MX-DIF"):
    for tipo_agente, temas in temas_por_tipo.items():
        try:
            ranking = tendencias_bloque(temas, geo)
            top_temas = list(ranking.keys())[:3]
            ahora = datetime.now()

            with sqlite3.connect("database.db", timeout=60) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                c = conn.cursor()
                for tema in top_temas:
                    c.execute('''
                        INSERT INTO tendencias_cache (tipo_agente, tema, resultado, actualizado_en)
                        VALUES (?, ?, ?, ?)
                    ''', (tipo_agente, tema, tema, ahora.isoformat()))
                conn.commit()
            print(f"[PRECACHE] {tipo_agente}: {top_temas}")
        except Exception as e:
            print(f"[ERROR PRECACHE] {tipo_agente}: {e}")