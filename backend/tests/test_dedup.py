import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from dedup import _key, deduplicate
from spotify import _normalize_date

# ── _key ──────────────────────────────────────────────────────────────────────

def test_key_strips_and_lowercases():
    assert _key("  Song Title  ") == "song title"
    assert _key("UPPERCASE") == "uppercase"
    assert _key("Mixed Case") == "mixed case"


# ── deduplicate ───────────────────────────────────────────────────────────────

def _track(name: str, date: str, album: str = "A") -> dict:
    return {
        "track_name": name,
        "release_date": date,
        "album_name": album,
        "artist_name": "",
        "duration_ms": 0,
        "isrc": "",
        "spotify_url": "",
    }


def test_keeps_newest_when_duplicated():
    tracks = [
        _track("Song", "2020-01-01"),
        _track("Song", "2023-05-01"),
    ]
    result = deduplicate(tracks)
    assert len(result) == 1
    assert result[0]["release_date"] == "2023-05-01"


def test_dedup_is_case_insensitive():
    tracks = [_track("SONG", "2020-01-01"), _track("song", "2023-01-01")]
    result = deduplicate(tracks)
    assert len(result) == 1


def test_variants_are_kept_separately():
    tracks = [
        _track("Song", "2020-01-01"),
        _track("Song (Live)", "2021-01-01"),
        _track("Song (Acoustic)", "2022-01-01"),
    ]
    assert len(deduplicate(tracks)) == 3


def test_output_sorted_descending_by_date():
    tracks = [
        _track("A", "2020-01-01"),
        _track("B", "2023-01-01"),
        _track("C", "2021-01-01"),
    ]
    result = deduplicate(tracks)
    dates = [t["release_date"] for t in result]
    assert dates == sorted(dates, reverse=True)


def test_empty_input():
    assert deduplicate([]) == []


def test_single_track_passthrough():
    tracks = [_track("Only", "2022-06-15")]
    result = deduplicate(tracks)
    assert len(result) == 1
    assert result[0]["track_name"] == "Only"


# ── _normalize_date ───────────────────────────────────────────────────────────

def test_normalize_year_only():
    assert _normalize_date("2023") == "2023-01-01"


def test_normalize_year_month():
    assert _normalize_date("2023-05") == "2023-05-01"


def test_normalize_full_date_unchanged():
    assert _normalize_date("2023-05-15") == "2023-05-15"
