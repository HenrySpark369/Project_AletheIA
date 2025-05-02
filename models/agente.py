class Agente:
    def __init__(self, id, nombre, edad, intereses, tono, objetivo, tipo_agente):
        self.id = id
        self.nombre = nombre
        self.edad = edad
        self.intereses = intereses
        self.tono = tono
        self.objetivo = objetivo
        self.tipo_agente = tipo_agente

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "edad": self.edad,
            "intereses": self.intereses,
            "tono": self.tono,
            "objetivo": self.objetivo,
            "tipo_agente": self.tipo_agente
        }