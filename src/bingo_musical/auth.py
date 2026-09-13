"""Login de usuario con Spotify (Authorization Code + PKCE).

Solo se usa cuando Client Credentials no basta para leer el contenido de una
lista: Spotify exige una sesión de usuario para listar las canciones de
playlists (ver `SpotifyClient._get` en spotify.py). El flujo:

1. Se abre el navegador en la pantalla de login/autorización de Spotify.
2. Un servidor HTTP local (Redirect URI registrada: http://127.0.0.1:8888/callback)
   recibe el código de autorización.
3. Se intercambia el código por un access token + refresh token (PKCE, sin
   client secret) y se cachean en ~/.cache/bingo-musical/token.json para no
   pedir login en cada ejecución.
"""

from __future__ import annotations

import base64
import hashlib
import json
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
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(data))


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (nombre impuesto por BaseHTTPRequestHandler)
        query = parse_qs(urlparse(self.path).query)
        self.server.auth_code = query.get("code", [None])[0]  # type: ignore[attr-defined]
        self.server.auth_error = query.get("error", [None])[0]  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if self.server.auth_code:  # type: ignore[attr-defined]
            body = "<p>Sesión iniciada con Spotify. Ya puedes cerrar esta pestaña.</p>"
        else:
            body = "<p>No se pudo iniciar sesión en Spotify.</p>"
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:  # silencia el log por stderr
        pass


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
    server = HTTPServer(("127.0.0.1", 8888), _CallbackHandler)
    server.auth_code = None  # type: ignore[attr-defined]
    server.auth_error = None  # type: ignore[attr-defined]
    print("Spotify requiere que inicies sesión para leer las canciones de esta lista.")
    print("Abriendo el navegador...")
    webbrowser.open(f"{AUTHORIZE_URL}?{urlencode(params)}")
    server.timeout = 180
    server.handle_request()
    server.server_close()
    code = server.auth_code  # type: ignore[attr-defined]
    error = server.auth_error  # type: ignore[attr-defined]
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
