"""
Repetição espaçada (SRS) para flashcards. Algoritmo SM-2 simplificado.

`apply_review` é uma função pura: recebe o card e a nota dada pelo usuário
e devolve o novo estado (status, due_date, interval_days, ease, reps,
lapses), sem tocar no banco.
"""

from datetime import date, timedelta

RATINGS = ("reset", "dificil", "bom", "facil")

MIN_EASE = 1.3
DEFAULT_EASE = 2.5

# Status que ainda não passaram por um ciclo completo de review.
_NAO_REVIEW = ("novo", "aprendendo", "reaprendendo")


def apply_review(card, rating: str, today: date = None):
    """
    Aplica uma revisão a um flashcard e devolve o novo estado do SRS.

    Parameters
    ----------
    card : objeto com atributos status, interval_days, ease, reps, lapses
        (aceita Flashcard ou qualquer objeto com esses campos).
    rating : "reset" | "dificil" | "bom" | "facil"
        Nota dada pelo usuário na revisão.
    today : date
        Data de referência (default: hoje).

    Returns
    -------
    tuple (status, due_date, interval_days, ease, reps, lapses)
        due_date é string ISO (YYYY-MM-DD).

    Regras
    ------
    - reset (errei): volta para 'reaprendendo', intervalo zera e o card
      reaparece na mesma sessão (due = hoje); ease cai (piso 1.3); soma 1
      lapse. reps não muda.
    - dificil: se ainda não passou por review completo, vira 'aprendendo'
      com due hoje (repete na sessão); se já estava em review, o intervalo
      cresce pouco (x1.2) e a ease cai um pouco (piso 1.3).
    - bom: se novo/aprendendo/reaprendendo, gradua para 'review' com
      intervalo de 1 dia; se já em review, intervalo cresce pela ease.
    - facil: graduação/crescimento mais agressivo e ease aumenta.
    - reps soma 1 em qualquer rating exceto reset.
    """
    if today is None:
        today = date.today()

    if rating not in RATINGS:
        raise ValueError(f"rating inválido: {rating!r}")

    status = str(card.status)
    interval = float(card.interval_days or 0)
    ease = float(card.ease or DEFAULT_EASE)
    reps = int(card.reps or 0)
    lapses = int(card.lapses or 0)

    if rating == "reset":
        new_status = "reaprendendo"
        new_interval = 0
        ease = max(MIN_EASE, ease - 0.2)
        lapses += 1
        due_date = today

    elif rating == "dificil":
        reps += 1
        if status in _NAO_REVIEW:
            new_status = "aprendendo"
            new_interval = 0
            due_date = today
        else:
            new_status = "review"
            new_interval = max(1, interval * 1.2)
            ease = max(MIN_EASE, ease - 0.15)
            due_date = today + timedelta(days=round(new_interval))

    elif rating == "bom":
        reps += 1
        if status in _NAO_REVIEW:
            new_status = "review"
            new_interval = 1
            due_date = today + timedelta(days=1)
        else:
            new_status = "review"
            new_interval = interval * ease
            due_date = today + timedelta(days=round(new_interval))

    else:  # facil
        reps += 1
        if status in _NAO_REVIEW:
            new_status = "review"
            new_interval = 4
            ease += 0.15
            due_date = today + timedelta(days=4)
        else:
            new_status = "review"
            new_interval = interval * ease * 1.3
            ease += 0.15
            due_date = today + timedelta(days=round(new_interval))

    return new_status, due_date.isoformat(), new_interval, ease, reps, lapses
