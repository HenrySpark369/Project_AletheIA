from difflib import SequenceMatcher
from urllib.parse import urlparse

def evaluar_similitud(nombre, username, correo, resultado):
    texto_referencia = " ".join(filter(None, [nombre, username, correo])).lower()
    contenido = resultado.get("contenido", "").lower()
    dominio = urlparse(resultado.get("url", "")).netloc.split('.')[0]  # Ej: github

    score_contenido = SequenceMatcher(None, texto_referencia, contenido).ratio()
    score_dominio = SequenceMatcher(None, texto_referencia, dominio).ratio()

    return max(score_contenido, score_dominio)