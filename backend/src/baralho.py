"""
    Módulo responsável pelos baralhos de revisão de um documento enviado a plataforma
"""


from datetime import date
from material import Material

class Baralho(Material):
    """
    Classe Baralho: Responsável por armazenar um breve baralho de um tópico/documento do usuário.

    Attributes:
            id (int): ID do material
            subject_id (int): ID da matéria
            titulo (str): Nome do material
            acuracia (int): Acurácia do Baralho
            novos (int): Quantidade de Flashcards novos no Baralho
            aprendendo (int): Quantidade de Flashcards que precisam ser reforçados
            review (int): Quantidade de Flashcards que necessitam ser revisados e aprendidos novamente
            creation_date (date): Data de criação do material
    """

    def __init__(self, subject_id: int, titulo: str, acuracia: int, novos: int, aprendendo: int, review: int, creation_date=date.today(), id=None):
        """Inicializa um novo material

        Args:
            subject_id (int): ID da matéria
            id (int): ID do material
            titulo (str): Nome do material
            acuracia (int): Acurácia do Baralho
            novos (int): Quantidade de Flashcards novos no Baralho
            aprendendo (int): Quantidade de Flashcards que precisam ser reforçados
            review (int): Quantidade de Flashcards que necessitam ser revisados e aprendidos novamente
            creation_date (date): Data de criação do material
        """
        super().__init__(subject_id, titulo, creation_date, id)
        self.acuracia = acuracia
        self.novos = novos
        self.aprendendo = aprendendo
        self.review = review

    def __str__(self):
        """
        Define o formato padrão de impressão de um Baralho
        """
        return super().__str__() + f" Acurácia: {self.acuracia}"
