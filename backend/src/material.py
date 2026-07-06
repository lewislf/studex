"""
    Classe auxiliar para ajudar na criação de resumos, mapas mentais e baralhos de revisão.
"""


from datetime import date

class Material:
    """
    Classe auxiliar para ajudar na criação de resumos, mapas mentais e baralhos de revisão.

    Attributes:
            id (int): ID do material
            subject_id (int): ID da matéria
            titulo (str): Nome do material
            creation_date (date): Data de criação do material
    """

    def __init__(self, subject_id: int, titulo: str, creation_date=date.today(), id=None):
        """Inicializa um novo material

        Args:
            subject_id (int): ID da matéria
            id (int): ID do material
            titulo (str): Nome do material
            creation_date (date): Data de criação do material
        """
        self.date = creation_date
        self.titulo = titulo
        self.date = creation_date
        self.id = id
        self.subject_id = subject_id

    def __str__(self):
        """
        Define o formato padrão de impressão de um Material
        """
        return f"Título: {self.titulo}\nCriado em: {self.date}"
