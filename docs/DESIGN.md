# UniVibe — Design Notes

## Architecture

```
browser (index.html — all business logic lives here)
  ├─ Spotify PKCE OAuth  → https://accounts.spotify.com  (direct)
  ├─ Spotify API calls   → https://api.spotify.com/v1    (direct, bearer token)
  └─ GET /               → served by FastAPI backend

backend/
  main.py           FastAPI: serves index.html + mounts mock router
  mock_spotify.py   Local mock for /mock/spotify/v1/* (dev only, USE_MOCK=true)
```

All Spotify API calls are made directly from the browser (no backend proxy).
The backend exists solely to serve the static HTML and provide the dev mock.

## Distribution

Built via PyInstaller (`univibe.spec`) into a single `dist/UniVibe.exe`.
- No SSL cert bundled → runs on `http://127.0.0.1:8000`
- Auto-opens browser on launch; close the console window to stop the server
- Build: `.\build.ps1`

Spotify redirect URI requirements (confirmed 2026-05-24):
- `http://127.0.0.1` is explicitly allowed as a loopback exception (HTTPS not required)
- `localhost` hostname is banned; must use `127.0.0.1` IP
- Reference: https://developer.spotify.com/blog/2025-02-12-increasing-the-security-requirements-for-integrating-with-spotify

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

- No integration tests covering the full fetch→dedup→CSV pipeline.
- **[Future] Playlist import**: Export collected track list directly as a Spotify playlist
  via `POST /v1/playlists/{id}/tracks`. Requires upgrading to user-level OAuth
  (currently client credentials only); would need a new OAuth scope (`playlist-modify-public`
  or `playlist-modify-private`) and a playlist creation step in the UI.
