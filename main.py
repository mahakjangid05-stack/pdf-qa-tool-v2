"""
PDF Q&A Tool v2 - main.py

Flow:
  /upload-pdf/  -> PDF se text nikalo -> chunks -> ChromaDB me store -> metadata SQLite me
  /ask/         -> doc_id ke andar relevant chunks dhundo -> Claude se answer lo -> history save

Run:  uvicorn main:app --reload
Docs: http://127.0.0.1:8000/docs
"""

import io
import logging
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

# .env backend imports se PEHLE load hona zaroori hai
load_dotenv()

from backend.database import (  # noqa: E402
    get_chat_history,
    get_document,
    init_db,
    list_documents,
    save_chat,
    save_document,
)
from backend.llm_handler import generate_answer  # noqa: E402
from backend.pdf_processor import extract_text  # noqa: E402
from backend.rag_engine import add_document, delete_document, search  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("pdf-qa")

MAX_FILE_SIZE_MB = 10
TOP_K = 4
USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"
NOT_FOUND_MSG = "Is document me is sawaal ka jawab nahi mila."


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Startup complete | mock_mode=%s", USE_MOCK)
    yield


app = FastAPI(title="PDF Q&A Tool", version="2.0.0", lifespan=lifespan)


# ---------- Schemas ----------
class AskRequest(BaseModel):
    doc_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=3, max_length=1000)


class AskResponse(BaseModel):
    doc_id: str
    question: str
    answer: str
    sources: list[dict]


# ---------- Routes ----------
@app.get("/")
def root():
    return {"message": "PDF Q&A Tool v2 running", "docs": "/docs"}


@app.get("/status/")
def status():
    return {"status": "ok", "mock_mode": USE_MOCK, "documents": len(list_documents())}


@app.get("/documents/")
def documents():
    return list_documents()


@app.get("/history/{doc_id}")
def history(doc_id: str):
    if get_document(doc_id) is None:
        raise HTTPException(status_code=404, detail="doc_id nahi mila.")
    return get_chat_history(doc_id)


@app.post("/upload-pdf/")
def upload_pdf(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Sirf .pdf file allowed hai.")

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="File empty hai.")
    if len(data) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File {MAX_FILE_SIZE_MB}MB se badi hai.")

    try:
        pages = extract_text(io.BytesIO(data))
    except Exception:
        logger.exception("PDF parse fail")
        raise HTTPException(status_code=422, detail="PDF read nahi ho paayi (corrupt ya protected).")

    total_chars = sum(len(p["text"].strip()) for p in pages)
    if total_chars == 0:
        raise HTTPException(
            status_code=422,
            detail="PDF se text nahi nikla. Shayad scanned PDF hai (OCR chahiye).",
        )

    doc_id = uuid.uuid4().hex
    try:
        num_chunks = add_document(doc_id, pages)
        save_document(doc_id, file.filename, len(pages), num_chunks)
    except Exception:
        logger.exception("Document store fail")
        # adhoora data chhodna nahi hai
        try:
            delete_document(doc_id)
        except Exception:
            logger.exception("Cleanup fail")
        raise HTTPException(status_code=500, detail="Document save karte time error aaya.")

    logger.info("Uploaded %s | doc_id=%s pages=%d chunks=%d", file.filename, doc_id, len(pages), num_chunks)
    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "pages": len(pages),
        "chunks": num_chunks,
        "chars_extracted": total_chars,
    }


@app.post("/ask/", response_model=AskResponse)
def ask(req: AskRequest):
    if get_document(req.doc_id) is None:
        raise HTTPException(status_code=404, detail="doc_id nahi mila. Pehle PDF upload karo.")

    question = req.question.strip()

    try:
        chunks = search(req.doc_id, question, TOP_K)
    except Exception:
        logger.exception("Search fail")
        raise HTTPException(status_code=500, detail="Search me error aaya.")

    # Context nahi mila to LLM call mat karo (paisa bachta hai, hallucination bhi nahi hota)
    if not chunks:
        save_chat(req.doc_id, question, NOT_FOUND_MSG)
        return AskResponse(doc_id=req.doc_id, question=question, answer=NOT_FOUND_MSG, sources=[])

    if USE_MOCK:
        answer = f"[MOCK] {len(chunks)} relevant chunks mile. Real API ke liye USE_MOCK=false karo."
    else:
        try:
            answer = generate_answer(question, chunks)
        except Exception:
            logger.exception("LLM call fail")
            raise HTTPException(status_code=502, detail="LLM se answer nahi aaya. API key/credits check karo.")

    save_chat(req.doc_id, question, answer)
    sources = [{"page": c.get("page"), "distance": c.get("distance"), "preview": c["text"][:200]} for c in chunks]
    return AskResponse(doc_id=req.doc_id, question=question, answer=answer, sources=sources)