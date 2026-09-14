import stat
import threading

import httpx
import pytest

from bingo_musical import auth

STATE = "estado-esperado"


@pytest.fixture
def callback():
    """Servidor de callback en un puerto libre esperando en segundo plano."""
    server = auth._CallbackServer(("127.0.0.1", 0), STATE)
    result = {}
    thread = threading.Thread(target=lambda: result.update(value=auth._wait_for_callback(server, timeout=5)))
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    yield base, result, thread
    thread.join(timeout=10)
    server.server_close()


def test_callback_accepts_valid_state(callback):
    base, result, thread = callback
    resp = httpx.get(f"{base}/callback", params={"code": "abc", "state": STATE})
    thread.join(timeout=5)
    assert resp.status_code == 200
    assert resp.headers["Cache-Control"] == "no-store"
    assert result["value"] == ("abc", None)


def test_callback_ignores_wrong_state_and_other_paths(callback):
    base, result, thread = callback
    assert httpx.get(f"{base}/callback", params={"code": "atacante", "state": "otro"}).status_code == 400
    assert httpx.get(f"{base}/callback", params={"code": "atacante"}).status_code == 400
    assert httpx.get(f"{base}/callback", params={"error": "x", "state": "ñ"}).status_code == 400
    assert httpx.get(f"{base}/favicon.ico").status_code == 404
    assert thread.is_alive()  # sigue esperando el callback bueno
    httpx.get(f"{base}/callback", params={"code": "bueno", "state": STATE})
    thread.join(timeout=5)
    assert result["value"] == ("bueno", None)


def test_callback_reports_error_with_valid_state(callback):
    base, result, thread = callback
    httpx.get(f"{base}/callback", params={"error": "access_denied", "state": STATE})
    thread.join(timeout=5)
    assert result["value"] == (None, "access_denied")


def test_callback_timeout():
    server = auth._CallbackServer(("127.0.0.1", 0), STATE)
    try:
        assert auth._wait_for_callback(server, timeout=0.2) == (None, "tiempo de espera agotado")
    finally:
        server.server_close()


def test_save_cache_restricts_permissions(tmp_path, monkeypatch):
    path = tmp_path / "cache" / "token.json"
    monkeypatch.setattr(auth, "CACHE_PATH", path)
    path.parent.mkdir(mode=0o755)
    path.write_text("{}")
    path.chmod(0o644)  # caché creada por una versión anterior

    auth._save_cache({"access_token": "t", "refresh_token": "r", "expires_at": 1})

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert auth._load_cache() == {"access_token": "t", "refresh_token": "r", "expires_at": 1}
