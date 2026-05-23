"""
Local mock for Spotify Web API v1.
Activate by setting USE_MOCK = true in frontend/index.html.
All endpoints return minimal fixture data; shape matches real Spotify responses.
"""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/mock/spotify/v1")

# ── Fixture data ──────────────────────────────────────────────────────────────

_ALBUMS = [
    {
        "id": f"mock_album_{i}",
        "name": f"Mock Album {i + 1}",
        "release_date": f"202{i % 4}-{(i % 11) + 1:02d}-01",
        "release_date_precision": "day",
        "album_type": "album",
    }
    for i in range(8)
]

# 3 tracks per album
_ALBUM_TRACKS: dict[str, list] = {
    alb["id"]: [
        {
            "id": f"{alb['id']}_t{j}",
            "name": f"Track {j + 1} — {alb['name']}",
            "duration_ms": 180_000 + j * 12_000,
            "external_urls": {"spotify": f"https://open.spotify.com/track/{alb['id']}_t{j}"},
        }
        for j in range(3)
    ]
    for alb in _ALBUMS
}

# Full track objects (for /tracks batch — includes ISRC)
_FULL_TRACKS: dict[str, dict] = {
    t["id"]: {
        **t,
        "artists": [{"name": "Mock Artist"}],
        "external_ids": {"isrc": f"US-MOCK-{i:02d}-{j:04d}"},
    }
    for i, alb in enumerate(_ALBUMS)
    for j, t in enumerate(_ALBUM_TRACKS[alb["id"]])
}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/search")
def mock_search(q: str = "", type: str = "artist", limit: int = 5):
    return {
        "artists": {
            "items": [
                {"id": "mock_artist_001", "name": f"Mock Artist ({q or 'query'})", "images": []}
            ]
        }
    }


@router.get("/artists/{artist_id}")
def mock_artist(artist_id: str):
    return {"id": artist_id, "name": "Mock Artist", "images": []}


@router.get("/artists/{artist_id}/albums")
def mock_artist_albums(request: Request, artist_id: str, include_groups: str = "", limit: int = 10, offset: int = 0):
    page = _ALBUMS[offset : offset + limit]
    has_next = offset + limit < len(_ALBUMS)
    base = str(request.base_url).rstrip("/")
    return {
        "items": page,
        "total": len(_ALBUMS),
        "limit": limit,
        "offset": offset,
        "next": (
            f"{base}/mock/spotify/v1/artists/{artist_id}/albums"
            f"?limit={limit}&offset={offset + limit}"
            if has_next
            else None
        ),
    }


@router.get("/albums/{album_id}/tracks")
def mock_album_tracks(request: Request, album_id: str, limit: int = 50, offset: int = 0):
    tracks = _ALBUM_TRACKS.get(album_id, [])
    page = tracks[offset : offset + limit]
    has_next = offset + limit < len(tracks)
    base = str(request.base_url).rstrip("/")
    return {
        "items": page,
        "total": len(tracks),
        "limit": limit,
        "offset": offset,
        "next": (
            f"{base}/mock/spotify/v1/albums/{album_id}/tracks"
            f"?limit={limit}&offset={offset + limit}"
            if has_next
            else None
        ),
    }


@router.get("/tracks")
def mock_tracks(ids: str = ""):
    id_list = [t.strip() for t in ids.split(",") if t.strip()]
    return {
        "tracks": [
            _FULL_TRACKS.get(
                tid,
                {
                    "id": tid,
                    "name": f"Unknown ({tid})",
                    "artists": [{"name": "Mock Artist"}],
                    "external_ids": {"isrc": ""},
                    "duration_ms": 0,
                    "external_urls": {"spotify": ""},
                },
            )
            for tid in id_list
        ]
    }
