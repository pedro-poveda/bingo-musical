<div align="center">

# 🎵 Bingo Musical

**Convierte cualquier lista de Spotify en cartones de bingo listos para imprimir.**

![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/gestor-uv-DE5FE9)
![Spotify Web API](https://img.shields.io/badge/Spotify-Web%20API-1DB954?logo=spotify&logoColor=white)
![PDF](https://img.shields.io/badge/salida-PDF%20A4%20apaisado-EC1C24?logo=adobeacrobatreader&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude%20Code-skills-D97757)

</div>

---

## ✨ Qué hace

| | |
|---|---|
| 🎧 **Lee listas de Spotify** | Pega la URL de una lista y obtén todas sus canciones, sin duplicados ni podcasts. Si Spotify lo exige, inicias sesión una sola vez en el navegador. |
| 🃏 **Genera cartones únicos** | Elige cuántos cartones y cuántas filas × columnas. Nunca se repite una canción en un cartón ni hay dos cartones iguales. |
| 🖨️ **Ahorra tinta** | PDF A4 apaisado en blanco y negro: título de la canción y, debajo, el artista en letra más pequeña. |
| 📋 **Hoja de control** | Lista alfabética de todas las canciones con casillas para ir marcando las que suenan. |
| 🎲 **Reproducible** | Cada PDF lleva una semilla: con ella puedes reimprimir exactamente los mismos cartones. |
| 🤖 **Skills de Claude Code** | Pídeselo a Claude en lenguaje natural: *"hazme 20 cartones de 3×4 con esta lista"*. |

<table>
<tr>
<td align="center"><b>Cartón</b></td>
<td align="center"><b>Hoja de control</b></td>
</tr>
<tr>
<td><img src="docs/ejemplo-carton.png" alt="Ejemplo de cartón de bingo musical" width="420"></td>
<td><img src="docs/ejemplo-hoja-control.png" alt="Ejemplo de hoja de control" width="420"></td>
</tr>
</table>

---

## 🚀 Puesta en marcha

### 1. Requisitos

- [uv](https://docs.astral.sh/uv/) (instala Python automáticamente si hace falta)
- Una cuenta de Spotify

### 2. Crea la app en Spotify

1. Entra en el [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) y pulsa **Create app**.
2. Rellena nombre y descripción. En **Redirect URIs** pon exactamente `http://127.0.0.1:8888/callback` (se usa para el inicio de sesión, ver más abajo).
3. Marca **Web API** y guarda.
4. En **Settings** copia el **Client ID** y el **Client Secret**.
5. Si otra persona va a usar el proyecto con su cuenta, añádela en **User Management**: las apps en modo desarrollo solo admiten usuarios dados de alta.

### 3. Configura el proyecto

```bash
uv sync                  # instala dependencias
cp .env.example .env     # y rellena las credenciales
```

```dotenv
SPOTIFY_CLIENT_ID=tu_client_id
SPOTIFY_CLIENT_SECRET=tu_client_secret
```

> [!IMPORTANT]
> `.env` está en `.gitignore`. No compartas nunca el Client Secret.

### 4. Primer inicio de sesión

Con el Client ID y el Client Secret basta para leer el nombre de una lista, pero **Spotify exige una sesión de usuario para leer sus canciones**, aunque la lista sea pública. El programa lo detecta solo:

1. La primera vez que pidas canciones verás:
   ```text
   Spotify requiere que inicies sesión para leer las canciones de esta lista.
   Abriendo el navegador...
   ```
2. Inicia sesión en Spotify y acepta los permisos (solo lectura de tus listas, incluidas privadas y colaborativas).
3. El navegador vuelve a `http://127.0.0.1:8888/callback`, muestra *"Sesión iniciada con Spotify"* y el comando continúa. Tienes 3 minutos para completarlo.

El token se guarda en `~/.cache/bingo-musical/token.json` y se renueva automáticamente, así que en las siguientes ejecuciones no se vuelve a abrir el navegador.

> [!TIP]
> Para cerrar sesión o entrar con otra cuenta, borra `~/.cache/bingo-musical/token.json`.

---

## 🛠️ Uso de los comandos

La URL puede ser de cualquiera de estas formas:

```text
https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=...
https://open.spotify.com/intl-es/playlist/37i9dQZF1DXcBWIGoYBM5M
spotify:playlist:37i9dQZF1DXcBWIGoYBM5M
37i9dQZF1DXcBWIGoYBM5M
```

### 🎧 `songs` — ver las canciones de una lista

```bash
uv run bingo-musical songs "https://open.spotify.com/playlist/<id>"
```

```text
Clásicos de la Fiesta de Verano (Pedro) · 27 canciones
   1. Bohemian Rhapsody - Remastered 2011 — Queen
   2. Mediterráneo — Joan Manuel Serrat
   ...
```

Añade `--json` para obtener `{ id, name, owner, tracks: [{ id, name, artists }] }`.

### 🃏 `cards` — generar los cartones en PDF

```bash
uv run bingo-musical cards "https://open.spotify.com/playlist/<id>" --cards 20 --rows 3 --cols 4
```

```text
PDF generado: /…/bingo-musical/output/bingo-clasicos-de-la-fiesta-de-verano.pdf
Lista: Clásicos de la Fiesta de Verano (27 canciones)
Cartones: 20 de 3×4 · 21 páginas
Semilla: 482913
```

| Opción | Por defecto | Descripción |
|---|---|---|
| `--cards N` | `10` | Número de cartones (uno por página). |
| `--rows N` | `3` | Filas de cada cartón. |
| `--cols N` | `4` | Columnas de cada cartón. |
| `--seed N` | aleatoria | Semilla para regenerar los mismos cartones. |
| `--output RUTA` | `output/bingo-<lista>.pdf` | Dónde guardar el PDF. |
| `--no-control-sheet` | — | No añadir la hoja de control al final. |
| `--full-titles` | — | Mantener coletillas como `(feat. …)` o `- Remastered 2011`. |

> [!TIP]
> **¿Cuántas canciones necesito?** Como mínimo `filas × columnas`. Para que los cartones sean variados y no cante bingo medio salón a la vez, usa al menos **el doble** de canciones que casillas (un cartón 3×4 → 24+ canciones). Si hay pocas, el comando te avisa.

> [!NOTE]
> **¿Se ha estropeado un cartón?** Vuelve a lanzar el comando con la misma lista, filas, columnas y `--seed` que aparecen en el pie del PDF y obtendrás exactamente los mismos cartones (siempre que la lista no haya cambiado).

---

## 🤖 Uso con Claude Code

Abre Claude Code en la carpeta del proyecto y pídelo con tus palabras. Claude elegirá la skill adecuada y ejecutará el comando por ti.

| Skill | Cuándo se activa | Ejemplo de petición |
|---|---|---|
| **`spotify-playlist`** | Quieres ver o exportar las canciones de una lista. | *"¿Qué canciones tiene esta lista? https://open.spotify.com/playlist/…"* |
| **`bingo-cards`** | Quieres crear o reimprimir cartones. | *"Hazme 25 cartones de 4×5 con esta lista y sin hoja de control"* |

También puedes invocarlas directamente:

```text
/bingo-cards https://open.spotify.com/playlist/<id> 30 cartones de 3x3
/spotify-playlist https://open.spotify.com/playlist/<id>
```

Claude te devolverá la ruta del PDF y la semilla usada.

---

## 🏗️ Arquitectura

```mermaid
flowchart LR
    user(["👤 Usuario"])
    skills["🤖 Skills Claude Code<br/><code>spotify-playlist</code><br/><code>bingo-cards</code>"]
    cli["⌨️ cli.py<br/><code>bingo-musical songs | cards</code>"]
    spotify["🎧 spotify.py<br/>SpotifyClient<br/>parse_playlist_id · clean_title"]
    auth["🔑 auth.py<br/>get_user_token<br/>OAuth PKCE"]
    browser(["🌐 Navegador<br/>127.0.0.1:8888/callback"])
    cache[/"~/.cache/bingo-musical/token.json"/]
    cards["🃏 cards.py<br/>generate_cards(seed)"]
    pdf["🖨️ pdf.py<br/>render_pdf · layout_cell"]
    api[("Spotify Web API")]
    out[/"📄 output/bingo-&lt;lista&gt;.pdf"/]

    user -->|lenguaje natural| skills
    user -->|terminal| cli
    skills -->|uv run| cli
    cli --> spotify
    spotify <-->|Client Credentials o token de usuario<br/>paginación · reintentos| api
    spotify -->|401/403| auth
    auth <-->|login la 1ª vez| browser
    auth <--> cache
    spotify -->|Playlist + Tracks| cards
    cards -->|Cards| pdf
    spotify -. clean_title .-> pdf
    pdf --> out
```

```mermaid
sequenceDiagram
    autonumber
    participant U as Usuario
    participant C as cli.py
    participant S as spotify.py
    participant K as auth.py
    participant A as Spotify API
    participant G as cards.py
    participant P as pdf.py

    U->>C: bingo-musical cards URL --cards 20 --rows 3 --cols 4
    C->>S: fetch_playlist(URL)
    S->>A: POST /api/token (client credentials)
    S->>A: GET /playlists/{id}
    S->>A: GET /playlists/{id}/items
    A-->>S: 401 (hace falta sesión de usuario)
    S->>K: get_user_token()
    alt token en caché válido o renovable
        K-->>S: access token
    else sin caché
        K->>U: abre el navegador (login + permisos)
        U-->>K: redirección a 127.0.0.1:8888/callback con código
        K->>A: POST /api/token (authorization_code + code_verifier)
        K-->>S: access token (se guarda en caché)
    end
    loop páginas de 100
        S->>A: GET /playlists/{id}/items (token de usuario)
    end
    S-->>C: Playlist (sin duplicados ni podcasts)
    C->>G: generate_cards(tracks, 20, 3, 4, seed)
    G-->>C: 20 cartones únicos
    C->>P: render_pdf(playlist, cards, seed)
    P-->>U: PDF + semilla
```

| Módulo | Responsabilidad |
|---|---|
| `spotify.py` | Token Client Credentials, paso automático a token de usuario ante `401`/`403`, paginación, reintentos ante `429`, filtrado de episodios y pistas locales, deduplicado y limpieza de títulos. |
| `auth.py` | Inicio de sesión OAuth Authorization Code + PKCE: abre el navegador, recibe el código en un servidor local (`127.0.0.1:8888`), y guarda y renueva el token en `~/.cache/bingo-musical/token.json`. |
| `cards.py` | Lógica pura: reparte canciones al azar con semilla, garantiza cartones distintos y valida que haya suficientes canciones. |
| `pdf.py` | Maquetación con reportlab: rejilla, ajuste automático del tamaño de letra, fuente TTF con tildes y hoja de control paginada. |
| `cli.py` | Punto de entrada `bingo-musical` y mensajes de error legibles. |

---

## 📁 Estructura del proyecto

```text
bingo-musical/
├── 📄 pyproject.toml            # dependencias y entrypoint `bingo-musical`
├── 🔐 .env.example              # plantilla de credenciales de Spotify
├── 📘 CLAUDE.md                 # guía para Claude Code
├── 🤖 .claude/skills/
│   ├── spotify-playlist/SKILL.md
│   └── bingo-cards/SKILL.md
├── 🐍 src/bingo_musical/
│   ├── cli.py                   # comandos songs / cards
│   ├── spotify.py               # cliente de la API de Spotify
│   ├── auth.py                  # inicio de sesión OAuth PKCE y caché del token
│   ├── cards.py                 # generación de cartones
│   └── pdf.py                   # render del PDF
├── 🧪 tests/
│   ├── test_spotify.py          # API simulada con httpx.MockTransport
│   ├── test_cards.py
│   └── test_pdf.py
├── 🖼️ docs/                     # capturas del README
└── 📂 output/                   # PDFs generados (ignorado en git)
```

---

## 🧪 Tests

```bash
uv run pytest                                              # todos
uv run pytest tests/test_pdf.py                            # un fichero
uv run pytest tests/test_cards.py::test_same_seed_same_cards   # un test
```

Los tests no llaman a Spotify: las respuestas de la API se simulan.

---

## 🩺 Problemas frecuentes

| Mensaje | Causa y solución |
|---|---|
| `Faltan credenciales de Spotify` | No existe `.env` o está vacío. Copia `.env.example` y rellena las dos variables. |
| `No se pudo obtener el token (400/401)` | Client ID o Secret incorrectos. Cópialos de nuevo desde **Settings** de la app. |
| `Spotify no encuentra la lista` (404) | La URL es incorrecta o la lista es editorial/algorítmica de Spotify (*Top 50*, *Descubrimiento semanal*…), que las apps nuevas no pueden leer. **Solución:** copia sus canciones a una lista tuya. |
| `Spotify ha denegado el acceso a la lista` (403) | Tras iniciar sesión, tu cuenta no puede leer esa lista (privada de otra persona) o no está dada de alta en **User Management** de la app. |
| `No se pudo completar el login en Spotify` | Cancelaste los permisos, pasaron los 3 minutos o la Redirect URI de la app no es exactamente `http://127.0.0.1:8888/callback`. Vuelve a lanzar el comando. |
| `Address already in use` | Otro programa ocupa el puerto `8888`. Ciérralo y repite. |
| Entra con la cuenta equivocada | Borra `~/.cache/bingo-musical/token.json` y vuelve a lanzar el comando. |
| `La lista tiene X canciones y un cartón … necesita Y` | Reduce filas/columnas o usa una lista más larga. |
| Caracteres que no se ven en el PDF | La fuente del sistema (Arial/DejaVu) no incluye ese alfabeto o emoji. |

---

<div align="center">

Hecho con 🎶 para fiestas, bodas, cumpleaños y cenas de empresa.

</div>
