# UniVibe — Design Notes

## Architecture

```
browser
  └─ GET /            → serves frontend/index.html
  └─ POST /config     → validates + saves Spotify credentials
  └─ GET  /search     → artist search
  └─ GET  /resolve/:id → artist lookup by Spotify URL
  └─ POST /fetch      → full track fetch (blocking, streams CSV response)
  └─ POST /update     → incremental fetch since last_fetched_at
  └─ GET  /fetch-progress/:id → in-memory progress dict (polled every 1s)
  └─ GET  /artist/:id/status  → last_fetched_at + track_count from state.json

backend/
  main.py      FastAPI app + route handlers
  spotify.py   Spotify Web API client (token, search, fetch)
  dedup.py     Deduplication logic + CSV serialisation
  state.py     JSON persistence (~/.univibe/state.json)
```

## Module Responsibilities

| Module | Responsibility | Side effects |
|---|---|---|
| `spotify.py` | All Spotify API calls; token caching; rate-limit handling | Mutates `_token_cache` (module global) |
| `dedup.py` | Pure functions; dedup by name, CSV output | None |
| `state.py` | Read/write `~/.univibe/state.json` thread-safely | Writes to filesystem |
| `main.py` | HTTP routing; in-memory progress state; response shaping | Mutates `_progress` (module global, guarded by `_progress_lock`) |

## Spotify Dev Mode Constraints

These are **hard limits** imposed on apps in Spotify's Development Mode (< 25 users).
Do not change these values without verifying Extended Quota Mode has been granted.

| Constraint | Value | Why |
|---|---|---|
| `albums` page limit | `10` | `limit=50` returns HTTP 400 |
| Batch `/v1/artists?ids=` | Not used | Returns HTTP 403 in Dev Mode |
| `followers`, `popularity`, `genres` | Not returned | Stripped from artist objects in Dev Mode |
| `_REQUEST_INTERVAL` | `0.2s` | ~5 req/s proactive throttle within 30s rolling window |
| `_RATE_LIMIT_ABORT_SECS` | `300s` | `Retry-After` values > 5 min indicate credential exhaustion; abort and show error |

## Key Design Decisions

**Client Credentials flow (no user OAuth)**
Users supply their own Spotify App credentials. The tool never requests user-level
permissions, so no OAuth callback or token refresh is needed beyond the client token.

**Progress via polling, not WebSocket**
Frontend polls `/fetch-progress/{artist_id}` every second. Simpler to implement and
debug; acceptable latency for a batch operation taking 10–120s.

**ISRC fetch is best-effort**
`/v1/tracks` batch may be restricted in Dev Mode. `_batch_full_tracks` returns `{}`
on any error and logs a warning; ISRC fields are empty strings rather than blocking.

**Dedup key: `strip().lower()` on track_name**
Exact-match after normalisation. This keeps `"Song (Live)"` and `"Song"` separate
(correct) while merging `"SONG"` and `"song"` (also correct). Does not attempt
fuzzy matching; false-positives from exact duplication are far more common than
false-negatives from near-duplicates.

**State file: plaintext JSON**
Credentials stored at `~/.univibe/state.json` without encryption. Acceptable for a
local single-user tool; document clearly and do not deploy on shared servers.

## Known Issues / Future Work

- `save_artist_tracks` acquires `_state_lock` for the full read-modify-write cycle,
  preventing concurrent writes from corrupting the file. However, the file is not
  written atomically (no temp-file rename), so a crash mid-write can corrupt state.
- PyInstaller packaging (`sys._MEIPASS` path detection) is implemented but untested.
- No integration tests covering the full fetch→dedup→CSV pipeline.
