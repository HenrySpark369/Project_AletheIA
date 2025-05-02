class Post:
    def __init__(self, id, agente_id, contenido, created_at):
        self.id = id
        self.agente_id = agente_id
        self.contenido = contenido
        self.created_at = created_at

    def to_dict(self):
        return {
            "id": self.id,
            "agente_id": self.agente_id,
            "contenido": self.contenido,
            "created_at": self.created_at
        }