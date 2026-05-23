import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from unittest.mock import MagicMock, patch
import pytest
import spotify


def _mock_resp(status: int, body: dict | None = None, retry_after: str | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.is_success = (200 <= status < 300)
    r.json.return_value = body or {}
    r.headers = {}
    if retry_after is not None:
        r.headers["Retry-After"] = retry_after
    r.raise_for_status = MagicMock()
    if status >= 400:
        r.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return r


# ── _get: rate-limit behaviour ─────────────────────────────────────────────────

def test_get_retries_on_429_with_short_retry_after():
    ok = _mock_resp(200, {"items": [], "next": None})
    rate_limited = _mock_resp(429, retry_after="2")

    with patch("httpx.get", side_effect=[rate_limited, ok]) as mock_get:
        with patch("time.sleep"):
            resp = spotify._get("tok", "http://example.com")

    assert mock_get.call_count == 2
    assert resp.status_code == 200


def test_get_aborts_on_429_with_long_retry_after():
    rate_limited = _mock_resp(429, retry_after=str(spotify._RATE_LIMIT_ABORT_SECS + 1))

    with patch("httpx.get", return_value=rate_limited):
        with patch("time.sleep"):
            with pytest.raises(RuntimeError, match="rate limit"):
                spotify._get("tok", "http://example.com")


def test_get_retries_at_exact_threshold():
    # wait == _RATE_LIMIT_ABORT_SECS: condition is >, so exactly 300 still retries
    rate_limited = _mock_resp(429, retry_after=str(spotify._RATE_LIMIT_ABORT_SECS))
    ok = _mock_resp(200)

    with patch("httpx.get", side_effect=[rate_limited, ok]):
        with patch("time.sleep"):
            resp = spotify._get("tok", "http://example.com")

    assert resp.status_code == 200


# ── _batch_full_tracks: graceful degrade ───────────────────────────────────────

def test_batch_full_tracks_returns_empty_on_http_error():
    bad = _mock_resp(403)

    with patch("spotify._get", return_value=bad):
        result = spotify._batch_full_tracks("tok", ["id1", "id2"])

    assert result == {}


def test_batch_full_tracks_returns_empty_on_success_but_empty_tracks():
    ok = _mock_resp(200, {"tracks": []})

    with patch("spotify._get", return_value=ok):
        result = spotify._batch_full_tracks("tok", ["id1"])

    assert result == {}


def test_batch_full_tracks_maps_by_id():
    track = {"id": "t1", "external_ids": {"isrc": "ABC123"}, "artists": []}
    ok = _mock_resp(200, {"tracks": [track]})

    with patch("spotify._get", return_value=ok):
        result = spotify._batch_full_tracks("tok", ["t1"])

    assert "t1" in result
    assert result["t1"]["external_ids"]["isrc"] == "ABC123"


# ── get_all_tracks: since_date filtering + on_progress ─────────────────────────

def _album(aid: str, release: str) -> dict:
    return {"id": aid, "name": f"Album {aid}", "release_date": release}


def _album_page(albums: list[dict]) -> dict:
    return {"items": albums, "next": None}


def _tracks_page(tids: list[str]) -> dict:
    return {
        "items": [
            {
                "id": tid,
                "name": f"Track {tid}",
                "duration_ms": 200000,
                "external_urls": {"spotify": f"https://open.spotify.com/track/{tid}"},
            }
            for tid in tids
        ],
        "next": None,
    }


def test_get_all_tracks_filters_by_since_date():
    old_album = _album("a_old", "2020-01-01")
    new_album = _album("a_new", "2024-06-01")

    albums_resp = _mock_resp(200, _album_page([old_album, new_album]))
    tracks_resp = _mock_resp(200, _tracks_page(["t1"]))

    with patch("spotify._get", side_effect=[albums_resp, tracks_resp]):
        with patch("spotify._batch_full_tracks", return_value={}):
            result = spotify.get_all_tracks("tok", "artist1", since_date="2023-01-01")

    # Only new_album passes the filter; old_album is excluded
    assert len(result) == 1


def test_get_all_tracks_on_progress_fires_listing_phase():
    albums_resp = _mock_resp(200, _album_page([_album("a1", "2023-01-01")]))
    tracks_resp = _mock_resp(200, _tracks_page(["t1"]))
    progress_calls: list[dict] = []

    with patch("spotify._get", side_effect=[albums_resp, tracks_resp]):
        with patch("spotify._batch_full_tracks", return_value={}):
            spotify.get_all_tracks("tok", "artist1", on_progress=progress_calls.append)

    phases = [c.get("phase") for c in progress_calls if "phase" in c]
    assert "listing" in phases
    assert "albums" in phases


def test_get_all_tracks_returns_empty_for_no_albums():
    empty_resp = _mock_resp(200, _album_page([]))

    with patch("spotify._get", return_value=empty_resp):
        result = spotify.get_all_tracks("tok", "artist1")

    assert result == []
