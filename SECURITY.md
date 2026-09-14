# Política de seguridad

## Versiones con soporte

Solo se da soporte a la última versión de la rama `main`.

## Cómo informar de una vulnerabilidad

**No abras un issue público.** Usa el aviso privado de GitHub:

1. Ve a la pestaña [Security](https://github.com/pedro-poveda/bingo-musical/security) del repositorio.
2. Pulsa **Report a vulnerability** y describe el problema, cómo reproducirlo y su posible impacto.

Recibirás respuesta en un plazo aproximado de 7 días. Es un proyecto personal mantenido en ratos libres, así que te agradezco la paciencia. Una vez corregido, se publicará el aviso y se reconocerá tu aportación si lo deseas.

## Alcance

Especialmente interesan los problemas en:

- **`auth.py`:** servidor local de callback OAuth (`127.0.0.1:8888`), validación del `state`, PKCE y la caché del token en `~/.cache/bingo-musical/token.json`.
- **Manejo de credenciales:** lectura de `.env` y posibles fugas de Client Secret o tokens en mensajes, logs o PDF.
- **Skills de Claude Code** (`.claude/skills/`): inyección de comandos o de instrucciones a partir de URLs, nombres de listas o títulos de canciones.

Quedan fuera del alcance los fallos de la propia API de Spotify y las limitaciones de las apps de Spotify en modo desarrollo.
