from enums.flashcard_status import FlashcardStatus
from datetime import date

class Flashcard:
    """ Flashcard padrão Anki 

        Attributes:
        deck_id (int): ID do Baralho que pertence
        pergunte (str): Frente do Flashcard
        resposta (str): Verso do Flashcard
        status (FlashcardStatus): ENUM definido em FlashcardStatus
        date (date): Data de criação
        id (int): id do Flashcard
    """
    def __init__(
        self,
        deck_id: int,
        pergunta: str,
        resposta: str,
        status: FlashcardStatus = FlashcardStatus.NOVO,
        creation_date: date = date.today(),
        id = None,
        embedding: list[float] | None = None,
    ):
        """Construtor Flashcard

        Args:
            deck_id (int): ID do Baralho que pertence
            pergunte (str): Frente do Flashcard
            resposta (str): Verso do Flashcard
            status (FlashcardStatus): ENUM definido em FlashcardStatus
            creation_date (date): Data de criação
            id (int): id do Flashcard
            embedding (list[float] | None): embedding de "pergunta\\nresposta"
                usado na deduplicação semântica. None se ainda não calculado
                (migração preguiçosa na primeira comparação).
        """
        self.deck_id = deck_id
        self.pergunta = pergunta
        self.resposta = resposta
        self.status = status
        self.date = creation_date
        self.id = id
        self.embedding = embedding

    def __str__(self):
        """
        Define o formato padrão de impressão de um Baralho
        """
        
        return f"Frente: {self.pergunta} - Verso: {self.resposta}; Status: {self.status}"
    
    def to_dict(self):
        """
        Retorna um dicionario de Flashcards, facilitando o envio de JSONs
        """
        return {
            "id": self.id,
            "deck_id": self.deck_id,
            "pergunta": self.pergunta,
            "resposta": self.resposta,
            "status": self.status,
            "creation_date": self.date,
        }
