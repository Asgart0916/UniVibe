import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import state


def _patch(monkeypatch, tmp_path):
    """Redirect state storage to a temp directory."""
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(state, "_STATE_DIR", tmp_path)
    monkeypatch.setattr(state, "_STATE_FILE", state_file)


# ── get_config ─────────────────────────────────────────────────────────────────

def test_get_config_returns_empty_when_no_file(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    assert state.get_config() == {}


def test_save_and_get_config_roundtrip(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    state.save_config("my_id", "my_secret")
    cfg = state.get_config()
    assert cfg["client_id"] == "my_id"
    assert cfg["client_secret"] == "my_secret"


def test_save_config_overwrites_previous(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    state.save_config("old_id", "old_secret")
    state.save_config("new_id", "new_secret")
    cfg = state.get_config()
    assert cfg["client_id"] == "new_id"


# ── get_artist_state / save_artist_tracks ──────────────────────────────────────

def test_get_artist_state_returns_empty_for_unknown(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    assert state.get_artist_state("unknown_id") == {}


def test_save_and_get_artist_tracks_roundtrip(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    tracks = [{"track_name": "Song", "release_date": "2023-01-01"}]
    state.save_artist_tracks("artist_1", "Artist One", tracks)
    s = state.get_artist_state("artist_1")
    assert s["artist_name"] == "Artist One"
    assert s["tracks"] == tracks
    assert s["last_fetched_at"]  # non-empty date string


def test_save_artist_tracks_does_not_clobber_config(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    state.save_config("cid", "csec")
    state.save_artist_tracks("a1", "A", [])
    cfg = state.get_config()
    assert cfg["client_id"] == "cid"


def test_multiple_artists_stored_independently(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    state.save_artist_tracks("a1", "Artist A", [{"track_name": "A Song"}])
    state.save_artist_tracks("a2", "Artist B", [{"track_name": "B Song"}])
    assert state.get_artist_state("a1")["artist_name"] == "Artist A"
    assert state.get_artist_state("a2")["artist_name"] == "Artist B"


# ── resilience ─────────────────────────────────────────────────────────────────

def test_corrupted_state_file_returns_empty(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    (tmp_path / "state.json").write_text("not valid json", encoding="utf-8")
    assert state.get_config() == {}
    assert state.get_artist_state("x") == {}


def test_save_creates_directory_if_missing(monkeypatch, tmp_path):
    nested = tmp_path / "deep" / "dir"
    monkeypatch.setattr(state, "_STATE_DIR", nested)
    monkeypatch.setattr(state, "_STATE_FILE", nested / "state.json")
    state.save_config("id", "secret")
    assert (nested / "state.json").exists()
