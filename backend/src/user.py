"""Módulo de exemplo da documentação do backend StudEx.

Este módulo mostra como documentar o código Python através do *MkDocs* usando *docstrings* para gerar a documentação do back-end.
"""

import json


class Usuario:
    """Esta classe representa um usuário simples da plataforma, criada apenas para demonstrar a geração
    automática de documentação a partir das docstrings.

    Attributes:
        name (str): Nome do usuário.
        email (str): Endereço de e-mail do usuário.
        hash_password (bytes): Hash da senha do usuário.
        gamification (dict): Dados de gamificação com current_streak e active_yesterday.
        counters (dict): Contadores com summaries, mind_maps, pending_flashcards_today e total_flashcards_created.

    Example:
        > user = User("Ana", "ana@studex.com", "9f3a7c2e8b14d6a0f5c9e1b78a42d3c6")

        > user.greet()

        **Output:** 'Olá, Ana!'
    """

    def __init__(
        self, 
        name: str, 
        email: str, 
        hash_password: bytes, 
        id=None,
        gamification: dict = None,
        counters: dict = None
    ) -> None:
        """Inicializa um novo usuário.

        Args:
            name: Nome do usuário.
            email: Endereço de e-mail do usuário.
            hash_password: Hash da senha do usuário.
            id: ID do usuário (opcional).
            gamification: Dicionário com dados de gamificação (opcional).
            counters: Dicionário com contadores (opcional).
        """
        self.name = name
        self.email = email
        self.hash_password = hash_password
        self.id = id
        self.gamification = gamification or {
            "current_streak": 0,
            "active_yesterday": False
        }
        self.counters = counters or {
            "summaries": 0,
            "mind_maps": 0,
            "pending_flashcards_today": 0,
            "total_flashcards_created": 0
        }
    
    def __str__(self):
        """
            Define o formato padrão de impressão do usuário
        """
        return f"Nome: {self.name}, Email: {self.email}"
    
    def to_dict(self):
        """
        Retorna um dicionário de usuário, facilitando o envio de JSONs
        """
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "gamification": self.gamification,
            "counters": self.counters,
        }

    def greet(self) -> str:
        """Gera uma saudação personalizada para o usuário.

        Returns:
            str: Uma mensagem de saudação contendo o nome do usuário.
        """
        return f"Olá, {self.name}!"
