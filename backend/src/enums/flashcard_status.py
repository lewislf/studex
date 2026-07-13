from enum import StrEnum


class FlashcardStatus(StrEnum):
    NOVO = "novo"
    APRENDENDO = "aprendendo"
    REVIEW = "review"
    REAPRENDENDO = "reaprendendo"
    # FEITO não está no CHECK da tabela flashcards e não é usado no SRS,
    # mantido só por compatibilidade com quem já importa o enum.
    FEITO = "feito"
