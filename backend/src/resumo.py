"""
    Módulo responsável pelo resumo de um documento enviado a plataforma
"""


from datetime import date
from material import Material

class Resumo(Material):
    """
    Classe Resumo: Responsável por armazenar um breve resumo de um tópico/documento do usuário.

    Attributes:
            id (int): ID do material
            subject_id (int): ID da matéria
            titulo (str): Nome do material
            conteudo (str): Conteúdo do material
            creation_date (date): Data de criação do material
    """

    def __init__(self, subject_id: int, titulo: str, conteudo: str, creation_date=date.today(), id=None):
        """Inicializa um novo material

        Args:
            subject_id (int): ID da matéria
            id (int): ID do material
            titulo (str): Nome do material
            conteudo (str): Conteúdo do material
            creation_date (date): Data de criação do material
        """
        super().__init__(subject_id, titulo, creation_date, id)
        self.conteudo = conteudo

    def __str__(self):
        """
        Define o formato padrão de impressão de um Material
        """
        return super().__str__() + f" Conteúdo: {self.conteudo}"
