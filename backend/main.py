import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from mock_spotify import router as mock_router

app = FastAPI()
app.include_router(mock_router)

# sys._MEIPASS is the temp extraction dir when running as a PyInstaller bundle
_base = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parent.parent  # type: ignore[attr-defined]
_html = _base / "frontend" / "index.html"
_CERT = _base / "127.0.0.1.pem"
_KEY  = _base / "127.0.0.1-key.pem"


@app.get("/{full_path:path}", response_class=HTMLResponse)
def index(full_path: str = ""):
    return _html.read_text(encoding="utf-8")


def _open_browser(url: str) -> None:
    time.sleep(1.5)
    webbrowser.open(url)


if __name__ == "__main__":
    cert = str(_CERT) if _CERT.exists() and _KEY.exists() else None
    key  = str(_KEY)  if cert else None
    scheme = "https" if cert else "http"
    url = f"{scheme}://127.0.0.1:8000"
    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False,
                ssl_certfile=cert, ssl_keyfile=key)
