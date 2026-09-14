# Cómo contribuir

¡Gracias por querer mejorar Bingo Musical! 🎵 Es un proyecto pequeño y cualquier ayuda es bienvenida: avisar de errores, proponer ideas, mejorar la documentación o enviar código.

Al participar aceptas el [código de conducta](CODE_OF_CONDUCT.md).

## Antes de empezar

- **Errores e ideas:** abre un [issue](https://github.com/pedro-poveda/bingo-musical/issues/new/choose) con la plantilla que corresponda.
- **Cambios grandes** (nuevos comandos, cambios en el formato del PDF, nuevas dependencias): abre antes un issue para comentarlo y no trabajar en balde.
- **Vulnerabilidades:** no abras un issue público; sigue la [política de seguridad](SECURITY.md).

## Preparar el entorno

1. Instala [uv](https://docs.astral.sh/uv/).
2. Haz un fork del repositorio y clónalo.
3. Instala las dependencias (incluidas las de desarrollo):

   ```bash
   uv sync
   ```

4. Para probar contra Spotify de verdad necesitas **tu propia app de Spotify** y un `.env`: sigue la [puesta en marcha del README](README.md#-puesta-en-marcha). Para ejecutar los tests no hace falta.

## Flujo de trabajo

1. Crea una rama desde `main` con un nombre descriptivo: `git switch -c arregla-titulos-largos`.
2. Haz tus cambios, con tests si cambias comportamiento.
3. Comprueba que todo pasa, igual que en la CI:

   ```bash
   uv run ruff check .
   uv run ruff format --check .   # o `uv run ruff format .` para formatear
   uv run pytest
   ```

4. Abre un pull request contra `main` y rellena la plantilla. La CI debe estar en verde y hace falta una revisión para mergear.

## Convenciones

- **Idioma:** código, mensajes de la CLI, commits y documentación en **español**.
- **Estilo:** el que marca `ruff` (configurado en `pyproject.toml`).
- **Tests:** nunca llaman a la API real de Spotify. Simula las respuestas con `httpx.MockTransport`, como en `tests/test_spotify.py`.
- **Commits:** pequeños y con un mensaje que explique qué cambia y por qué.
- **Documentación:** si cambias la CLI o su comportamiento, actualiza `README.md`, `CLAUDE.md` y, si aplica, las skills de `.claude/skills/`. Añade una línea en `CHANGELOG.md` bajo *Sin publicar*.

## Qué no subir nunca

- El fichero `.env` ni ningún Client ID/Secret o token de Spotify.
- `~/.cache/bingo-musical/token.json`.
- PDF generados en `output/` ni URLs de listas privadas.
