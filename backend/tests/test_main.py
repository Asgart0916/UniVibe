import csv
import io
import sys
import pathlib
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

import main as main_mod
from main import app

client = TestClient(app, raise_server_exceptions=False)


# ── helpers ────────────────────────────────────────────────────────────────────

def _track(name: str = "Song", date: str = "2023-01-01") -> dict:
    return {
        "track_name": name,
        "artist_name": "Artist",
        "album_name": "Album",
        "release_date": date,
        "duration_ms": 200000,
        "isrc": "",
        "spotify_url": "https://open.spotify.com/track/x",
    }


def _parse_csv(response_bytes: bytes) -> list[dict]:
    text = response_bytes.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_progress():
    """Reset in-memory progress dict between tests."""
    main_mod._progress.clear()
    yield
    main_mod._progress.clear()


# ── GET / ──────────────────────────────────────────────────────────────────────

def test_index_returns_html():
    with patch.object(pathlib.Path, "read_text", return_value="<html></html>"):
        resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


# ── /config/status ─────────────────────────────────────────────────────────────

def test_config_status_unconfigured():
    with patch("main.get_config", return_value={}):
        resp = client.get("/config/status")
    assert resp.status_code == 200
    assert resp.json() == {"configured": False}


def test_config_status_configured():
    with patch("main.get_config", return_value={"client_id": "x", "client_secret": "y"}):
        resp = client.get("/config/status")
    assert resp.json() == {"configured": True}


# ── POST /config ───────────────────────────────────────────────────────────────

def test_post_config_success():
    with patch("main.get_token", return_value="tok"), \
         patch("main.save_config") as mock_save:
        resp = client.post("/config", json={"client_id": "id", "client_secret": "sec"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    mock_save.assert_called_once_with("id", "sec")


def test_post_config_invalid_credentials():
    with patch("main.get_token", side_effect=Exception("bad credentials")):
        resp = client.post("/config", json={"client_id": "bad", "client_secret": "bad"})
    assert resp.status_code == 400


# ── GET /search ────────────────────────────────────────────────────────────────

def test_search_returns_artist_list():
    artists = [{"id": "a1", "name": "The Band", "image": None}]
    with patch("main.get_config", return_value={"client_id": "x", "client_secret": "y"}), \
         patch("main.get_token", return_value="tok"), \
         patch("main.search_artist", return_value=artists):
        resp = client.get("/search", params={"q": "band"})
    assert resp.status_code == 200
    assert resp.json() == artists


def test_search_empty_query_returns_422():
    resp = client.get("/search", params={"q": ""})
    assert resp.status_code == 422


def test_search_no_config_returns_401():
    with patch("main.get_config", return_value={}):
        resp = client.get("/search", params={"q": "band"})
    assert resp.status_code == 401


# ── GET /resolve/{artist_id} ───────────────────────────────────────────────────

def test_resolve_returns_artist():
    artist = {"id": "a1", "name": "The Band", "image": None}
    with patch("main.get_config", return_value={"client_id": "x", "client_secret": "y"}), \
         patch("main.get_token", return_value="tok"), \
         patch("main.get_artist", return_value=artist):
        resp = client.get("/resolve/a1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "The Band"


def test_resolve_not_found_returns_404():
    with patch("main.get_config", return_value={"client_id": "x", "client_secret": "y"}), \
         patch("main.get_token", return_value="tok"), \
         patch("main.get_artist", side_effect=Exception("not found")):
        resp = client.get("/resolve/bad_id")
    assert resp.status_code == 404


# ── POST /fetch ────────────────────────────────────────────────────────────────

def test_fetch_returns_csv_with_headers():
    tracks = [_track("Song A"), _track("Song B")]
    with patch("main.get_config", return_value={"client_id": "x", "client_secret": "y"}), \
         patch("main.get_token", return_value="tok"), \
         patch("main.get_all_tracks", return_value=tracks), \
         patch("main.save_artist_tracks"):
        resp = client.post("/fetch", json={"artist_id": "a1", "artist_name": "Artist"})

    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert resp.headers["x-track-count"] == "2"
    rows = _parse_csv(resp.content)
    assert len(rows) == 2
    assert rows[0]["track_name"] in ("Song A", "Song B")


def test_fetch_returns_deduplicated_tracks():
    # Two tracks with the same name — deduplicate keeps one (newest)
    tracks = [_track("Same Song", "2020-01-01"), _track("Same Song", "2023-01-01")]
    with patch("main.get_config", return_value={"client_id": "x", "client_secret": "y"}), \
         patch("main.get_token", return_value="tok"), \
         patch("main.get_all_tracks", return_value=tracks), \
         patch("main.save_artist_tracks"):
        resp = client.post("/fetch", json={"artist_id": "a1", "artist_name": "Artist"})

    assert resp.status_code == 200
    assert resp.headers["x-track-count"] == "1"


def test_fetch_spotify_error_returns_500():
    with patch("main.get_config", return_value={"client_id": "x", "client_secret": "y"}), \
         patch("main.get_token", return_value="tok"), \
         patch("main.get_all_tracks", side_effect=RuntimeError("rate limit")):
        resp = client.post("/fetch", json={"artist_id": "a1", "artist_name": "Artist"})

    assert resp.status_code == 500
    assert "rate limit" in resp.json()["detail"]


def test_fetch_sets_progress_to_done():
    tracks = [_track()]
    with patch("main.get_config", return_value={"client_id": "x", "client_secret": "y"}), \
         patch("main.get_token", return_value="tok"), \
         patch("main.get_all_tracks", return_value=tracks), \
         patch("main.save_artist_tracks"):
        client.post("/fetch", json={"artist_id": "a1", "artist_name": "Artist"})

    progress = client.get("/fetch-progress/a1").json()
    assert progress.get("phase") == "done"


def test_fetch_error_sets_progress_to_error():
    with patch("main.get_config", return_value={"client_id": "x", "client_secret": "y"}), \
         patch("main.get_token", return_value="tok"), \
         patch("main.get_all_tracks", side_effect=RuntimeError("boom")):
        client.post("/fetch", json={"artist_id": "a1", "artist_name": "Artist"})

    progress = client.get("/fetch-progress/a1").json()
    assert progress.get("phase") == "error"
    assert "boom" in progress.get("error", "")


# ── POST /update ───────────────────────────────────────────────────────────────

def test_update_merges_new_with_stored_tracks():
    stored = [_track("Old Song", "2020-01-01")]
    new_tracks = [_track("New Song", "2024-06-01")]
    with patch("main.get_config", return_value={"client_id": "x", "client_secret": "y"}), \
         patch("main.get_token", return_value="tok"), \
         patch("main.get_artist_state", return_value={"tracks": stored, "last_fetched_at": "2023-01-01"}), \
         patch("main.get_all_tracks", return_value=new_tracks), \
         patch("main.save_artist_tracks"):
        resp = client.post("/update", json={"artist_id": "a1", "artist_name": "Artist"})

    assert resp.status_code == 200
    assert resp.headers["x-track-count"] == "2"
    assert resp.headers["x-new-count"] == "1"


def test_update_with_no_existing_state_acts_as_fresh_fetch():
    new_tracks = [_track("Song", "2024-01-01")]
    with patch("main.get_config", return_value={"client_id": "x", "client_secret": "y"}), \
         patch("main.get_token", return_value="tok"), \
         patch("main.get_artist_state", return_value={}), \
         patch("main.get_all_tracks", return_value=new_tracks), \
         patch("main.save_artist_tracks"):
        resp = client.post("/update", json={"artist_id": "a1", "artist_name": "Artist"})

    assert resp.status_code == 200
    assert resp.headers["x-track-count"] == "1"


# ── GET /artist/{id}/status ────────────────────────────────────────────────────

def test_artist_status_with_existing_state():
    stored_tracks = [_track(), _track("B")]
    with patch("main.get_artist_state", return_value={
        "last_fetched_at": "2024-01-15",
        "tracks": stored_tracks,
    }):
        resp = client.get("/artist/a1/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["last_fetched_at"] == "2024-01-15"
    assert data["track_count"] == 2


def test_artist_status_with_no_state():
    with patch("main.get_artist_state", return_value={}):
        resp = client.get("/artist/a1/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["last_fetched_at"] is None
    assert data["track_count"] == 0
