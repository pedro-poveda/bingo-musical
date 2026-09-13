# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

Genera cartones de bingo musical en PDF (A4 apaisado, blanco y negro: título de la canción y artista debajo, más pequeño) a partir de una lista de Spotify. Paquete Python gestionado con `uv`, CLI `bingo-musical` y dos skills de Claude Code (`.claude/skills/spotify-playlist`, `.claude/skills/bingo-cards`) que simplemente invocan la CLI. Código, mensajes y documentación en español.

## Comandos

```bash
uv sync                                   # instala dependencias (incluye grupo dev: pytest, pypdf)
uv run pytest                             # todos los tests
uv run pytest tests/test_cards.py::test_same_seed_same_cards   # un test concreto
uv run bingo-musical songs "<url>" [--json]
uv run bingo-musical cards "<url>" --cards 10 --rows 3 --cols 4 [--seed N] [--output ruta.pdf] [--no-control-sheet] [--full-titles]
```

No hay linter ni formateador configurado. Los PDF se generan por defecto en `output/` (ignorado en git).

## Arquitectura

Flujo: `cli.py` → `SpotifyClient.fetch_playlist` (`spotify.py`) → `generate_cards` (`cards.py`) → `render_pdf` (`pdf.py`).

- **`spotify.py`**: autenticación Client Credentials con `SPOTIFY_CLIENT_ID`/`SPOTIFY_CLIENT_SECRET` desde `.env` (sin login de usuario, solo listas públicas). Pide primero `/playlists/{id}/items` (campo `item`) y, si da 404, recurre al antiguo `/tracks` (campo `track`). Filtra episodios, pistas locales y duplicados (por id y por título limpio + primer artista). `clean_title` (quita "(feat. …)", "- Remastered 2011", etc.) se reutiliza en `pdf.py` tanto para mostrar como para ordenar.
- **`cards.py`**: lógica pura. Necesita siempre una `seed` (la CLI genera una con `new_seed()` si no se pasa) para que los cartones sean reproducibles; el resultado depende también del orden de las canciones de la lista. Garantiza canciones distintas dentro de cada cartón y cartones distintos entre sí.
- **`pdf.py`**: reportlab. `fonts()` registra una TTF del sistema (Arial en macOS, DejaVu en Linux) para soportar tildes/ñ, con Helvetica como fallback; los caracteres fuera de la fuente no se ven. `layout_cell` reduce el tamaño de letra hasta que título y artista quepan y, como último recurso, recorta con "…". La hoja de control (lista alfabética con casillas, 3 columnas, paginada) va al final del PDF.
- **`cli.py`**: solo `SpotifyError` y `CardError` se convierten en mensajes `Error: …` con código de salida 1.

Los tests de Spotify no llaman a la API real: usan `httpx.MockTransport` inyectado vía `SpotifyClient(transport=..., sleep=...)`.

## Limitaciones de Spotify

Las apps nuevas en modo desarrollo no pueden leer listas editoriales/algorítmicas de Spotify (Top 50, Descubrimiento semanal…) y devuelven 404. Si listas públicas de usuario también fallan con Client Credentials, la alternativa prevista es añadir OAuth PKCE; la Redirect URI registrada en la app es `http://127.0.0.1:8888/callback`.
