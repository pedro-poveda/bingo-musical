"""Generación de cartones de bingo (lógica pura, sin I/O)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Sequence

from .spotify import Track


class CardError(ValueError):
    pass


@dataclass(frozen=True)
class Card:
    number: int
    cells: tuple[tuple[Track, ...], ...]


def new_seed() -> int:
    return random.SystemRandom().randrange(1, 1_000_000)


def generate_cards(
    tracks: Sequence[Track],
    n_cards: int,
    rows: int,
    cols: int,
    seed: int,
    max_attempts: int = 10_000,
) -> list[Card]:
    """Crea `n_cards` cartones distintos de `rows`×`cols` canciones sin repetir dentro del cartón."""
    if n_cards < 1 or rows < 1 or cols < 1:
        raise CardError("El número de cartones, filas y columnas debe ser al menos 1.")
    size = rows * cols
    if len(tracks) < size:
        raise CardError(
            f"La lista tiene {len(tracks)} canciones y un cartón {rows}×{cols} necesita {size}. "
            "Usa menos filas/columnas o una lista más larga."
        )
    if math.comb(len(tracks), size) < n_cards:
        raise CardError(
            f"Con {len(tracks)} canciones solo se pueden hacer {math.comb(len(tracks), size)} "
            f"cartones distintos de {rows}×{cols}."
        )

    rng = random.Random(seed)
    seen: set[frozenset[str]] = set()
    cards: list[Card] = []
    attempts = 0
    while len(cards) < n_cards:
        chosen = rng.sample(list(tracks), size)
        key = frozenset(t.id for t in chosen)
        if key in seen:
            attempts += 1
            if attempts > max_attempts:
                raise CardError("No se han podido generar suficientes cartones distintos.")
            continue
        seen.add(key)
        grid = tuple(tuple(chosen[r * cols : (r + 1) * cols]) for r in range(rows))
        cards.append(Card(number=len(cards) + 1, cells=grid))
    return cards


def similarity_warning(n_tracks: int, rows: int, cols: int) -> str | None:
    size = rows * cols
    if n_tracks < size * 1.5:
        return (
            f"Aviso: solo hay {n_tracks} canciones para cartones de {size} casillas; "
            "los cartones se parecerán mucho y puede haber varios ganadores a la vez."
        )
    return None
