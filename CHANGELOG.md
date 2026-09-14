# Registro de cambios

Todos los cambios relevantes del proyecto se documentan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

### Añadido

- Licencia MIT, guía de contribución, código de conducta y política de seguridad.
- Plantillas de issues y pull requests, CODEOWNERS y Dependabot.
- Integración continua con GitHub Actions (ruff y pytest en Linux y macOS).
- Linter y formateador `ruff`.

## [0.1.0] - 2026-09-13

### Añadido

- Comando `songs`: canciones de una lista de Spotify, sin duplicados, episodios ni pistas locales, con salida opcional en JSON.
- Comando `cards`: cartones de bingo en PDF A4 apaisado en blanco y negro, con número de cartones, filas y columnas configurables y semilla reproducible.
- Hoja de control en un PDF aparte y carpetas de salida por lista y fecha.
- Inicio de sesión OAuth Authorization Code + PKCE cuando Client Credentials no basta para leer las canciones.
- Skills de Claude Code `spotify-playlist` y `bingo-cards`.

### Seguridad

- Permisos `600` para la caché del token, validación del `state` OAuth y endurecimiento de las skills frente a datos no fiables.

[Sin publicar]: https://github.com/pedro-poveda/bingo-musical/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pedro-poveda/bingo-musical/releases/tag/v0.1.0
