from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from apa7_agent import __version__
from apa7_agent.pipeline import ReferenceAgent
from apa7_agent.providers import CrossrefProvider
from apa7_agent.reporting import render_corrected_references, render_markdown


STATIC_DIR = Path(__file__).parent / "static"
ALLOWED_SUFFIXES = {".txt", ".md", ".pdf", ".docx"}
MAX_UPLOAD_BYTES = int(os.getenv("APA7_MAX_UPLOAD_MB", "15")) * 1024 * 1024


app = FastAPI(
    title="APA 7 Reference Agent",
    description="Evidence-bounded reference extraction, verification, and correction.",
    version=__version__,
    docs_url="/api/docs",
    redoc_url=None,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


async def _save_upload(upload: UploadFile, destination: Path) -> int:
    total = 0
    with destination.open("wb") as target:
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise HTTPException(413, f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.")
            target.write(chunk)
    return total


@app.post("/api/analyze")
async def analyze(
    file: Annotated[UploadFile, File(description="Academic document or reference list")],
    offline: Annotated[bool, Form()] = False,
    auto_fix: Annotated[bool, Form()] = True,
    title_threshold: Annotated[float, Form()] = 0.92,
    mailto: Annotated[str | None, Form()] = None,
) -> dict:
    filename = Path(file.filename or "upload.txt").name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(415, "Unsupported file type. Upload TXT, Markdown, PDF, or DOCX.")
    if not 0.0 <= title_threshold <= 1.0:
        raise HTTPException(422, "title_threshold must be between 0 and 1.")

    with tempfile.TemporaryDirectory(prefix="apa7-upload-") as temp_dir:
        temp_path = Path(temp_dir) / ("input" + suffix)
        try:
            file_size = await _save_upload(file, temp_path)
            provider = None
            if not offline:
                cache_dir = Path(os.getenv("APA7_CACHE_DIR", Path(tempfile.gettempdir()) / "apa7-reference-agent"))
                provider = CrossrefProvider(mailto=mailto or None, cache_path=cache_dir / "crossref-cache.json")
            agent = ReferenceAgent(
                provider=provider,
                auto_fix=auto_fix,
                title_threshold=title_threshold,
            )
            report = await run_in_threadpool(agent.analyze, temp_path)
        except HTTPException:
            raise
        except (OSError, ValueError, RuntimeError) as exc:
            raise HTTPException(422, str(exc)) from exc
        finally:
            await file.close()

    payload = report.to_dict()
    payload["input_file"] = filename
    payload["upload"] = {"filename": filename, "size_bytes": file_size}
    payload["exports"] = {
        "markdown": render_markdown(report).replace(str(temp_path), filename),
        "corrected_references": render_corrected_references(report),
    }
    return payload


def run() -> None:
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("apa7_agent.web.app:app", host=host, port=port, reload=False)
