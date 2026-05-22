import csv
import io


def _key(name: str) -> str:
    return name.strip().lower()


def deduplicate(tracks: list[dict]) -> list[dict]:
    """Keep one track per normalized name — the one with the latest release_date."""
    best: dict[str, dict] = {}
    for t in tracks:
        k = _key(t["track_name"])
        if k not in best or t["release_date"] > best[k]["release_date"]:
            best[k] = t
    return sorted(best.values(), key=lambda t: t["release_date"], reverse=True)


def to_csv(tracks: list[dict]) -> str:
    fields = [
        "track_name", "artist_name", "album_name",
        "release_date", "duration_ms", "isrc", "spotify_url",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(tracks)
    return buf.getvalue()
