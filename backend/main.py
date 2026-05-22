import io
import sys
import threading
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from dedup import deduplicate, to_csv
from spotify import get_all_tracks, get_artist, get_token, search_artist
from state import get_artist_state, get_config, save_artist_tracks, save_config

app = FastAPI(title="UniVibe")

# In-memory progress state; keyed by artist_id
_progress: dict[str, dict] = {}
_progress_lock = threading.Lock()


def _set_progress(artist_id: str, data: dict) -> None:
    with _progress_lock:
        _progress[artist_id] = {**_progress.get(artist_id, {}), **data}


def _frontend() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))
    return base / "frontend" / "index.html"


def _token() -> str:
    cfg = get_config()
    if not cfg:
        raise HTTPException(status_code=401, detail="Spotify 尚未設定")
    try:
        return get_token(cfg["client_id"], cfg["client_secret"])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Spotify 憑證無效：{e}")


def _csv_response(tracks: list[dict], filename: str, new_count: int | None = None) -> StreamingResponse:
    csv_text = to_csv(tracks)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Track-Count": str(len(tracks)),
        "Access-Control-Expose-Headers": "X-Track-Count, X-New-Count",
    }
    if new_count is not None:
        headers["X-New-Count"] = str(new_count)
        headers["Access-Control-Expose-Headers"] += ", X-New-Count"
    return StreamingResponse(
        io.BytesIO(csv_text.encode("utf-8-sig")),
        media_type="text/csv",
        headers=headers,
    )


class ConfigBody(BaseModel):
    client_id: str
    client_secret: str


class ArtistBody(BaseModel):
    artist_id: str
    artist_name: str


@app.get("/", response_class=HTMLResponse)
def index():
    return _frontend().read_text(encoding="utf-8")


@app.get("/config/status")
def config_status():
    return {"configured": bool(get_config())}


@app.post("/config")
def set_config(body: ConfigBody):
    try:
        get_token(body.client_id, body.client_secret)
    except Exception:
        raise HTTPException(status_code=400, detail="Spotify 憑證無效，請確認 Client ID 與 Secret")
    save_config(body.client_id, body.client_secret)
    return {"ok": True}


@app.get("/search")
def search(q: Annotated[str, Query(min_length=1)]):
    try:
        return search_artist(_token(), q)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Spotify 搜尋失敗：{e}")


@app.get("/resolve/{artist_id}")
def resolve(artist_id: str):
    try:
        return get_artist(_token(), artist_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="找不到該藝人 ID")


@app.get("/fetch-progress/{artist_id}")
def fetch_progress(artist_id: str):
    with _progress_lock:
        return _progress.get(artist_id, {})


@app.post("/fetch")
def fetch(body: ArtistBody):
    _set_progress(body.artist_id, {"albums_done": 0, "albums_total": 0, "tracks": 0, "phase": "albums"})
    try:
        tracks = get_all_tracks(
            _token(), body.artist_id,
            on_progress=lambda p: _set_progress(body.artist_id, p),
        )
        deduped = deduplicate(tracks)
        save_artist_tracks(body.artist_id, body.artist_name, deduped)
        _set_progress(body.artist_id, {"phase": "done"})
        return _csv_response(deduped, f"{body.artist_name}_all_tracks.csv")
    except HTTPException:
        raise
    except Exception as e:
        _set_progress(body.artist_id, {"phase": "error", "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/update")
def update(body: ArtistBody):
    state = get_artist_state(body.artist_id)
    stored: list[dict] = state.get("tracks", [])
    since: str | None = state.get("last_fetched_at")

    _set_progress(body.artist_id, {"albums_done": 0, "albums_total": 0, "tracks": 0, "phase": "albums"})
    try:
        new_tracks = get_all_tracks(
            _token(), body.artist_id, since_date=since,
            on_progress=lambda p: _set_progress(body.artist_id, p),
        )
        merged = deduplicate(stored + new_tracks)
        save_artist_tracks(body.artist_id, body.artist_name, merged)
        _set_progress(body.artist_id, {"phase": "done"})
        return _csv_response(merged, f"{body.artist_name}_all_tracks.csv", new_count=len(new_tracks))
    except HTTPException:
        raise
    except Exception as e:
        _set_progress(body.artist_id, {"phase": "error", "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/artist/{artist_id}/status")
def artist_status(artist_id: str):
    state = get_artist_state(artist_id)
    return {
        "last_fetched_at": state.get("last_fetched_at"),
        "track_count": len(state.get("tracks", [])),
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
