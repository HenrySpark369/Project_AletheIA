import sqlite3
from openai import OpenAI
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Usa una variable de entorno por seguridad
client = OpenAI(api_key=OPENAI_API_KEY)

def generar_post(agente, contexto):
    prompt = f"""Eres un usuario de redes sociales con esta personalidad:
Nombre: {agente['nombre']}, Edad: {agente['edad']}
Intereses: {agente['intereses']}
Tono: {agente['tono']}
Objetivo: {agente['objetivo']}
Tipo: {agente['tipo_agente']}
Crea un **micro-post de máximo 2 frases**, directo y breve, considerando tus intereses, tono, objetivo y tipo de agente que eres, relacionalo al tema del contexto.
Usa emojis solo si encajan naturalmente con el tono del personaje.

Tema: {contexto}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        mensaje = response.choices[0].message
        return mensaje.content.strip() if mensaje else "[Post vacío por error de respuesta]"
    except:
        print("[ERROR en generación de post]:", e)
        return "[Error generando post]"