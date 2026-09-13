from pypdf import PdfReader

from bingo_musical.cards import generate_cards
from bingo_musical.pdf import fonts, layout_cell, render_pdf
from bingo_musical.spotify import Playlist, Track


def make_playlist(n):
    tracks = [
        Track(id="long", name="Una canción con un título larguísimo que no cabe en una sola línea ni en dos " * 2,
              artists=("Artista Uno", "Artista Dos", "Tercera Artista Con Nombre Largo")),
        Track(id="accents", name="Mediterráneo (feat. Niña Pastori)", artists=("Joan Manuel Serrat",)),
    ]
    tracks += [Track(id=f"t{i}", name=f"Canción {i}", artists=(f"Artista {i}",)) for i in range(n - 2)]
    return Playlist(id="p", name="Fiesta de cumpleaños", owner="Pedro", tracks=tracks)


def test_render_pdf_pages_and_orientation(tmp_path):
    playlist = make_playlist(30)
    cards = generate_cards(playlist.tracks, 4, 3, 4, seed=7)
    out = tmp_path / "bingo.pdf"
    pages = render_pdf(playlist, cards, out, seed=7)
    reader = PdfReader(out)
    assert pages == len(reader.pages) == 5  # 4 cartones + 1 hoja de control
    box = reader.pages[0].mediabox
    assert box.width > box.height
    text = reader.pages[0].extract_text()
    assert "Fiesta de cumpleaños" in text and "Cartón nº 1" in text
    assert "Hoja de control" in reader.pages[-1].extract_text()


def test_control_sheet_paginates_and_can_be_disabled(tmp_path):
    playlist = make_playlist(200)
    cards = generate_cards(playlist.tracks, 2, 5, 5, seed=1)
    assert render_pdf(playlist, cards, tmp_path / "a.pdf", seed=1) > 3
    assert render_pdf(playlist, cards, tmp_path / "b.pdf", seed=1, control_sheet=False) == 2


def test_layout_cell_fits_within_bounds():
    from reportlab.pdfbase.pdfmetrics import stringWidth

    regular, bold = fonts()
    title = "Supercalifragilisticoespialidoso " * 6
    t_lines, t_size, a_lines, a_size = layout_cell(title, "Alguien, Otra Persona", 120, 50)
    assert len(t_lines) <= 3 and len(a_lines) <= 2
    assert all(stringWidth(line, bold, t_size) <= 120 for line in t_lines)
    assert all(stringWidth(line, regular, a_size) <= 120 for line in a_lines)
