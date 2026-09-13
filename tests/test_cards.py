import pytest

from bingo_musical.cards import CardError, generate_cards, similarity_warning
from bingo_musical.spotify import Track


def make_tracks(n):
    return [Track(id=f"t{i}", name=f"Canción {i}", artists=(f"Artista {i}",)) for i in range(n)]


def test_cards_shape_and_no_repeats():
    cards = generate_cards(make_tracks(40), n_cards=15, rows=3, cols=4, seed=1)
    assert [c.number for c in cards] == list(range(1, 16))
    for card in cards:
        assert len(card.cells) == 3 and all(len(row) == 4 for row in card.cells)
        ids = [t.id for row in card.cells for t in row]
        assert len(set(ids)) == 12
    assert len({frozenset(t.id for row in c.cells for t in row) for c in cards}) == 15


def test_same_seed_same_cards():
    tracks = make_tracks(30)
    assert generate_cards(tracks, 5, 3, 3, seed=42) == generate_cards(tracks, 5, 3, 3, seed=42)
    assert generate_cards(tracks, 5, 3, 3, seed=42) != generate_cards(tracks, 5, 3, 3, seed=43)


def test_not_enough_tracks():
    with pytest.raises(CardError, match="18 canciones"):
        generate_cards(make_tracks(18), 1, 4, 5, seed=1)


def test_not_enough_combinations():
    # C(5, 4) = 5 cartones distintos como máximo
    assert len(generate_cards(make_tracks(5), 5, 2, 2, seed=1)) == 5
    with pytest.raises(CardError):
        generate_cards(make_tracks(5), 6, 2, 2, seed=1)


def test_similarity_warning():
    assert similarity_warning(14, 3, 4) is not None
    assert similarity_warning(60, 3, 4) is None
