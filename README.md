# UniVibe

Collect every track from a Spotify artist into a single, deduplicated CSV — then keep it up to date with one click.

## What it does

- Fetches all albums, singles, EPs, and compilations for any artist on Spotify
- Deduplicates tracks by name, keeping the most recently released version
- Variant titles (Live, Acoustic, Remix, etc.) are treated as distinct tracks and all retained
- Exports a clean CSV ready to import into any playlist tool
- Incremental updates: re-run anytime and only new releases are fetched

## CSV output columns

| Column | Description |
|---|---|
| `track_name` | Track title |
| `artist_name` | Primary artist |
| `album_name` | Source album/single |
| `release_date` | Album release date (YYYY-MM-DD) |
| `duration_ms` | Track length in milliseconds |
| `isrc` | International Standard Recording Code |
| `spotify_url` | Direct Spotify link |

## Prerequisites

- Python 3.10+
- A free Spotify Developer account → [Create one here](https://developer.spotify.com/dashboard)

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/asgart0916/UniVibe.git
cd UniVibe
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux
pip install -r backend/requirements.txt

# 2. Configure credentials
copy .env.example .env
# Edit .env and fill in your SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET

# 3. Run
python backend/main.py
# Open http://127.0.0.1:8000 in your browser
```

### Getting Spotify API credentials

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account (free account works)
3. Click **Create app**
4. Fill in any name/description; set Redirect URI to `http://127.0.0.1:8000` — Spotify 自 2025/4/9 起禁止 `localhost`，須用明確 IP
5. Copy the **Client ID** and **Client Secret** into your `.env` file

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python / FastAPI |
| Frontend | Vanilla HTML + JS (no framework) |
| Spotify auth | Client Credentials flow (read-only, no user login) |
| State | `~/.univibe/state.json` |
| Packaging | PyInstaller (standalone `.exe` for Windows) |

## Security note

Your Spotify credentials are stored in plaintext at `~/.univibe/state.json`.
This is intentional for a local single-user tool — do not run this backend on a shared or public server.

## Roadmap

- [x] Project scaffold & documentation
- [x] Spotify API module (artist search, album/track fetch)
- [x] Deduplication logic & CSV export
- [x] Incremental update (state management)
- [x] FastAPI routes
- [x] Frontend UI
- [ ] PyInstaller packaging (standalone `.exe`)

## License

MIT
