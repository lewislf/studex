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
        id = None
    ):
        """Construtor Flashcard

        Args:
            deck_id (int): ID do Baralho que pertence
            pergunte (str): Frente do Flashcard
            resposta (str): Verso do Flashcard
            status (FlashcardStatus): ENUM definido em FlashcardStatus
            creation_date (date): Data de criação
            id (int): id do Flashcard
        """
        self.deck_id = deck_id
        self.pergunta = pergunta
        self.resposta = resposta
        self.status = status
        self.date = creation_date
        self.id = id

    def __str__(self):
        """
        Define o formato padrão de impressão de um Baralho
        """
        
        return f"Frente: {self.pergunta} - Verso: {self.resposta}; Status: {self.status}"
