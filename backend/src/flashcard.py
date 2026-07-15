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
        due_date (str | None): data (ISO) em que o card deve ser revisado
        interval_days (float): intervalo atual em dias (SRS)
        ease (float): fator de facilidade (SRS, estilo SM-2)
        reps (int): número de revisões feitas
        lapses (int): número de vezes que o card foi "resetado" (errado)
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
        due_date: str | None = None,
        interval_days: float = 0,
        ease: float = 2.5,
        reps: int = 0,
        lapses: int = 0,
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
            due_date (str | None): data ISO da próxima revisão (SRS)
            interval_days (float): intervalo atual em dias (SRS)
            ease (float): fator de facilidade (SRS)
            reps (int): número de revisões feitas
            lapses (int): número de vezes que o card foi resetado
        """
        self.deck_id = deck_id
        self.pergunta = pergunta
        self.resposta = resposta
        self.status = status
        self.date = creation_date
        self.id = id
        self.embedding = embedding
        self.due_date = due_date
        self.interval_days = interval_days
        self.ease = ease
        self.reps = reps
        self.lapses = lapses

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
            "due_date": self.due_date,
            "interval_days": self.interval_days,
            "ease": self.ease,
            "reps": self.reps,
            "lapses": self.lapses,
        }
