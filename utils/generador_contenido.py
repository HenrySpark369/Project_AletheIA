# utils/generador_contenido.py
import os
import textwrap
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def generar_post(agente, contexto):
    prompt = textwrap.dedent(f"""
        Eres un agente llamado {agente['nombre']}, de {agente['edad']} años.
        Tus intereses principales son: {agente['intereses']}.
        Tu estilo de comunicación es: {agente['tono']}.
        Tu objetivo al publicar es: {agente['objetivo']}.
        Actúas como un agente de tipo: {agente['tipo_agente']}.
        Teniendo en cuenta tu personalidad, atributos asi como el {contexto}, genera un post relacionado con el tema proporcionado.
        Sé directo, breve y cautivador: máximo 1 oración.
        Utiliza un lenguaje acorde a tu estilo y objetivos. Usa emojis solo si encajan de forma natural con tu tono.
    """)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        mensaje = response.choices[0].message
        return mensaje.content.strip() if mensaje else "[Post vacío por error de respuesta]"
    except Exception as e:
        print("[ERROR en generación de post]:", e)
        return "[Error generando post]"