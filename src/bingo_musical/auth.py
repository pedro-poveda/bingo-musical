"""Login de usuario con Spotify (Authorization Code + PKCE).

Solo se usa cuando Client Credentials no basta para leer el contenido de una
lista: Spotify exige una sesión de usuario para listar las canciones de
playlists (ver `SpotifyClient._get` en spotify.py). El flujo:

1. Se abre el navegador en la pantalla de login/autorización de Spotify.
2. Un servidor HTTP local (Redirect URI registrada: http://127.0.0.1:8888/callback)
   recibe el código de autorización. Se ignoran las peticiones a otras rutas o con
   un `state` distinto del enviado (protección CSRF).
3. Se intercambia el código por un access token + refresh token (PKCE, sin
   client secret) y se cachean en ~/.cache/bingo-musical/token.json (permisos
   600, carpeta 700) para no pedir login en cada ejecución.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
CALLBACK_PATH = "/callback"
LOGIN_TIMEOUT = 180  # segundos para completar el login en el navegador
SCOPE = "playlist-read-private playlist-read-collaborative"
CACHE_PATH = Path.home() / ".cache" / "bingo-musical" / "token.json"


class SpotifyAuthError(Exception):
    pass


def _code_verifier() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode("ascii")


def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _load_cache() -> dict | None:
    if not CACHE_PATH.exists():
        return None
    try:
        return json.loads(CACHE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _save_cache(data: dict) -> None:
    # El refresh token da acceso a las listas privadas: solo lo puede leer el usuario.
    CACHE_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(CACHE_PATH.parent, 0o700)
    fd = os.open(CACHE_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    os.chmod(CACHE_PATH, 0o600)  # corrige cachés creadas por versiones anteriores


class _CallbackServer(HTTPServer):
    """Servidor local que espera el callback OAuth con el `state` esperado."""

    def __init__(self, address: tuple[str, int], expected_state: str):
        super().__init__(address, _CallbackHandler)
        self.expected_state = expected_state
        self.auth_code: str | None = None
        self.auth_error: str | None = None
        self.done = False


class _CallbackHandler(BaseHTTPRequestHandler):
    server: _CallbackServer
    timeout = 10  # que una conexión que no envía nada no bloquee el login

    def do_GET(self) -> None:  # noqa: N802 (nombre impuesto por BaseHTTPRequestHandler)
        parsed = urlparse(self.path)
        if parsed.path != CALLBACK_PATH:
            self._reply(404, "<p>No encontrado.</p>")
            return
        query = parse_qs(parsed.query)
        state = query.get("state", [""])[0]
        if not secrets.compare_digest(state.encode("utf-8"), self.server.expected_state.encode("utf-8")):
            # Petición que no viene de nuestro login (CSRF u otra pestaña): se ignora.
            self._reply(400, "<p>Petición de inicio de sesión no válida.</p>")
            return
        self.server.auth_code = query.get("code", [None])[0]
        self.server.auth_error = query.get("error", [None])[0]
        self.server.done = True
        if self.server.auth_code:
            self._reply(200, "<p>Sesión iniciada con Spotify. Ya puedes cerrar esta pestaña.</p>")
        else:
            self._reply(200, "<p>No se pudo iniciar sesión en Spotify.</p>")

    def _reply(self, status: int, body: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:  # silencia el log por stderr
        pass


def _wait_for_callback(server: _CallbackServer, timeout: float) -> tuple[str | None, str | None]:
    """Atiende peticiones hasta recibir un callback con `state` válido o agotar `timeout`."""
    deadline = time.monotonic() + timeout
    while not server.done:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None, "tiempo de espera agotado"
        server.timeout = remaining
        server.handle_request()
    return server.auth_code, server.auth_error


def _authorize(client_id: str) -> tuple[str, str]:
    """Abre el navegador, espera el callback local y devuelve (código, code_verifier)."""
    verifier = _code_verifier()
    challenge = _code_challenge(verifier)
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "scope": SCOPE,
        "state": state,
    }
    server = _CallbackServer(("127.0.0.1", 8888), state)
    print("Spotify requiere que inicies sesión para leer las canciones de esta lista.")
    print("Abriendo el navegador...")
    webbrowser.open(f"{AUTHORIZE_URL}?{urlencode(params)}")
    try:
        code, error = _wait_for_callback(server, LOGIN_TIMEOUT)
    finally:
        server.server_close()
    if error or not code:
        raise SpotifyAuthError(f"No se pudo completar el login en Spotify ({error or 'sin código'}).")
    return code, verifier


def _refresh(client_id: str, refresh_token: str) -> str | None:
    resp = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        },
    )
    if resp.status_code != 200:
        return None
    data = resp.json()
    _save_cache(
        {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", refresh_token),
            "expires_at": time.time() + data.get("expires_in", 3600),
        }
    )
    return data["access_token"]


def get_user_token(client_id: str) -> str:
    """Devuelve un token de usuario válido, renovando o pidiendo login si hace falta."""
    cached = _load_cache()
    if cached and cached.get("expires_at", 0) > time.time() + 30:
        return cached["access_token"]
    if cached and cached.get("refresh_token"):
        token = _refresh(client_id, cached["refresh_token"])
        if token:
            return token
    code, verifier = _authorize(client_id)
    resp = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "code_verifier": verifier,
        },
    )
    if resp.status_code != 200:
        raise SpotifyAuthError(f"Spotify rechazó el login ({resp.status_code}): {resp.text[:200]}")
    data = resp.json()
    _save_cache(
        {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_at": time.time() + data.get("expires_in", 3600),
        }
    )
    return data["access_token"]
