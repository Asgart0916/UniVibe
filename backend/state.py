import json
import threading
from datetime import date
from pathlib import Path

_STATE_DIR = Path.home() / ".univibe"
_STATE_FILE = _STATE_DIR / "state.json"

# WARNING: client_id and client_secret are stored in plaintext at _STATE_FILE.
# This is acceptable for a local single-user tool where the user controls their
# own machine. Do not deploy this backend on a shared or public server.
_state_lock = threading.Lock()


def _load_unsafe() -> dict:
    """Read state from disk. Caller must hold _state_lock."""
    if not _STATE_FILE.exists():
        return {}
    try:
        return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_unsafe(data: dict) -> None:
    """Write state to disk. Caller must hold _state_lock."""
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def get_config() -> dict:
    with _state_lock:
        return _load_unsafe().get("_config", {})


def save_config(client_id: str, client_secret: str) -> None:
    with _state_lock:
        data = _load_unsafe()
        data["_config"] = {"client_id": client_id, "client_secret": client_secret}
        _save_unsafe(data)


def get_artist_state(artist_id: str) -> dict:
    """Returns {last_fetched_at, tracks, artist_name} or {}."""
    with _state_lock:
        return _load_unsafe().get(artist_id, {})


def save_artist_tracks(artist_id: str, artist_name: str, tracks: list[dict]) -> None:
    with _state_lock:
        data = _load_unsafe()
        data[artist_id] = {
            "artist_name": artist_name,
            "last_fetched_at": date.today().isoformat(),
            "tracks": tracks,
        }
        _save_unsafe(data)
