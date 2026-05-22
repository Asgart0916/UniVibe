import time
from typing import Callable
import httpx

ACCOUNTS_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

_token_cache: dict = {}


def get_token(client_id: str, client_secret: str) -> str:
    now = time.time()
    if _token_cache.get("expires_at", 0) > now + 60:
        return _token_cache["access_token"]
    resp = httpx.post(
        ACCOUNTS_URL,
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data["expires_in"]
    return data["access_token"]


def get_artist(token: str, artist_id: str) -> dict:
    resp = httpx.get(
        f"{API_BASE}/artists/{artist_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    a = resp.json()
    return {
        "id": a["id"],
        "name": a["name"],
        "image": a["images"][0]["url"] if a.get("images") else None,
    }


def search_artist(token: str, query: str) -> list[dict]:
    # Spotify Development Mode no longer returns followers/popularity in artist objects
    resp = httpx.get(
        f"{API_BASE}/search",
        params={"q": query, "type": "artist", "limit": 5},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return [
        {
            "id": a["id"],
            "name": a["name"],
            "image": a["images"][0]["url"] if a.get("images") else None,
        }
        for a in resp.json()["artists"]["items"]
        if a
    ]


def _normalize_date(d: str) -> str:
    """Pad year-only or year-month dates to YYYY-MM-DD for consistent comparison."""
    parts = d.split("-")
    if len(parts) == 1:
        return f"{d}-01-01"
    if len(parts) == 2:
        return f"{d}-01"
    return d


_REQUEST_INTERVAL = 0.2  # proactive throttle: ~5 req/s within 30s window


def _get(token: str, url: str, params: dict | None = None) -> httpx.Response:
    """GET with proactive throttle + automatic 429 retry (Retry-After)."""
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(8):
        resp = httpx.get(url, params=params, headers=headers, timeout=20)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            if wait > 300:
                raise RuntimeError(f"Spotify rate limit 過長（{wait}s / {wait//3600:.1f}h）— 請建立新的 Spotify App 或等待後再試")
            time.sleep(wait)
            continue  # params unchanged — retry with same arguments
        time.sleep(_REQUEST_INTERVAL)
        return resp
    return resp


def _paginate(token: str, url: str, params: dict) -> list[dict]:
    items: list[dict] = []
    while url:
        resp = _get(token, url, params)
        resp.raise_for_status()
        data = resp.json()
        items.extend(data["items"])
        url = data.get("next")
        params = {}  # next URL already encodes all params
    return items


def _batch_full_tracks(token: str, track_ids: list[str]) -> dict[str, dict]:
    """Fetch full track objects (includes ISRC). Returns {} on any API error."""
    result: dict[str, dict] = {}
    for i in range(0, len(track_ids), 50):
        batch = track_ids[i : i + 50]
        resp = _get(token, f"{API_BASE}/tracks", {"ids": ",".join(batch)})
        if not resp.is_success:
            return {}  # ISRC unavailable in this API tier — degrade gracefully
        for tr in resp.json().get("tracks", []):
            if tr:
                result[tr["id"]] = tr
    return result


def get_all_tracks(
    token: str,
    artist_id: str,
    since_date: str | None = None,
    on_progress: Callable | None = None,
) -> list[dict]:
    """
    Fetch all tracks for an artist across albums, singles, and compilations.
    since_date: ISO date (YYYY-MM-DD). When set, skips albums released before this date.
    on_progress: optional callback(dict) called after each album is processed.
    """
    albums: list[dict] = []
    url = f"{API_BASE}/artists/{artist_id}/albums"
    params: dict = {"include_groups": "album,single,compilation", "limit": 10}
    while url:
        resp = _get(token, url, params)
        resp.raise_for_status()
        data = resp.json()
        albums.extend(data["items"])
        url = data.get("next")
        params = {}
        if on_progress:
            on_progress({"phase": "listing", "albums_found": len(albums)})

    if since_date:
        albums = [
            a for a in albums
            if _normalize_date(a.get("release_date", "0000")) >= since_date
        ]

    total = len(albums)
    if on_progress:
        on_progress({"phase": "albums", "albums_done": 0, "albums_total": total, "tracks": 0})

    raw: list[dict] = []
    for i, album in enumerate(albums):
        tracks = _paginate(
            token, f"{API_BASE}/albums/{album['id']}/tracks", {"limit": 50}
        )
        release = _normalize_date(album.get("release_date", ""))
        for t in tracks:
            raw.append({
                "_id": t["id"],
                "track_name": t["name"],
                "album_name": album["name"],
                "release_date": release,
                "duration_ms": t["duration_ms"],
                "spotify_url": t["external_urls"].get("spotify", ""),
            })
        if on_progress:
            on_progress({"albums_done": i + 1, "albums_total": total, "tracks": len(raw)})

    if not raw:
        return []

    if on_progress:
        on_progress({"albums_done": total, "albums_total": total, "tracks": len(raw), "phase": "isrc"})

    full = _batch_full_tracks(token, [t["_id"] for t in raw])

    result = []
    for t in raw:
        ft = full.get(t["_id"], {})
        result.append({
            "track_name": t["track_name"],
            "artist_name": ", ".join(a["name"] for a in ft.get("artists", [])),
            "album_name": t["album_name"],
            "release_date": t["release_date"],
            "duration_ms": t["duration_ms"],
            "isrc": ft.get("external_ids", {}).get("isrc", ""),
            "spotify_url": t["spotify_url"],
        })

    return result
