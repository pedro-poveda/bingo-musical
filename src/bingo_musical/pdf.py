"""Render de cartones y hoja de control en PDF A4 apaisado, en blanco y negro."""

from __future__ import annotations

import functools
from collections.abc import Sequence
from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from .cards import Card
from .spotify import Playlist, Track, _normalize, clean_title

PAGE_W, PAGE_H = landscape(A4)
MARGIN = 12 * mm
HEADER_H = 14 * mm
FOOTER_H = 6 * mm
CELL_PAD = 3 * mm
ELLIPSIS = "…"

_FONT_CANDIDATES = [
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
]


@functools.lru_cache(maxsize=1)
def fonts() -> tuple[str, str]:
    """(regular, negrita). Usa una TTF del sistema para tildes/ñ; Helvetica si no hay."""
    for regular, bold in _FONT_CANDIDATES:
        if Path(regular).exists() and Path(bold).exists():
            try:
                pdfmetrics.registerFont(TTFont("BingoSans", regular))
                pdfmetrics.registerFont(TTFont("BingoSans-Bold", bold))
                return "BingoSans", "BingoSans-Bold"
            except Exception:
                continue
    return "Helvetica", "Helvetica-Bold"


def _width(text: str, font: str, size: float) -> float:
    return pdfmetrics.stringWidth(text, font, size)


def truncate(text: str, font: str, size: float, width: float) -> str:
    if _width(text, font, size) <= width:
        return text
    while text and _width(text + ELLIPSIS, font, size) > width:
        text = text[:-1]
    return text.rstrip() + ELLIPSIS


def _wrap(text: str, font: str, size: float, width: float) -> list[str]:
    return simpleSplit(text, font, size, width) if text else []


def _fits(lines: list[str], font: str, size: float, width: float) -> bool:
    return all(_width(line, font, size) <= width for line in lines)


def layout_cell(
    title: str, artist: str, width: float, height: float, max_title_lines: int = 3, max_artist_lines: int = 2
) -> tuple[list[str], float, list[str], float]:
    """Busca el mayor tamaño de letra con el que título y artista caben en la casilla."""
    regular, bold = fonts()
    size = min(16.0, height / 4.5)
    min_size = 5.0
    while True:
        artist_size = size * 0.72
        t_lines = _wrap(title, bold, size, width)
        a_lines = _wrap(artist, regular, artist_size, width)
        needed = len(t_lines) * size * 1.15 + size * 0.35 + len(a_lines) * artist_size * 1.15
        ok = (
            len(t_lines) <= max_title_lines
            and len(a_lines) <= max_artist_lines
            and needed <= height
            and _fits(t_lines, bold, size, width)
            and _fits(a_lines, regular, artist_size, width)
        )
        if ok:
            return t_lines, size, a_lines, artist_size
        if size - 0.5 < min_size:
            break
        size -= 0.5

    # Último recurso: tamaño mínimo y recorte con puntos suspensivos.
    t_lines = _clip_lines(t_lines, max_title_lines, bold, size, width)
    a_lines = _clip_lines(a_lines, max_artist_lines, regular, artist_size, width)
    return t_lines, size, a_lines, artist_size


def _clip_lines(lines: list[str], max_lines: int, font: str, size: float, width: float) -> list[str]:
    clipped = [truncate(line, font, size, width) for line in lines[:max_lines]]
    if len(lines) > max_lines and clipped:
        last = clipped[-1].rstrip(ELLIPSIS)
        clipped[-1] = truncate(last + ELLIPSIS, font, size, width)
    return clipped


def _draw_cell(c: Canvas, track: Track, x: float, y: float, w: float, h: float, clean: bool) -> None:
    regular, bold = fonts()
    title = clean_title(track.name) if clean else track.name
    inner_w, inner_h = w - 2 * CELL_PAD, h - 2 * CELL_PAD
    t_lines, t_size, a_lines, a_size = layout_cell(title, track.artist_line, inner_w, inner_h)
    total = len(t_lines) * t_size * 1.15 + t_size * 0.35 + len(a_lines) * a_size * 1.15
    cx = x + w / 2
    cursor = y + h / 2 + total / 2

    c.setFillGray(0)
    c.setFont(bold, t_size)
    for line in t_lines:
        cursor -= t_size * 1.15
        c.drawCentredString(cx, cursor + t_size * 0.25, line)
    cursor -= t_size * 0.35
    c.setFillGray(0.25)
    c.setFont(regular, a_size)
    for line in a_lines:
        cursor -= a_size * 1.15
        c.drawCentredString(cx, cursor + a_size * 0.25, line)
    c.setFillGray(0)


def _draw_header(c: Canvas, left: str, right: str) -> None:
    _, bold = fonts()
    baseline = PAGE_H - MARGIN - 8 * mm
    c.setFillGray(0)
    c.setFont(bold, 13)
    right_w = _width(right, bold, 13)
    c.drawRightString(PAGE_W - MARGIN, baseline, right)
    c.setFont(bold, 17)
    c.drawString(MARGIN, baseline, truncate(left, bold, 17, PAGE_W - 2 * MARGIN - right_w - 10 * mm))
    c.setLineWidth(0.6)
    line_y = PAGE_H - MARGIN - HEADER_H + 2 * mm
    c.line(MARGIN, line_y, PAGE_W - MARGIN, line_y)


def _draw_footer(c: Canvas, text: str) -> None:
    regular, _ = fonts()
    c.setFillGray(0.4)
    c.setFont(regular, 7)
    c.drawString(MARGIN, MARGIN, text)
    c.setFillGray(0)


def _draw_card(c: Canvas, playlist: Playlist, card: Card, seed: int, clean: bool) -> None:
    _draw_header(c, playlist.name, f"Cartón nº {card.number}")
    rows, cols = len(card.cells), len(card.cells[0])
    x0, y0 = MARGIN, MARGIN + FOOTER_H
    grid_w = PAGE_W - 2 * MARGIN
    grid_h = PAGE_H - 2 * MARGIN - HEADER_H - FOOTER_H
    cell_w, cell_h = grid_w / cols, grid_h / rows

    c.setLineWidth(0.8)
    c.rect(x0, y0, grid_w, grid_h)
    for i in range(1, cols):
        c.line(x0 + i * cell_w, y0, x0 + i * cell_w, y0 + grid_h)
    for j in range(1, rows):
        c.line(x0, y0 + j * cell_h, x0 + grid_w, y0 + j * cell_h)

    for r, row in enumerate(card.cells):
        for col, track in enumerate(row):
            cell_y = y0 + grid_h - (r + 1) * cell_h
            _draw_cell(c, track, x0 + col * cell_w, cell_y, cell_w, cell_h, clean)
    _draw_footer(c, f"Bingo musical · semilla {seed}")


def _draw_control_sheets(c: Canvas, playlist: Playlist, seed: int, clean: bool) -> int:
    regular, bold = fonts()
    columns = 3
    row_h = 16.0
    size = 8.5
    gap = 6 * mm
    box = 3 * mm
    top = PAGE_H - MARGIN - HEADER_H - 4 * mm
    bottom = MARGIN + FOOTER_H
    rows_per_col = int((top - bottom) // row_h)
    per_page = rows_per_col * columns
    col_w = (PAGE_W - 2 * MARGIN - gap * (columns - 1)) / columns

    entries = sorted(
        playlist.tracks,
        key=lambda t: (_normalize(clean_title(t.name) if clean else t.name), _normalize(t.artist_line)),
    )
    pages = max(1, -(-len(entries) // per_page))
    for page in range(pages):
        label = "Hoja de control" + (f" ({page + 1}/{pages})" if pages > 1 else "")
        _draw_header(c, playlist.name, label)
        chunk = entries[page * per_page : (page + 1) * per_page]
        for i, track in enumerate(chunk):
            col, row = divmod(i, rows_per_col)
            x = MARGIN + col * (col_w + gap)
            baseline = top - row * row_h - size
            c.setLineWidth(0.6)
            c.rect(x, baseline - 0.5, box, box)
            text_x = x + box + 2 * mm
            avail = col_w - box - 2 * mm
            title = truncate(clean_title(track.name) if clean else track.name, bold, size, avail)
            c.setFont(bold, size)
            c.drawString(text_x, baseline, title)
            used = _width(title, bold, size)
            rest = avail - used - _width(" · ", regular, size)
            if track.artist_line and rest > 15:
                c.setFillGray(0.25)
                c.setFont(regular, size)
                c.drawString(text_x + used, baseline, " · " + truncate(track.artist_line, regular, size, rest))
                c.setFillGray(0)
        _draw_footer(c, f"{len(entries)} canciones · semilla {seed}")
        c.showPage()
    return pages


def _canvas(path: Path, title: str) -> Canvas:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    c.setTitle(title)
    c.setCreator("bingo-musical")
    return c


def render_cards_pdf(playlist: Playlist, cards: Sequence[Card], path: Path, seed: int, clean: bool = True) -> int:
    """Escribe el PDF de cartones (una página por cartón) y devuelve el número de páginas."""
    c = _canvas(path, f"Bingo musical · {playlist.name}")
    for card in cards:
        _draw_card(c, playlist, card, seed, clean)
        c.showPage()
    c.save()
    return len(cards)


def render_control_sheet_pdf(playlist: Playlist, path: Path, seed: int, clean: bool = True) -> int:
    """Escribe el PDF de la hoja de control y devuelve el número de páginas."""
    c = _canvas(path, f"Hoja de control · {playlist.name}")
    pages = _draw_control_sheets(c, playlist, seed, clean)
    c.save()
    return pages
