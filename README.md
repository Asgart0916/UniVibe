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

---

## Installation

### Option A — Standalone .exe (Windows, no Python required)

1. Download `UniVibe.exe` from [Releases](https://github.com/asgart0916/UniVibe/releases/latest)
2. Set up a Spotify App (one-time, see [Spotify setup](#spotify-setup) below)
3. Double-click `UniVibe.exe` — the browser opens automatically
4. Enter your **Client ID** in the app and log in with Spotify

To stop the server, close the console window that appears alongside the browser.

### Option B — Run from source (developers)

**Prerequisites:** Python 3.10+

```powershell
# 1. Clone and create venv
git clone https://github.com/asgart0916/UniVibe.git
cd UniVibe
python -m venv .venv
.venv\Scripts\activate

# 2. Install dependencies
pip install fastapi uvicorn

# 3. Run
python backend/main.py
# Browser opens automatically at http://127.0.0.1:8000
```

To build the .exe yourself:
```powershell
.\build.ps1   # outputs dist\UniVibe.exe
```

---

## Spotify setup

> **One-time setup required.** UniVibe uses Spotify's OAuth PKCE flow — you need a free Spotify Developer App to obtain a Client ID.

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and log in
2. Click **Create app** — any name/description works
3. Under **Redirect URIs**, add: `http://127.0.0.1:8000`
   > `localhost` is not accepted; use the explicit IP `127.0.0.1`
   > ([Spotify policy, confirmed 2026-05-24](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri))
4. Copy the **Client ID** (you do **not** need the Client Secret)
5. Paste the Client ID into UniVibe when prompted

### Sharing with others (Dev Mode limit)

Spotify's Development Mode allows **up to 5 users** (including yourself). Each person who wants to use the app must be added manually:

1. In the Dashboard, go to your app → **Users and Access**
2. Add each person's Spotify account email
3. Share `UniVibe.exe` and your **Client ID** with them

---

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python / FastAPI (serves static HTML only) |
| Frontend | Vanilla HTML + JS (no framework) |
| Spotify auth | PKCE OAuth (user login, no Client Secret required) |
| Packaging | PyInstaller — single `UniVibe.exe` for Windows |

---

## Roadmap

- [x] Spotify API integration (artist search, album/track fetch)
- [x] Deduplication logic & CSV export
- [x] FastAPI backend + frontend UI
- [x] Incremental update (re-fetch only new releases)
- [x] PyInstaller standalone `.exe`
- [ ] Direct Spotify playlist import from collected track list

## License

MIT
