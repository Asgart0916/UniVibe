from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from mock_spotify import router as mock_router

app = FastAPI()
app.include_router(mock_router)

_html = Path(__file__).parent.parent / "frontend" / "index.html"

_root = Path(__file__).parent.parent
_CERT = _root / "127.0.0.1.pem"
_KEY  = _root / "127.0.0.1-key.pem"


@app.get("/{full_path:path}", response_class=HTMLResponse)
def index(full_path: str = ""):
    return _html.read_text(encoding="utf-8")


if __name__ == "__main__":
    cert = str(_CERT) if _CERT.exists() and _KEY.exists() else None
    key  = str(_KEY)  if cert else None
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False,
                ssl_certfile=cert, ssl_keyfile=key)
