import httpx
import pytest

from bingo_musical.spotify import SpotifyClient, SpotifyError, clean_title, parse_playlist_id

PID = "37i9dQZF1DXcBWIGoYBM5M"


@pytest.mark.parametrize(
    "value",
    [
        PID,
        f"https://open.spotify.com/playlist/{PID}?si=abc123",
        f"https://open.spotify.com/intl-es/playlist/{PID}",
        f"spotify:playlist:{PID}",
        f"  https://open.spotify.com/embed/playlist/{PID}  ",
    ],
)
def test_parse_playlist_id(value):
    assert parse_playlist_id(value) == PID


def test_parse_playlist_id_invalid():
    with pytest.raises(SpotifyError):
        parse_playlist_id("https://open.spotify.com/album/123")


def test_clean_title():
    assert clean_title("Bohemian Rhapsody - Remastered 2011") == "Bohemian Rhapsody"
    assert clean_title("Despacito (feat. Daddy Yankee)") == "Despacito"
    assert clean_title("Mediterráneo") == "Mediterráneo"


def _track(tid, name, artist="Artista"):
    return {"type": "track", "id": tid, "name": name, "artists": [{"name": artist}]}


def _client(handler):
    return SpotifyClient("id", "secret", transport=httpx.MockTransport(handler), sleep=lambda s: None)


def _token_or(handler):
    def wrapped(request):
        if request.url.host == "accounts.spotify.com":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        return handler(request)

    return wrapped


def test_fetch_playlist_paginates_filters_and_dedupes():
    calls = {"meta_429": 0}

    def handler(request):
        path = request.url.path
        if path == f"/v1/playlists/{PID}":
            if calls["meta_429"] == 0:
                calls["meta_429"] += 1
                return httpx.Response(429, headers={"Retry-After": "0"})
            return httpx.Response(200, json={"name": "Fiesta", "owner": {"display_name": "Pedro"}})
        if path == f"/v1/playlists/{PID}/items":
            if request.url.params.get("offset") == "3":
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {"item": _track("t1", "Uno")},  # id repetido
                            {"item": _track("t4", "Dos - Remastered 2011")},  # misma canción
                            {"item": _track("t5", "Cinco")},
                        ],
                        "next": None,
                    },
                )
            return httpx.Response(
                200,
                json={
                    "items": [
                        {"item": _track("t1", "Uno")},
                        {"item": None},
                        {"item": {"type": "episode", "id": "e1", "name": "Podcast"}},
                        {"is_local": True, "item": _track(None, "Local")},
                        {"item": _track("t2", "Dos")},
                    ],
                    "next": f"https://api.spotify.com/v1/playlists/{PID}/items?offset=3&limit=100",
                },
            )
        return httpx.Response(500)

    playlist = _client(_token_or(handler)).fetch_playlist(f"https://open.spotify.com/playlist/{PID}")
    assert playlist.name == "Fiesta"
    assert playlist.owner == "Pedro"
    assert [t.id for t in playlist.tracks] == ["t1", "t2", "t5"]


def test_fetch_playlist_falls_back_to_tracks_endpoint():
    def handler(request):
        path = request.url.path
        if path == f"/v1/playlists/{PID}":
            return httpx.Response(200, json={"name": "Vieja", "owner": {}})
        if path.endswith("/items"):
            return httpx.Response(404)
        if path.endswith("/tracks"):
            return httpx.Response(200, json={"items": [{"track": _track("t1", "Uno")}], "next": None})
        return httpx.Response(500)

    playlist = _client(_token_or(handler)).fetch_playlist(PID)
    assert [t.name for t in playlist.tracks] == ["Uno"]


def test_refreshes_token_on_401():
    tokens = iter(["old", "new"])

    def handler(request):
        if request.url.host == "accounts.spotify.com":
            return httpx.Response(200, json={"access_token": next(tokens)})
        if request.headers["Authorization"] == "Bearer old":
            return httpx.Response(401)
        if request.url.path == f"/v1/playlists/{PID}":
            return httpx.Response(200, json={"name": "X"})
        return httpx.Response(200, json={"items": [], "next": None})

    assert _client(handler).fetch_playlist(PID).tracks == []


def test_not_found_has_helpful_message():
    client = _client(_token_or(lambda request: httpx.Response(404)))
    with pytest.raises(SpotifyError, match="pública"):
        client.fetch_playlist(PID)


def test_missing_credentials(monkeypatch):
    monkeypatch.setattr("bingo_musical.spotify.load_dotenv", lambda: None)
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    with pytest.raises(SpotifyError, match="credenciales"):
        SpotifyClient()
