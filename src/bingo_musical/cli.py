"""CLI: `bingo-musical songs <url>` y `bingo-musical cards <url>`."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from .cards import CardError, generate_cards, new_seed, similarity_warning
from .pdf import render_cards_pdf, render_control_sheet_pdf
from .spotify import SpotifyClient, SpotifyError

CARDS_FILE = "cartones.pdf"
CONTROL_FILE = "hoja-control.pdf"


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("debe ser un entero mayor que 0")
    return number


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower() or "lista"


def output_dir(playlist_name: str, base: Path | None = None, now: datetime | None = None) -> Path:
    """Carpeta de un bingo: <base>/<lista>/<yyyymmdd_hhmmss>."""
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return (base or Path("output")) / _slug(playlist_name) / stamp


def cmd_songs(args: argparse.Namespace) -> int:
    playlist = SpotifyClient().fetch_playlist(args.url)
    if args.json:
        data = {
            "id": playlist.id,
            "name": playlist.name,
            "owner": playlist.owner,
            "tracks": [{"id": t.id, "name": t.name, "artists": list(t.artists)} for t in playlist.tracks],
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"{playlist.name} ({playlist.owner}) · {len(playlist.tracks)} canciones")
        for i, track in enumerate(playlist.tracks, 1):
            print(f"{i:>4}. {track.name} — {track.artist_line}")
    return 0


def cmd_cards(args: argparse.Namespace) -> int:
    playlist = SpotifyClient().fetch_playlist(args.url)
    seed = args.seed if args.seed is not None else new_seed()
    cards = generate_cards(playlist.tracks, args.cards, args.rows, args.cols, seed)
    folder = output_dir(playlist.name, args.output)
    clean = not args.full_titles
    cards_path = folder / CARDS_FILE
    pages = render_cards_pdf(playlist, cards, cards_path, seed, clean=clean)
    warning = similarity_warning(len(playlist.tracks), args.rows, args.cols)
    if warning:
        print(warning, file=sys.stderr)
    print(f"Cartones: {cards_path.resolve()}")
    if not args.no_control_sheet:
        control_path = folder / CONTROL_FILE
        control_pages = render_control_sheet_pdf(playlist, control_path, seed, clean=clean)
        print(f"Hoja de control: {control_path.resolve()} ({control_pages} páginas)")
    print(f"Lista: {playlist.name} ({len(playlist.tracks)} canciones)")
    print(f"Cartones: {len(cards)} de {args.rows}×{args.cols} · {pages} páginas")
    print(f"Semilla: {seed}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bingo-musical", description="Bingo musical a partir de listas de Spotify.")
    sub = parser.add_subparsers(dest="command", required=True)

    songs = sub.add_parser("songs", help="Lista las canciones de una lista de Spotify")
    songs.add_argument("url", help="URL, URI o id de la lista")
    songs.add_argument("--json", action="store_true", help="Salida en JSON")
    songs.set_defaults(func=cmd_songs)

    cards = sub.add_parser("cards", help="Genera cartones en PDF")
    cards.add_argument("url", help="URL, URI o id de la lista")
    cards.add_argument("--cards", type=_positive_int, default=10, help="Número de cartones (10)")
    cards.add_argument("--rows", type=_positive_int, default=3, help="Filas por cartón (3)")
    cards.add_argument("--cols", type=_positive_int, default=4, help="Columnas por cartón (4)")
    cards.add_argument("--seed", type=int, help="Semilla para reproducir los mismos cartones")
    cards.add_argument(
        "--output",
        type=Path,
        help="Carpeta base (output); los PDF van en <base>/<lista>/<yyyymmdd_hhmmss>/",
    )
    cards.add_argument("--no-control-sheet", action="store_true", help="No generar el PDF de hoja de control")
    cards.add_argument("--full-titles", action="store_true", help="No quitar '(feat. …)', '- Remastered', etc.")
    cards.set_defaults(func=cmd_cards)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (SpotifyError, CardError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
