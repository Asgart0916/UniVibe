from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from mock_spotify import router as mock_router

app = FastAPI()
app.include_router(mock_router)

_html = Path(__file__).parent.parent / "frontend" / "index.html"


@app.get("/{full_path:path}", response_class=HTMLResponse)
def index(full_path: str = ""):
    return _html.read_text(encoding="utf-8")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
