import hashlib
import io
import json
import os
import re
import secrets
import uuid
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel
from PyPDF2 import PdfReader

load_dotenv()

try:
    import anthropic
except ImportError:  # anthropic not installed -> mock mode
    anthropic = None

app = FastAPI(title="PDF Q&A Tool v2")


def verify_key(x_api_key: str = Header(None)):
    expected = os.getenv("APP_API_KEY")
    if not expected or not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ---------- Config ----------
API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
client = anthropic.Anthropic(api_key=API_KEY) if (anthropic and API_KEY) else None
MOCK_MODE = client is None

DATA_FILE = Path("data.json")
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
TOP_K = 3

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "of", "in", "on", "to", "and",
    "or", "for", "with", "what", "who", "how", "why", "when", "where", "this",
    "that", "it", "about", "me", "tell", "please", "does", "do", "document",
}

# ---------- Storage ----------
documents: Dict[str, dict] = {}
history: Dict[str, List[dict]] = {}


def save_data() -> None:
    DATA_FILE.write_text(
        json.dumps({"documents": documents, "history": history}, ensure_ascii=False),
        encoding="utf-8",
    )


def load_data() -> None:
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            documents.update(data.get("documents", {}))
            history.update(data.get("history", {}))
        except (json.JSONDecodeError, OSError):
            pass


load_data()


# ---------- Helpers ----------
def chunk_pages(pages: List[str]) -> List[dict]:
    chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    for page_no, text in enumerate(pages, start=1):
        text = re.sub(r"\s+", " ", text).strip()
        for start in range(0, len(text), step):
            piece = text[start:start + CHUNK_SIZE]
            if piece.strip():
                chunks.append({"page": page_no, "text": piece})
    return chunks


def keyword_search(question: str, chunks: List[dict]) -> List[dict]:
    words = [w for w in re.findall(r"\w+", question.lower()) if w not in STOPWORDS]
    scored = []
    for chunk in chunks:
        text = chunk["text"].lower()
        score = sum(text.count(w) for w in words)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [c for _, c in scored[:TOP_K]]
    if top:
        return top
    return chunks[:TOP_K]


def ask_llm(question: str, context: str) -> str:
    if MOCK_MODE:
        return "[MOCK MODE - no API key set] Most relevant text found:\n\n" + context[:500]
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=(
            "You answer questions using ONLY the provided document context. "
            "If the answer is not in the context, say so clearly. "
            "Reply in the same language as the question."
        ),
        messages=[
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ],
    )
    return msg.content[0].text


# ---------- Models ----------
class QuestionRequest(BaseModel):
    doc_id: str
    question: str


# ---------- Endpoints ----------
@app.get("/")
def root():
    return {"message": "pdf q&A tool v2 running", "docs": "/docs"}


@app.get("/status/")
def status():
    return {"status": "ok", "mock_mode": MOCK_MODE, "documents": len(documents)}


@app.get("/documents/", dependencies=[Depends(verify_key)])
def list_documents():
    return [
        {
            "doc_id": doc_id,
            "filename": d["filename"],
            "pages": d["pages"],
            "chunks": len(d["chunks"]),
        }
        for doc_id, d in documents.items()
    ]


@app.get("/history/{doc_id}", dependencies=[Depends(verify_key)])
def get_history(doc_id: str):
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail="doc_id not found")
    return history.get(doc_id, [])


@app.post("/upload-pdf/", dependencies=[Depends(verify_key)])
async def upload_pdf(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are allowed")
    raw = await file.read()
    file_hash = hashlib.sha256(raw).hexdigest()
    for existing_id, existing in documents.items():
        if existing.get("file_hash") == file_hash:
            return {
                "doc_id": existing_id,
                "filename": existing["filename"],
                "pages": existing["pages"],
                "chunks": len(existing["chunks"]),
                "duplicate": True,
            }

    try:
        reader = PdfReader(io.BytesIO(raw))
        pages = [(p.extract_text() or "") for p in reader.pages]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}")

    chunks = chunk_pages(pages)
    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No text found. The PDF may be scanned images (needs OCR).",
        )
    doc_id = uuid.uuid4().hex
    documents[doc_id] = {
        "filename": os.path.basename(file.filename),
        "pages": len(pages),
        "chunks": chunks,
        "file_hash": file_hash,
    }
    history[doc_id] = []
    save_data()

    return {
        "doc_id": doc_id,
        "filename": documents[doc_id]["filename"],
        "pages": len(pages),
        "chunks": len(chunks),
        "chars_extracted": sum(len(p) for p in pages),
    }


@app.post("/ask/", dependencies=[Depends(verify_key)])
async def ask(req: QuestionRequest):
    doc = documents.get(req.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="doc_id not found. Upload the PDF first.")

    matched = keyword_search(req.question, doc["chunks"])
    context = "\n\n".join(f"[Page {c['page']}] {c['text']}" for c in matched)

    try:
        answer = ask_llm(req.question, context)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    history.setdefault(req.doc_id, []).append({"question": req.question, "answer": answer})
    save_data()

    return {
        "doc_id": req.doc_id,
        "question": req.question,
        "answer": answer,
        "sources": [{"page": c["page"], "preview": c["text"][:150]} for c in matched],
    }
