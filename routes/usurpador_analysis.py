# routes/usurpador_analysis.py  
from flask import Blueprint, render_template, jsonify, request  
from services.usurpador_detection_service import UsurpadorDetectionService  
from repositories.agente_repo import obtener_todos_los_agentes  
import sqlite3  
import os  
from config import config  
from flask import stream_with_context, Response
from datetime import datetime
from itertools import combinations
import logging
from db import get_db_connection

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# (Opcional) Si quieres que se imprima en consola con un formato específico:
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logger.addHandler(handler)

usurpador_analysis_bp = Blueprint("usurpador_analysis", __name__)  

@usurpador_analysis_bp.route('/analisis-usurpadores')  
def dashboard_usurpadores():  
    """Dashboard principal para análisis de usurpadores"""  
    return render_template("usurpadores/dashboard.html")  

@usurpador_analysis_bp.route('/ejecutar-analisis', methods=['POST'])
def ejecutar_analisis():
    try:
        umbral = float(request.form.get('umbral', 0.30))
        ventana_dias = int(request.form.get('ventana_dias', 1))
        detector = UsurpadorDetectionService()
        agentes = obtener_todos_los_agentes()

        # Precargar última fecha de análisis para cada par (ordenando ids para normalizar)
        last_dates = {}
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                CASE WHEN agente_a_id < agente_b_id THEN agente_a_id ELSE agente_b_id END AS id1,
                CASE WHEN agente_a_id < agente_b_id THEN agente_b_id ELSE agente_a_id END AS id2,
                MAX(fecha_analisis)
            FROM deteccion_usurpadores
            GROUP BY id1, id2
        """)
        for row in cursor.fetchall():
            last_dates[(row[0], row[1])] = row[2]

        # Precargar último score para cada par (basado en la fecha más reciente)
        last_scores = {}
        cursor.execute("""
            SELECT 
                CASE WHEN agente_a_id < agente_b_id THEN agente_a_id ELSE agente_b_id END AS id1,
                CASE WHEN agente_a_id < agente_b_id THEN agente_b_id ELSE agente_a_id END AS id2,
                d.score_total
            FROM deteccion_usurpadores d
            JOIN (
                SELECT 
                    CASE WHEN agente_a_id < agente_b_id THEN agente_a_id ELSE agente_b_id END AS id1,
                    CASE WHEN agente_a_id < agente_b_id THEN agente_b_id ELSE agente_a_id END AS id2,
                    MAX(fecha_analisis) AS max_fecha
                FROM deteccion_usurpadores
                GROUP BY id1, id2
            ) x ON (
                ((d.agente_a_id = x.id1 AND d.agente_b_id = x.id2) 
                 OR (d.agente_a_id = x.id2 AND d.agente_b_id = x.id1))
                AND d.fecha_analisis = x.max_fecha
            )
        """)
        for row in cursor.fetchall():
            last_scores[(row[0], row[1])] = row[2]
        conn.close()


        def generar_respuesta():
            yield "Iniciando análisis por bloques...\n"
            bloque_tamano = 5
            contador_total = 0
            def get_last_date(a_id, b_id):
                key = (a_id, b_id) if a_id < b_id else (b_id, a_id)
                return last_dates.get(key)
            combinaciones_iter = combinations(agentes, 2)
            resultados_bloque = []
            bloque_count = 0

            for agente_a, agente_b in combinaciones_iter:
                fecha_inicio = get_last_date(agente_a["id"], agente_b["id"])
                similitud_semantica, fecha_mas_reciente = detector.semantic_service.similitud_semantica_agentes(
                    agente_a["id"], agente_b["id"], ventana_dias, fecha_inicio
                )
                similitud_temas = detector._calcular_similitud_temas(
                    agente_a["id"], agente_b["id"], ventana_dias
                )
                score_final = (similitud_semantica * 0.7 + similitud_temas * 0.3)

                logging.warning(
                    f"[EVAL] A:{agente_a['nombre']} B:{agente_b['nombre']} "
                    f"→ Semántico:{similitud_semantica:.3f}, Temas:{similitud_temas:.3f}, Total:{score_final:.3f}"
                )

                if score_final > umbral:
                    tipos = (agente_a["tipo_agente"], agente_b["tipo_agente"])
                    if "usurpador" not in tipos:
                        continue

                    if agente_a["tipo_agente"] == "usurpador" and agente_b["tipo_agente"] != "usurpador":
                        posible_usurpador_id = agente_a["id"]
                    elif agente_b["tipo_agente"] == "usurpador" and agente_a["tipo_agente"] != "usurpador":
                        posible_usurpador_id = agente_b["id"]
                    else:
                        # Si ambos son "usurpador" o ninguno calificado, por defecto asigna agente_a
                        posible_usurpador_id = agente_a["id"]

                    # Verificar duplicado usando in-memory fechas
                    fecha_ultimo_analisis = get_last_date(agente_a["id"], agente_b["id"])
                    if fecha_ultimo_analisis and fecha_mas_reciente and fecha_mas_reciente <= fecha_ultimo_analisis:
                        continue

                    # Verificar si el score no ha incrementado desde el último análisis
                    key = (agente_a["id"], agente_b["id"]) if agente_a["id"] < agente_b["id"] else (agente_b["id"], agente_a["id"])
                    último_score = last_scores.get(key, 0)
                    if score_final <= último_score:
                        continue

                    # Evitar duplicados en el mismo bloque
                    if any(
                        r["agente_a"]["id"] == agente_a["id"] and
                        r["agente_b"]["id"] == agente_b["id"]
                        for r in resultados_bloque
                    ):
                        continue

                    resultados_bloque.append({
                        "agente_a": agente_a,
                        "agente_b": agente_b,
                        "score_semantico": similitud_semantica,
                        "score_temas": similitud_temas,
                        "score_total": score_final,
                        "fecha_analisis": fecha_mas_reciente,
                        "posible_usurpador": posible_usurpador_id
                    })
                    # Actualizar last_dates para evitar reprocesar este par en el mismo run
                    key = (agente_a["id"], agente_b["id"]) if agente_a["id"] < agente_b["id"] else (agente_b["id"], agente_a["id"])
                    last_dates[key] = fecha_mas_reciente
                    last_scores[key] = score_final

                    bloque_count += 1
                    if bloque_count >= bloque_tamano:
                        detector._guardar_resultados_deteccion(resultados_bloque)
                        contador_total += len(resultados_bloque)
                        resultados_bloque = []
                        yield f"Bloque procesado. Total acumulado: {contador_total}\n"
                        bloque_count = 0

            # Guardar resultados restantes si los hubiera
            if resultados_bloque:
                detector._guardar_resultados_deteccion(resultados_bloque)
                contador_total += len(resultados_bloque)

            if contador_total == 0:
                yield "Análisis completado. No se encontraron coincidencias nuevas.\n"
            else:
                yield f"Análisis completado. {contador_total} posibles usurpadores detectados.\n"

        return Response(stream_with_context(generar_respuesta()), mimetype='text/plain')

    except Exception as e:
        logging.exception("Error en ejecutar_analisis")
        return Response(f"Error: {str(e)}\n", mimetype='text/plain', status=500)

@usurpador_analysis_bp.route('/resultados-analisis')  
def obtener_resultados():  
    """Devuelve una tabla HTML con los resultados más recientes del análisis"""  
    try:  
        entorno = os.getenv("FLASK_ENV", "development")  
        db_path = config[entorno].DB_PATH  

        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT di.*,   
                   a1.nombre as agente_a_nombre,  
                   a2.nombre as agente_b_nombre,  
                   a3.nombre as posible_usurpador_nombre  
            FROM deteccion_usurpadores di  
            JOIN agentes a1 ON di.agente_a_id = a1.id  
            JOIN agentes a2 ON di.agente_b_id = a2.id  
            JOIN agentes a3 ON di.posible_usurpador_id = a3.id  
            WHERE DATE(di.fecha_analisis) = DATE('now')
            ORDER BY di.score_total DESC, di.fecha_analisis DESC  
            LIMIT 50  
        """)
        resultados = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not resultados:  
            return "<p>No se encontraron coincidencias en el análisis actual. Se muestran coincidencias históricas.</p>"  

        def safe_round(x, ndigits=3):
            try:
                return round(float(x), ndigits)
            except:
                return "-"

        # Construir tabla HTML  
        tabla = "<table border='1'><thead><tr><th>Agente A</th><th>Agente B</th><th>Posible Usurpador</th><th>Score Semántico</th><th>Score Temas</th><th>Score Total</th><th>Fecha</th></tr></thead><tbody>"  
        for r in resultados:  
            fila = f"<tr><td>{r['agente_a_nombre']}</td><td>{r['agente_b_nombre']}</td><td>{r['posible_usurpador_nombre']}</td><td>{safe_round(r['score_semantico'])}</td><td>{safe_round(r['score_temas'])}</td><td>{safe_round(r['score_total'])}</td><td>{r['fecha_analisis']}</td></tr>"  
            tabla += fila  
        tabla += "</tbody></table>"  
        return tabla  

    except Exception as e:  
        return f"<p style='color:red;'>Error: {str(e)}</p>"  

@usurpador_analysis_bp.route('/metricas-api')
def metricas_api():
    """API para métricas del dashboard"""
    try:
        logger.debug("Entrando a metricas_api")
        entorno = os.getenv("FLASK_ENV", "development")
        db_path = config[entorno].DB_PATH

        conn = get_db_connection()
        cursor = conn.cursor()

        # 1) Total de detecciones (hoy)
        cursor.execute("""
            SELECT COUNT(*)
            FROM deteccion_usurpadores
            WHERE DATE(fecha_analisis) = DATE('now')
        """)
        fila = cursor.fetchone()
        total_hoy = fila[0] if fila and fila[0] is not None else 0
        logger.debug(f"total_hoy: {total_hoy}")

        # 2) Total de detecciones (ayer)
        cursor.execute("""
            SELECT COUNT(*)
            FROM deteccion_usurpadores
            WHERE DATE(fecha_analisis) = DATE('now', '-1 day')
        """)
        fila = cursor.fetchone()
        total_ayer = fila[0] if fila and fila[0] is not None else 0
        logger.debug(f"total_ayer: {total_ayer}")

        # 3) Variación porcentual de detecciones (hoy vs ayer)
        if total_ayer == 0:
            variacion_pct = 100 if total_hoy > 0 else 0
        else:
            variacion_pct = round((total_hoy - total_ayer) / total_ayer * 100, 2)

        # 4) Detecciones únicas por posible usurpador (últimos 7 días)
        cursor.execute("""
            SELECT posible_usurpador_id, COUNT(*) AS veces
            FROM deteccion_usurpadores
            WHERE fecha_analisis >= datetime('now', '-7 days')
            GROUP BY posible_usurpador_id
            ORDER BY veces DESC
            LIMIT 5
        """)
        top_sospechosos = []
        for fila in cursor.fetchall() or []:
            agente_id = fila[0]
            veces = fila[1]
            cursor.execute("SELECT nombre FROM agentes WHERE id = ?", (agente_id,))
            nombre_row = cursor.fetchone()
            nombre = nombre_row[0] if nombre_row else "Desconocido"
            top_sospechosos.append({
                "agente_id": agente_id,
                "nombre": nombre,
                "veces_detectado": veces
            })
        logger.debug(f"top_sospechosos: {top_sospechosos}")

        # 5) Score promedio, máximo y mínimo (hoy)
        cursor.execute("""
            SELECT 
              ROUND(AVG(score_total), 3) AS avg_score,
              ROUND(MAX(score_total), 3) AS max_score,
              ROUND(MIN(score_total), 3) AS min_score
            FROM deteccion_usurpadores
            WHERE DATE(fecha_analisis) = DATE('now')
        """)
        avg_max_min = cursor.fetchone() or (0, 0, 0)
        avg_score_hoy, max_score_hoy, min_score_hoy = avg_max_min

        # 6) Detecciones repetidas vs nuevas (hoy)
        cursor.execute("""
            SELECT COUNT(*)
            FROM deteccion_usurpadores d
            WHERE DATE(d.fecha_analisis) = DATE('now')
              AND EXISTS (
                SELECT 1 
                FROM deteccion_usurpadores d2
                WHERE (
                  (d.agente_a_id = d2.agente_a_id AND d.agente_b_id = d2.agente_b_id)
                  OR (d.agente_a_id = d2.agente_b_id AND d.agente_b_id = d2.agente_a_id)
                )
                AND DATE(d2.fecha_analisis) < DATE('now')
              )
        """)
        fila = cursor.fetchone()
        conteo_repetidas = fila[0] if fila and fila[0] is not None else 0
        logger.debug(f"conteo_repetidas: {conteo_repetidas}")
        conteo_nuevas = total_hoy - conteo_repetidas
        pct_nuevas = round((conteo_nuevas / total_hoy) * 100, 2) if total_hoy > 0 else 0

        # 7) Pares analizados vs pares detectados (hoy)
        cursor.execute("SELECT COUNT(*) FROM agentes")
        fila = cursor.fetchone()
        n_agentes = fila[0] if fila and fila[0] is not None else 0
        logger.debug(f"n_agentes: {n_agentes}")
        pares_totales = n_agentes * (n_agentes - 1) / 2
        if pares_totales > 0:
            pct_pares_detectados = round((total_hoy / pares_totales) * 100, 2)
        else:
            pct_pares_detectados = 0

        # 8) Distribución de detecciones por tipo de agente (hoy)
        cursor.execute("""
            SELECT 
              a1.tipo_agente AS tipo_a, 
              a2.tipo_agente AS tipo_b, 
              COUNT(*) AS cantidad
            FROM deteccion_usurpadores d
            JOIN agentes a1 ON d.agente_a_id = a1.id
            JOIN agentes a2 ON d.agente_b_id = a2.id
            WHERE DATE(d.fecha_analisis) = DATE('now')
            GROUP BY a1.tipo_agente, a2.tipo_agente
        """)
        distribucion_tipos = []
        for fila in cursor.fetchall() or []:
            distribucion_tipos.append({
                "tipo_a": fila[0],
                "tipo_b": fila[1],
                "cantidad": fila[2]
            })
        logger.debug(f"distribucion_tipos: {distribucion_tipos}")

        # 9) Agentes “más críticos” (hoy)
        cursor.execute("""
            SELECT agente_id, SUM(veces) AS total_veces 
            FROM (
              SELECT d.agente_a_id AS agente_id, COUNT(*) AS veces
              FROM deteccion_usurpadores d
              WHERE DATE(d.fecha_analisis) = DATE('now')
              GROUP BY d.agente_a_id
              UNION ALL
              SELECT d.agente_b_id AS agente_id, COUNT(*) AS veces
              FROM deteccion_usurpadores d
              WHERE DATE(d.fecha_analisis) = DATE('now')
              GROUP BY d.agente_b_id
            )
            GROUP BY agente_id
            ORDER BY total_veces DESC
            LIMIT 5
        """)
        top_criticos = []
        for fila in cursor.fetchall() or []:
            agente_id = fila[0]
            cnt = fila[1]
            cursor.execute("SELECT nombre FROM agentes WHERE id = ?", (agente_id,))
            nombre_row = cursor.fetchone()
            nombre = nombre_row[0] if nombre_row else "Desconocido"
            top_criticos.append({
                "agente_id": agente_id,
                "nombre": nombre,
                "apariciones": cnt
            })
        logger.debug(f"top_criticos: {top_criticos}")

        # 10) Detecciones por día (últimos 7 días)
        cursor.execute("""
            SELECT DATE(fecha_analisis) as fecha, COUNT(*) as cantidad
            FROM deteccion_usurpadores
            WHERE fecha_analisis >= datetime('now', '-7 days')
            GROUP BY DATE(fecha_analisis)
            ORDER BY fecha
        """)
        detecciones_por_dia = [
            {"fecha": row[0], "cantidad": row[1]}
            for row in (cursor.fetchall() or [])
        ]
        logger.debug(f"detecciones_por_dia: {detecciones_por_dia}")

        # 11) Agentes analizados (total de agentes en DB)
        agentes_list = obtener_todos_los_agentes() or []
        agentes_analizados = len(agentes_list)
        conn.close()

        return jsonify({
            "total_hoy": total_hoy,
            "total_ayer": total_ayer,
            "variacion_pct": variacion_pct,
            "top_sospechosos": top_sospechosos,
            "avg_score_hoy": avg_score_hoy or 0,
            "max_score_hoy": max_score_hoy or 0,
            "min_score_hoy": min_score_hoy or 0,
            "conteo_repetidas": conteo_repetidas,
            "conteo_nuevas": conteo_nuevas,
            "pct_nuevas": pct_nuevas,
            "pares_totales": pares_totales,
            "pct_pares_detectados": pct_pares_detectados,
            "distribucion_tipos": distribucion_tipos,
            "top_criticos": top_criticos,
            "detecciones_por_dia": detecciones_por_dia,
            "agentes_analizados": agentes_analizados
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@usurpador_analysis_bp.route('/metricas-por-hora')
def metricas_por_hora():
    """API para promedio de score total por hora en las últimas 24 horas"""
    try:
        entorno = os.getenv("FLASK_ENV", "development")
        db_path = config[entorno].DB_PATH

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                strftime('%Y-%m-%dT%H:00:00', fecha_analisis) AS hora,
                ROUND(AVG(score_total), 3) AS promedio_score
            FROM deteccion_usurpadores
            WHERE fecha_analisis >= datetime('now', '-1 day')
            GROUP BY hora
            ORDER BY hora
        """)
        resultados_hora = [
            {"hora": row[0], "promedio_score": row[1]}
            for row in (cursor.fetchall() or [])
        ]
        conn.close()
        return jsonify(resultados_hora)
    except Exception as e:
        logger.exception("Error en metricas_por_hora")
        return jsonify({"error": str(e)}), 500

# --- NUEVO ENDPOINT: /metricas-por-5min ---
@usurpador_analysis_bp.route('/metricas-por-5min')
def metricas_por_5min():
    """API para conteo de detecciones cada 5 minutos en las últimas 4 horas"""
    try:
        entorno = os.getenv("FLASK_ENV", "development")
        db_path = config[entorno].DB_PATH

        conn = get_db_connection()
        cursor = conn.cursor()
        # Generar conteo por intervalos de 5 minutos en las últimas 4 horas
        cursor.execute("""
            SELECT 
                strftime('%Y-%m-%dT%H:%M:00', datetime((strftime('%s', fecha_analisis) / 300) * 300, 'unixepoch')) AS intervalo,
                COUNT(*) AS cantidad
            FROM deteccion_usurpadores
            WHERE fecha_analisis >= datetime('now', '-4 hours')
            GROUP BY intervalo
            ORDER BY intervalo
        """)
        resultados = [
            {"intervalo": row[0], "cantidad": row[1]}
            for row in cursor.fetchall() or []
        ]
        conn.close()
        return jsonify(resultados)
    except Exception as e:
        logger.exception("Error en metricas_por_hora")
        return jsonify({"error": str(e)}), 500