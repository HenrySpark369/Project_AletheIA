# models/clone.py

class Clone:
    def __init__(self, nombre, username, correo, ruta_imagen, contenido, url, score_similitud, fuente, fecha=None):
        self.nombre = nombre
        self.username = username
        self.correo = correo
        self.ruta_imagen = ruta_imagen
        self.contenido = contenido
        self.url = url
        self.score_similitud = score_similitud
        self.fuente = fuente
        self.fecha = fecha

    @classmethod
    def from_row(cls, row):
        _, nombre, username, correo, ruta_imagen, contenido, url, score, fuente, fecha = row
        return cls(nombre, username, correo, ruta_imagen, contenido, url, score, fuente, fecha)