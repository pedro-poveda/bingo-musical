---
name: spotify-playlist
description: Obtiene las canciones (título y artistas) de una lista de Spotify a partir de su URL. Úsala cuando el usuario comparta una URL/URI de lista de Spotify y quiera ver, revisar o exportar sus canciones.
---

# Obtener canciones de una lista de Spotify

Ejecuta desde la raíz del proyecto:

```bash
uv run bingo-musical songs "<URL de la lista>" --json
```

- Acepta `https://open.spotify.com/playlist/<id>?si=...`, `spotify:playlist:<id>` o el id.
- El JSON devuelve `name`, `owner` y `tracks` (`id`, `name`, `artists`). Sin `--json` imprime una lista numerada legible.
- Se descartan episodios de podcast, pistas locales y canciones duplicadas.

## Errores habituales

- **Faltan credenciales**: el usuario debe crear una app en https://developer.spotify.com/dashboard, copiar `.env.example` a `.env` y rellenar `SPOTIFY_CLIENT_ID` y `SPOTIFY_CLIENT_SECRET`. No pidas ni escribas tú los secretos en el chat.
- **404 / 403**: la lista es privada o es una lista editorial/algorítmica de Spotify (Top 50, Descubrimiento semanal…), que no son accesibles para apps nuevas. Sugiere copiar las canciones a una lista pública propia.
