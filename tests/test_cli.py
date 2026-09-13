import re
from datetime import datetime
from pathlib import Path

import pytest

from bingo_musical import cli
from bingo_musical.spotify import Playlist, Track


def test_output_dir_structure():
    now = datetime(2026, 9, 13, 18, 5, 9)
    assert cli.output_dir("Fiesta de Cumpleaños", now=now) == Path("output/fiesta-de-cumpleanos/20260913_180509")
    assert cli.output_dir("Mi lista", Path("/tmp/x"), now) == Path("/tmp/x/mi-lista/20260913_180509")


@pytest.mark.parametrize(
    "name, folder",
    [
        ("Clásicos de la Fiesta de Verano", "clasicos-de-la-fiesta-de-verano"),
        ("  ¡¡ÉXITOS  80's & 90's!!  ", "exitos-80-s-90-s"),
        ("rock_and_roll / Ñoño", "rock-and-roll-nono"),
        ("Top 50 — España 🇪🇸", "top-50-espana"),
        ("🎉🎶", "lista"),
    ],
)
def test_output_dir_playlist_folder_is_kebab_case(name, folder):
    result = cli.output_dir(name, now=datetime(2026, 1, 1)).parent.name
    assert result == folder
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", result)


def _fake_client(n):
    tracks = [Track(id=f"t{i}", name=f"Canción {i}", artists=(f"Artista {i}",)) for i in range(n)]
    playlist = Playlist(id="p", name="Fiesta", owner="Pedro", tracks=tracks)

    class FakeClient:
        def fetch_playlist(self, url):
            return playlist

    return FakeClient


def test_cards_writes_two_pdfs(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "SpotifyClient", _fake_client(30))
    code = cli.main(["cards", "x", "--cards", "3", "--seed", "1", "--output", str(tmp_path)])
    assert code == 0
    (folder,) = (tmp_path / "fiesta").iterdir()
    assert len(folder.name) == len("yyyymmdd_hhmmss")
    assert sorted(p.name for p in folder.iterdir()) == [cli.CARDS_FILE, cli.CONTROL_FILE]


def test_cards_without_control_sheet(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "SpotifyClient", _fake_client(30))
    cli.main(["cards", "x", "--cards", "3", "--output", str(tmp_path), "--no-control-sheet"])
    (folder,) = (tmp_path / "fiesta").iterdir()
    assert [p.name for p in folder.iterdir()] == [cli.CARDS_FILE]
