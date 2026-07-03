"""
Este módulo contém a classe Matéria do nosso sistema, que é a responsável principal por onde o nosso usuário irá estudar.
"""

from datetime import date

class Materia:
    """Esta classe representa uma matéria da plataforma.

        Attributes:
            id (int): ID da matéria
            name (str): Nome da matéria
            description (str): Breve descrição sobre a matéria
            domain (str): Grande área da matéria
            creation_date (date): Data de criação da matéria
    
        Example:
            > materia = Materia("Projeto Integrado", "Ensina boas práticas no desenvolvimento de software", "Desenvolvimento de Software")
    """
    
    def __init__(self, user_id: int, name: str, description: str, domain: str, creation_date=date.today(), id=None) -> None:
        """Inicializa uma nova matéria.

        Args:
            user_id: O ID do usuário ao qual essa matéria pertence
            name: Nome da matéria.
            description: Uma breve descrição da matéria
            domain: A grande área da matéria.
            creation_date (date): A data de criação da matéria
            id (int): O id da matéria
        """
        self.user_id = user_id
        self.name = name
        self.description = description
        self.domain = domain
      
    def __str__(self):
        """
            Define o formato padrão de impressão da matéria
        """
        return f"Nome: {self.name}, Descrição: {self.description}, Domínio: {self.domain}"
       

