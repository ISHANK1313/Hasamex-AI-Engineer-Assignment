"""FastAPI app: 5 routes over the deterministic core, plus a static single-page UI.

The store is in-memory. The transcripts total ~40 turns and load instantly, so a database and a
repository layer would be scaffolding for a scale this app does not have. The SQLite/FTS5 design in
docs/07-Database-Schema.md is the answer to "how would you scale this to 30+", not the v1 shape.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import analyze, llm

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # trust boundary: cap what a browser may push at us


# --- errors -------------------------------------------------------------------------------------

class AppError(Exception):
    """Anything we raise deliberately. Turns into the {error:{code,message}} envelope."""

    def __init__(self, message: str, code: str = "BAD_REQUEST", status_code: int = 400):
        self.message, self.code, self.status_code = message, code, status_code
        super().__init__(message)


class NotFound(AppError):
    def __init__(self, message: str):
        super().__init__(message, code="NOT_FOUND", status_code=404)


# --- state --------------------------------------------------------------------------------------

class Store:
    """Everything the app knows, held in memory. Reloaded from disk on startup."""

    def __init__(self) -> None:
        self.transcripts: list[dict] = []
        self.guide: list[dict] = []

    def load(self, directory: Path | None = None) -> None:
        self.transcripts = analyze.load_transcripts(directory)
        self.guide = analyze.load_guide()
        llm.reset_cache()
        log.info("loaded %d transcripts, %d guide questions", len(self.transcripts), len(self.guide))

    def add(self, transcript: dict) -> dict:
        """Replace a market if it is already loaded, so re-uploading a corrected file works."""
        self.transcripts = [t for t in self.transcripts if t["market"] != transcript["market"]]
        self.transcripts.append(transcript)
        self.transcripts.sort(key=lambda t: t["source"])
        llm.reset_cache()
        return transcript

    def segments(self) -> list[dict]:
        return [s for t in self.transcripts for s in t["segments"]]

    def require_loaded(self) -> None:
        if not self.transcripts:
            raise AppError("no transcripts are loaded", code="NO_TRANSCRIPTS", status_code=409)


store = Store()

@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    store.load()
    yield


app = FastAPI(title="Expert-Call Transcript Analyzer", version="1.0.0", lifespan=lifespan)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):  # noqa: ARG001
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message}})


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):  # noqa: ARG001
    log.exception("unhandled error")  # full detail server-side only
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}},
    )


# --- routes -------------------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "transcripts": len(store.transcripts),
        "segments": len(store.segments()),
        "llm": llm.provider_name(),
        "llm_available": llm.available(),
    }


@app.get("/api/transcripts")
def list_transcripts():
    return {
        "transcripts": [
            {
                "market": t["market"],
                "expert": t["expert"],
                "role": t["role"],
                "source": t["source"],
                "segments": len(t["segments"]),
                "turns": sum(1 for s in t["segments"] if s["is_expert"]),
                "duration": t["segments"][-1]["timestamp"] if t["segments"] else "00:00",
            }
            for t in store.transcripts
        ]
    }


@app.post("/api/transcripts/ingest")
async def ingest(file: UploadFile | None = File(default=None)):
    """Load the bundled samples, or add one uploaded transcript in the same format."""
    if file is None:
        store.load()
        return {"ingested": [t["market"] for t in store.transcripts], "source": "bundled_samples"}

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise AppError(f"file is larger than {MAX_UPLOAD_BYTES // 1024} KB", code="FILE_TOO_LARGE", status_code=413)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise AppError("file must be UTF-8 text", code="BAD_ENCODING", status_code=415) from None
    try:
        transcript = analyze.parse_transcript(text, file.filename or "upload.txt")
    except ValueError as e:
        raise AppError(str(e), code="PARSE_ERROR", status_code=422) from None

    store.add(transcript)
    return {
        "ingested": [transcript["market"]],
        "expert": transcript["expert"],
        "segments": len(transcript["segments"]),
    }


@app.get("/api/guide-answers")
def guide_answers(use_llm: bool = True):
    """Every guide question, answered per expert, with verbatim quotes and timestamps."""
    store.require_loaded()
    questions = analyze.guide_answers(store.transcripts, store.guide)
    out = []
    for q in questions:
        summary = llm.summarize_question(q, q["answers"]) if use_llm else {"summary": "", "provider": "lexical", "citations": []}
        out.append(
            {
                "id": q["id"],
                "topic": q["topic"],
                "name": q["name"],
                "question": q["question"],
                "summary": summary["summary"],
                "summary_provider": summary["provider"],
                "answers": q["answers"],
            }
        )
    return {"questions": out, "provider": llm.provider_name()}


@app.get("/api/themes")
def themes():
    """Common themes across experts, and where they disagree."""
    store.require_loaded()
    return analyze.themes_and_disagreements(store.transcripts, store.guide)


@app.post("/api/ask")
async def ask(payload: dict):
    """Free-form question across all transcripts. Always returns citations."""
    store.require_loaded()
    question = (payload.get("question") or "").strip()
    if not question:
        raise AppError("question must not be empty", code="EMPTY_QUESTION", status_code=422)
    if len(question) > 500:
        raise AppError("question must be 500 characters or fewer", code="QUESTION_TOO_LONG", status_code=422)
    if payload.get("use_llm", True) is False:
        evidence, topic = analyze.retrieve(question, store.transcripts)
        result = llm._lexical_answer(evidence)
        return {"question": question, "topic": topic, **result}
    evidence, topic = analyze.retrieve(question, store.transcripts)
    return {"question": question, "topic": topic, **llm.answer_question(question, evidence)}


@app.get("/api/segments/{segment_id:path}")
def segment(segment_id: str):
    """Source turn behind a citation, so the UI can prove a quote is real."""
    for s in store.segments():
        if s["id"] == segment_id:
            return s
    raise NotFound(f"no segment with id {segment_id!r}")


# --- static UI ----------------------------------------------------------------------------------

if STATIC.is_dir():
    app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")