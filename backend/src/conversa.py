"""
    Módulo responsável pelas conversas (chats) de um usuário sobre uma matéria
"""


from datetime import date
from material import Material


class Conversa(Material):
    """
    Classe Conversa: um chat do usuário ligado a uma matéria. As mensagens
    ficam na tabela chat_messages e não são carregadas aqui.

    Attributes:
            id (int): ID da conversa
            subject_id (int): ID da matéria
            user_id (int): ID do dono da conversa
            titulo (str): Nome da conversa
            creation_date (date): Data de criação da conversa
            materia_nome (str | None): Nome da matéria, quando a consulta traz
            materia_cor (str | None): Cor da matéria, quando a consulta traz
    """

    def __init__(self, subject_id: int, user_id: int, titulo: str, creation_date=None, id=None,
                 materia_nome: str | None = None, materia_cor: str | None = None):
        """Inicializa uma nova conversa

        Args:
            subject_id (int): ID da matéria
            user_id (int): ID do usuário
            titulo (str): Nome da conversa
            creation_date (date): Data de criação da conversa
            id (int): ID da conversa
            materia_nome (str): Nome da matéria
            materia_cor (str): Cor da matéria
        """
        # default calculado aqui: date.today() na assinatura congelaria a data do import
        super().__init__(subject_id, titulo, creation_date or date.today(), id)
        self.user_id = user_id
        self.materia_nome = materia_nome
        self.materia_cor = materia_cor

    def __str__(self):
        """
        Define o formato padrão de impressão de uma Conversa
        """
        return super().__str__() + f" Matéria: {self.subject_id}"

    def to_dict(self):
        return {
            "id": self.id,
            "tipo": "conversa",
            "subject_id": self.subject_id,
            "titulo": self.titulo,
            "creation_date": self.date,
            "materia_nome": self.materia_nome,
            "materia_cor": self.materia_cor,
        }
