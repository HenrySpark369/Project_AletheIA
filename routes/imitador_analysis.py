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

imitador_analysis_bp = Blueprint("imitador_analysis", __name__)  

@imitador_analysis_bp.route('/analisis-imitadores')  
def dashboard_imitadores():  
    """Dashboard principal para análisis de imitadores"""  
    return render_template("imitadores/dashboard.html")  

@imitador_analysis_bp.route('/ejecutar-analisis', methods=['POST'])
def ejecutar_analisis():
    """Ejecuta el análisis de detección de imitadores en bloques con stream"""
    try:
        umbral = float(request.form.get('umbral', 0.75))
        ventana_dias = int(request.form.get('ventana_dias', 180))
        detector = ImitadorDetectionService()

        def generar_respuesta():
            yield "Iniciando análisis por bloques...\n"
            agentes = obtener_todos_los_agentes()
            agentes_normales = [a for a in agentes if a.get("tipo_agente") != "imitador"]
            combinaciones = list(combinations(agentes_normales, 2))
            bloque_tamano = 5
            total = len(combinaciones)
            contador_total = 0

            for offset in range(0, total, bloque_tamano):
                combinaciones_en_bloque = combinaciones[offset:offset + bloque_tamano]
                resultados = []

                for agente_a, agente_b in combinaciones_en_bloque:
                    similitud_semantica = detector.semantic_service.similitud_semantica_agentes(
                        agente_a["id"], agente_b["id"], ventana_dias
                    )
                    similitud_temas = detector._calcular_similitud_temas(
                        agente_a["id"], agente_b["id"], ventana_dias
                    )
                    score_final = (similitud_semantica * 0.7 + similitud_temas * 0.3)

                    print(f"[EVAL] A:{agente_a['nombre']} B:{agente_b['nombre']} → Semántico:{similitud_semantica:.3f}, Temas:{similitud_temas:.3f}, Total:{score_final:.3f}")

                    if score_final > umbral:
                        # Verificar si ya existe el par con fecha actual
                        with sqlite3.connect(detector.db_path) as conn:
                            cursor = conn.cursor()
                            posible_imitador_id = agente_b["id"] if agente_b["tipo_agente"] == "imitador" else agente_a["id"]

                            cursor.execute("""
                                SELECT COUNT(*) FROM deteccion_imitadores
                                WHERE DATE(fecha_analisis) = DATE('now')
                                AND (
                                    (agente_a_id = ? AND agente_b_id = ? AND posible_imitador_id = ?)
                                    OR
                                    (agente_a_id = ? AND agente_b_id = ? AND posible_imitador_id = ?)
                                    OR
                                    (agente_a_id = ? AND agente_b_id = ?)
                                    OR
                                    (agente_a_id = ? AND agente_b_id = ?)
                                )
                            """, (
                                agente_a["id"], agente_b["id"], posible_imitador_id,
                                agente_b["id"], agente_a["id"], posible_imitador_id,
                                agente_a["id"], agente_b["id"],
                                agente_b["id"], agente_a["id"]
                            ))
                            resultado_existente = cursor.fetchone()[0]
                            if resultado_existente > 0:
                                continue

                        if any(r["agente_a"]["id"] == agente_a["id"] and r["agente_b"]["id"] == agente_b["id"] and r["score_total"] == score_final for r in resultados):
                            continue

                        resultado = {
                            "agente_a": agente_a,
                            "agente_b": agente_b,
                            "score_semantico": similitud_semantica,
                            "score_temas": similitud_temas,
                            "score_total": score_final,
                            "fecha_analisis": datetime.now().isoformat(),
                            "posible_imitador": posible_imitador_id
                        }
                        resultados.append(resultado)

                detector._guardar_resultados_deteccion(resultados)
                contador_total += len(resultados)
                yield f"Bloque {offset//bloque_tamano + 1} procesado. Total acumulado: {contador_total}\n"

            if contador_total == 0:
                yield "Análisis completado. No se encontraron coincidencias nuevas.\n"
            else:
                yield f"Análisis completado. {contador_total} posibles imitadores detectados.\n"

        return Response(stream_with_context(generar_respuesta()), mimetype='text/plain')

    except Exception as e:
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