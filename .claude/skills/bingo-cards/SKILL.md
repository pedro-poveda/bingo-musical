---
name: bingo-cards
description: Genera cartones de bingo musical en PDF (A4 apaisado, blanco y negro) a partir de una lista de Spotify, con número de cartones y filas×columnas configurables. Úsala cuando el usuario quiera crear o imprimir cartones de bingo musical.
---

# Crear cartones de bingo musical

1. Necesitas la URL de la lista. Si el usuario no indica número de cartones, filas o columnas, usa los valores por defecto (10 cartones de 3×4) y díselo.
2. Ejecuta desde la raíz del proyecto:

```bash
uv run bingo-musical cards "<URL>" --cards 10 --rows 3 --cols 4 [--seed 1234] [--output output/mi-bingo.pdf]
```

Opciones:
- `--seed N`: regenera exactamente los mismos cartones (misma lista y mismos parámetros).
- `--no-control-sheet`: omite la hoja de control final (lista alfabética de canciones con casillas para marcar las que suenan).
- `--full-titles`: no recorta coletillas como `(feat. …)` o `- Remastered 2011`.

3. Informa al usuario de la ruta del PDF, el nº de canciones, los cartones generados y la **semilla** (para poder reimprimir los mismos cartones).

## Contenido del PDF

- Una página por cartón: título de la lista y "Cartón nº X" en el encabezado; en cada casilla el título de la canción y debajo, más pequeño, el artista.
- Al final, la hoja de control.

## Errores habituales

- **Menos canciones que casillas**: propón reducir filas/columnas o usar una lista más larga.
- **Aviso de cartones parecidos**: con pocas canciones más que casillas habrá muchos ganadores simultáneos; recomienda ajustar filas/columnas.
- Credenciales o lista inaccesible: ver la skill `spotify-playlist`.
