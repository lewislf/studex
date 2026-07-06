from enum import StrEnum


class FlashcardStatus(StrEnum):
    NOVO = "novo"
    APRENDENDO = "aprendendo"
    REVIEW = "review"
    FEITO = "feito"
