# routes/imitador_analysis.py  
from flask import Blueprint, render_template, jsonify, request  
from services.imitador_detection_service import ImitadorDetectionService  
from repositories.agente_repo import obtener_todos_los_agentes  
import sqlite3  
import os  
from config import config  
from flask import stream_with_context, Response
from datetime import datetime
from itertools import combinations
import logging

imitador_analysis_bp = Blueprint("imitador_analysis", __name__)  

@imitador_analysis_bp.route('/analisis-imitadores')  
def dashboard_imitadores():  
    """Dashboard principal para análisis de imitadores"""  
    return render_template("imitadores/dashboard.html")  

@imitador_analysis_bp.route('/ejecutar-analisis', methods=['POST'])
def ejecutar_analisis():
    try:
        umbral = float(request.form.get('umbral', 0.75))
        ventana_dias = int(request.form.get('ventana_dias', 180))
        detector = ImitadorDetectionService()
        agentes = obtener_todos_los_agentes()

        # Precargar última fecha de análisis para cada par (ordenando ids para normalizar)
        last_dates = {}
        with sqlite3.connect(detector.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    CASE WHEN agente_a_id < agente_b_id THEN agente_a_id ELSE agente_b_id END AS id1,
                    CASE WHEN agente_a_id < agente_b_id THEN agente_b_id ELSE agente_a_id END AS id2,
                    MAX(fecha_analisis)
                FROM deteccion_imitadores
                GROUP BY id1, id2
            """)
            for row in cursor.fetchall():
                last_dates[(row[0], row[1])] = row[2]


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

                logging.info(
                    f"[EVAL] A:{agente_a['nombre']} B:{agente_b['nombre']} "
                    f"→ Semántico:{similitud_semantica:.3f}, Temas:{similitud_temas:.3f}, Total:{score_final:.3f}"
                )

                if score_final > umbral:
                    tipos = (agente_a["tipo_agente"], agente_b["tipo_agente"])
                    if "imitador" not in tipos:
                        continue

                    if agente_a["tipo_agente"] == "imitador" and agente_b["tipo_agente"] != "imitador":
                        posible_imitador_id = agente_a["id"]
                    elif agente_b["tipo_agente"] == "imitador" and agente_a["tipo_agente"] != "imitador":
                        posible_imitador_id = agente_b["id"]
                    else:
                        # Si ambos son "imitador" o ninguno calificado, por defecto asigna agente_a
                        posible_imitador_id = agente_a["id"]

                    # Verificar duplicado usando in-memory fechas
                    fecha_ultimo_analisis = get_last_date(agente_a["id"], agente_b["id"])
                    if fecha_ultimo_analisis and fecha_mas_reciente <= fecha_ultimo_analisis:
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
                        "posible_imitador": posible_imitador_id
                    })

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
                yield f"Análisis completado. {contador_total} posibles imitadores detectados.\n"

        return Response(stream_with_context(generar_respuesta()), mimetype='text/plain')

    except Exception as e:
        logging.exception("Error en ejecutar_analisis")
        return Response(f"Error: {str(e)}\n", mimetype='text/plain', status=500)

@imitador_analysis_bp.route('/resultados-analisis')  
def obtener_resultados():  
    """Devuelve una tabla HTML con los resultados más recientes del análisis"""  
    try:  
        entorno = os.getenv("FLASK_ENV", "development")  
        db_path = config[entorno].DB_PATH  

        with sqlite3.connect(db_path) as conn:  
            conn.row_factory = sqlite3.Row  
            cursor = conn.cursor()  
            cursor.execute("""  
                SELECT di.*,   
                       a1.nombre as agente_a_nombre,  
                       a2.nombre as agente_b_nombre,  
                       a3.nombre as posible_imitador_nombre  
                FROM deteccion_imitadores di  
                JOIN agentes a1 ON di.agente_a_id = a1.id  
                JOIN agentes a2 ON di.agente_b_id = a2.id  
                JOIN agentes a3 ON di.posible_imitador_id = a3.id  
                WHERE DATE(di.fecha_analisis) = DATE('now')
                ORDER BY di.score_total DESC, di.fecha_analisis DESC  
                LIMIT 50  
            """)  
            resultados = [dict(row) for row in cursor.fetchall()]  

        if not resultados:  
            return "<p>No se encontraron coincidencias en el análisis actual. Se muestran coincidencias históricas.</p>"  

        def safe_round(x, ndigits=3):
            try:
                return round(float(x), ndigits)
            except:
                return "-"

        # Construir tabla HTML  
        tabla = "<table border='1'><thead><tr><th>Agente A</th><th>Agente B</th><th>Posible Imitador</th><th>Score Semántico</th><th>Score Temas</th><th>Score Total</th><th>Fecha</th></tr></thead><tbody>"  
        for r in resultados:  
            fila = f"<tr><td>{r['agente_a_nombre']}</td><td>{r['agente_b_nombre']}</td><td>{r['posible_imitador_nombre']}</td><td>{safe_round(r['score_semantico'])}</td><td>{safe_round(r['score_temas'])}</td><td>{safe_round(r['score_total'])}</td><td>{r['fecha_analisis']}</td></tr>"  
            tabla += fila  
        tabla += "</tbody></table>"  
        return tabla  

    except Exception as e:  
        return f"<p style='color:red;'>Error: {str(e)}</p>"  

@imitador_analysis_bp.route('/metricas-api')  
def metricas_api():  
    """API para métricas del dashboard"""  
    try:  
        entorno = os.getenv("FLASK_ENV", "development")  
        db_path = config[entorno].DB_PATH  
          
        with sqlite3.connect(db_path) as conn:  
            cursor = conn.cursor()  
              
            # Total de detecciones (solo de la fecha actual)
            cursor.execute("SELECT COUNT(*) FROM deteccion_imitadores WHERE DATE(fecha_analisis) = DATE('now')")
            total_detecciones = cursor.fetchone()[0]
              
            # Detecciones por día (últimos 7 días)  
            cursor.execute("""  
                SELECT DATE(fecha_analisis) as fecha, COUNT(*) as cantidad  
                FROM deteccion_imitadores   
                WHERE fecha_analisis >= datetime('now', '-7 days')  
                GROUP BY DATE(fecha_analisis)  
                ORDER BY fecha  
            """)  
            detecciones_por_dia = [{"fecha": row[0], "cantidad": row[1]}   
                                 for row in cursor.fetchall()]  
              
            # Score promedio (solo de la fecha actual)
            cursor.execute("SELECT AVG(score_total) FROM deteccion_imitadores WHERE DATE(fecha_analisis) = DATE('now')")
            score_promedio = cursor.fetchone()[0] or 0
              
        return jsonify({  
            "total_detecciones": total_detecciones,  
            "detecciones_por_dia": detecciones_por_dia,  
            "score_promedio": round(score_promedio, 3),  
            "agentes_analizados": len(obtener_todos_los_agentes())  
        })  
          
    except Exception as e:  
        return jsonify({"error": str(e)}), 500