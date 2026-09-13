"""Cliente mínimo de la API de Spotify (Client Credentials) para leer listas."""

from __future__ import annotations

import os
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Callable, Iterator

import httpx
from dotenv import load_dotenv

from .auth import SpotifyAuthError, get_user_token

API_URL = "https://api.spotify.com/v1"
TOKEN_URL = "https://accounts.spotify.com/api/token"

_ID_RE = re.compile(r"^[A-Za-z0-9]{22}$")
_URL_ID_RE = re.compile(r"playlist[/:]([A-Za-z0-9]{22})")

# Sufijos que no aportan nada en un cartón: "(feat. X)", " - Remastered 2011", ...
_PAREN_RE = re.compile(
    r"\s*[\(\[](?:feat\.?|ft\.?|with|con|remaster(?:ed)?|\d{4} remaster(?:ed)?)[^\)\]]*[\)\]]",
    re.IGNORECASE,
)
_DASH_SUFFIX_RE = re.compile(
    r"\s+-\s+[^-]*\b(?:remaster(?:ed)?|version|versión|edit|mix|live|en vivo|directo|"
    r"mono|stereo|single|acoustic|acústica|from|bonus|feat\.?)\b.*$",
    re.IGNORECASE,
)


class SpotifyError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Track:
    id: str
    name: str
    artists: tuple[str, ...]

    @property
    def artist_line(self) -> str:
        return ", ".join(self.artists)


@dataclass
class Playlist:
    id: str
    name: str
    owner: str
    tracks: list[Track]


def parse_playlist_id(value: str) -> str:
    """Extrae el id de una URL, URI (spotify:playlist:...) o id pelado."""
    value = value.strip()
    if _ID_RE.match(value):
        return value
    match = _URL_ID_RE.search(value)
    if match:
        return match.group(1)
    raise SpotifyError(f"No reconozco una lista de Spotify en: {value!r}")


def clean_title(name: str) -> str:
    """Quita coletillas tipo '(feat. X)' o ' - Remastered 2011' del título."""
    cleaned = _DASH_SUFFIX_RE.sub("", _PAREN_RE.sub("", name)).strip()
    return cleaned or name


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


class SpotifyClient:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ):
        load_dotenv()
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise SpotifyError(
                "Faltan credenciales de Spotify. Crea una app en "
                "https://developer.spotify.com/dashboard y define SPOTIFY_CLIENT_ID y "
                "SPOTIFY_CLIENT_SECRET en el fichero .env (ver .env.example)."
            )
        self.max_retries = max_retries
        self._sleep = sleep
        self._http = httpx.Client(transport=transport, timeout=20)
        self._token: str | None = None
        self._auth_mode = "app"  # "app" (Client Credentials) o "user" (login OAuth PKCE)

    def _fetch_token(self) -> None:
        resp = self._http.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
        )
        if resp.status_code != 200:
            raise SpotifyError(
                f"No se pudo obtener el token de Spotify ({resp.status_code}). "
                "Revisa SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET.",
                resp.status_code,
            )
        self._token = resp.json()["access_token"]
        self._auth_mode = "app"

    def _fetch_user_token(self) -> None:
        # Spotify exige una sesión de usuario para listar canciones de playlists
        # (Client Credentials solo sirve para metadatos y búsquedas).
        try:
            self._token = get_user_token(self.client_id)
        except SpotifyAuthError as exc:
            raise SpotifyError(str(exc)) from exc
        self._auth_mode = "user"

    def _get(self, url: str, params: dict | None = None) -> dict:
        if self._token is None:
            self._fetch_token()
        refreshed = False
        switched_user = False
        retries = 0
        while True:
            resp = self._http.get(
                url, params=params, headers={"Authorization": f"Bearer {self._token}"}
            )
            if resp.status_code == 401 and self._auth_mode == "app" and not refreshed:
                refreshed = True
                self._fetch_token()
                continue
            if resp.status_code in (401, 403) and self._auth_mode == "app" and not switched_user:
                switched_user = True
                self._fetch_user_token()
                continue
            if resp.status_code == 429 and retries < self.max_retries:
                retries += 1
                self._sleep(float(resp.headers.get("Retry-After", "1")))
                continue
            if resp.status_code == 404:
                raise SpotifyError(
                    "Spotify no encuentra la lista. Comprueba que la URL es correcta y que "
                    "la lista es pública. Las listas editoriales o algorítmicas de Spotify "
                    "(Top 50, Descubrimiento semanal, ...) no son accesibles desde apps nuevas.",
                    404,
                )
            if resp.status_code == 403:
                raise SpotifyError(
                    "Spotify ha denegado el acceso a la lista (403). Puede ser privada o "
                    "estar restringida para apps en modo desarrollo.",
                    403,
                )
            if resp.status_code >= 400:
                raise SpotifyError(
                    f"Error de la API de Spotify ({resp.status_code}): {resp.text[:200]}",
                    resp.status_code,
                )
            return resp.json()

    def _iter_items(self, playlist_id: str) -> Iterator[dict]:
        params = {"limit": 100, "additional_types": "track"}
        try:
            page = self._get(f"{API_URL}/playlists/{playlist_id}/items", params)
        except SpotifyError as exc:
            if exc.status != 404:
                raise
            # Endpoint antiguo, por si /items no está disponible.
            page = self._get(f"{API_URL}/playlists/{playlist_id}/tracks", params)
        while True:
            yield from page.get("items") or []
            next_url = page.get("next")
            if not next_url:
                return
            page = self._get(next_url)

    def fetch_playlist(self, url_or_id: str) -> Playlist:
        playlist_id = parse_playlist_id(url_or_id)
        meta = self._get(
            f"{API_URL}/playlists/{playlist_id}",
            {"fields": "name,owner(display_name)"},
        )
        tracks: list[Track] = []
        seen: set = set()
        for item in self._iter_items(playlist_id):
            obj = item.get("item") or item.get("track")
            if not obj or obj.get("type", "track") != "track":
                continue
            if item.get("is_local") or obj.get("is_local") or not obj.get("id"):
                continue
            artists = tuple(a["name"] for a in obj.get("artists") or [] if a.get("name"))
            track = Track(id=obj["id"], name=obj.get("name") or "", artists=artists)
            key = (_normalize(clean_title(track.name)), _normalize(artists[0] if artists else ""))
            if track.id in seen or key in seen:
                continue
            seen.update((track.id, key))
            tracks.append(track)
        return Playlist(
            id=playlist_id,
            name=meta.get("name") or "Lista sin nombre",
            owner=(meta.get("owner") or {}).get("display_name") or "",
            tracks=tracks,
        )
