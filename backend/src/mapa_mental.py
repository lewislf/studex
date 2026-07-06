"""
    Módulo responsável pelo mapa mental de um documento enviado a plataforma
"""


from datetime import date
from material import Material

class MapaMental(Material):
    """
    Classe MapaMental: Responsável por armazenar o mapa mental (grafo de
    nós e arestas) de um tópico/documento do usuário.

    Attributes:
            id (int): ID do material
            subject_id (int): ID da matéria
            titulo (str): Nome do material
            conteudo (str): Conteúdo do material (JSON com nodes/edges)
            creation_date (date): Data de criação do material
    """

    def __init__(self, subject_id: int, titulo: str, conteudo: str, creation_date=date.today(), id=None):
        """Inicializa um novo mapa mental

        Args:
            subject_id (int): ID da matéria
            id (int): ID do material
            titulo (str): Nome do material
            conteudo (str): Conteúdo do material (JSON com nodes/edges)
            creation_date (date): Data de criação do material
        """
        super().__init__(subject_id, titulo, creation_date, id)
        self.conteudo = conteudo

    def __str__(self):
        """
        Define o formato padrão de impressão de um Material
        """
        return super().__str__() + f" Conteúdo: {self.conteudo}"
