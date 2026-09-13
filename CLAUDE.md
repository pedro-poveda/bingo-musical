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
uv run bingo-musical cards "<url>" --cards 10 --rows 3 --cols 4 [--seed N] [--output carpeta] [--no-control-sheet] [--full-titles]
```

No hay linter ni formateador configurado. Cada ejecución de `cards` crea `output/<slug-lista>/<yyyymmdd_hhmmss>/` (ignorado en git; `--output` cambia la carpeta base) con dos PDF: `cartones.pdf` y `hoja-control.pdf`.

## Arquitectura

Flujo: `cli.py` → `SpotifyClient.fetch_playlist` (`spotify.py`) → `generate_cards` (`cards.py`) → `render_cards_pdf` y `render_control_sheet_pdf` (`pdf.py`), cada uno a su propio PDF en la carpeta que calcula `output_dir` (`cli.py`).

- **`spotify.py`**: autenticación Client Credentials con `SPOTIFY_CLIENT_ID`/`SPOTIFY_CLIENT_SECRET` desde `.env` para metadatos y búsquedas. Para listar canciones, Spotify exige sesión de usuario aunque la lista sea pública: si `/playlists/{id}/items` (o `/tracks`) responde 401/403 con el token de Client Credentials, `_get` cambia automáticamente a un token de usuario vía `auth.get_user_token` (ver `auth.py`). Pide primero `/playlists/{id}/items` (campo `item`) y, si da 404, recurre al antiguo `/tracks` (campo `track`). Filtra episodios, pistas locales y duplicados (por id y por título limpio + primer artista). `clean_title` (quita "(feat. …)", "- Remastered 2011", etc.) se reutiliza en `pdf.py` tanto para mostrar como para ordenar.
- **`auth.py`**: login de usuario Authorization Code + PKCE (sin client secret). Abre el navegador, recibe el código en un servidor HTTP local (Redirect URI registrada: `http://127.0.0.1:8888/callback`) y cachea access/refresh token en `~/.cache/bingo-musical/token.json` para no pedir login en cada ejecución. Solo se invoca cuando Client Credentials no basta.
- **`cards.py`**: lógica pura. Necesita siempre una `seed` (la CLI genera una con `new_seed()` si no se pasa) para que los cartones sean reproducibles; el resultado depende también del orden de las canciones de la lista. Garantiza canciones distintas dentro de cada cartón y cartones distintos entre sí.
- **`pdf.py`**: reportlab. `fonts()` registra una TTF del sistema (Arial en macOS, DejaVu en Linux) para soportar tildes/ñ, con Helvetica como fallback; los caracteres fuera de la fuente no se ven. `layout_cell` reduce el tamaño de letra hasta que título y artista quepan y, como último recurso, recorta con "…". La hoja de control (lista alfabética con casillas, 3 columnas, paginada) se genera en un PDF aparte.
- **`cli.py`**: solo `SpotifyError` y `CardError` se convierten en mensajes `Error: …` con código de salida 1.

Los tests de Spotify no llaman a la API real: usan `httpx.MockTransport` inyectado vía `SpotifyClient(transport=..., sleep=...)`.

## Limitaciones de Spotify

Las apps nuevas en modo desarrollo no pueden leer listas editoriales/algorítmicas de Spotify (Top 50, Descubrimiento semanal…) y devuelven 404. Para listas de usuario (públicas o privadas), Spotify además exige sesión de usuario para listar canciones (Client Credentials da 401/403 en `/items` y `/tracks` aunque sí sirve para los metadatos de la lista): `spotify.py` cambia entonces a login OAuth PKCE (`auth.py`) de forma transparente, abriendo el navegador la primera vez.
