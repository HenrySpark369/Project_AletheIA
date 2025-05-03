from utils.sherlock_wrapper import buscar_en_fuentes
from utils.similarity import evaluar_similitud
from repositories.clone_repo import guardar_resultado

def procesar_busqueda_clones(nombre, username, correo, ruta_imagen):
    query = nombre or username or correo
    resultados = buscar_en_fuentes(query)
    clones_detectados = []

    for resultado in resultados:
        score = evaluar_similitud(nombre, username, correo, resultado)
        ruta = ruta_imagen if isinstance(ruta_imagen, str) else str(ruta_imagen or "")
        if score > 0.2:
            # Extrae URL y fuente de cada resultado
            url = resultado.get('url', '')
            fuente = resultado.get('fuente', 'web')

            guardar_resultado(nombre, username, correo, ruta, resultado, score, fuente, url)
            clones_detectados.append((resultado, score))

    return clones_detectados