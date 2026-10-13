import os
import shutil
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from backend.pdf_processor import extract_text, chunk_text
from backend.vector_store import add_chunks, query_chunks
from backend.database import init_db, add_document, get_document, list_documents
from backend.llm_handler import ask_claude

app = FastAPI(title="PDF Q&A Tool v2")
init_db()


class AskRequest(BaseModel):
    doc_id: str
    question: str


@app.post("/upload-pdf/")
def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        pages = extract_text(tmp_path)
    finally:
        os.remove(tmp_path)

    chunks = []
    for p in pages:
        for c in chunk_text(p["text"]):
            chunks.append({"text": c, "page": p["page"]})

    if not chunks:
        raise HTTPException(status_code=400, detail="No text found in this PDF")

    doc_id = add_document(file.filename, len(pages), len(chunks))
    add_chunks(doc_id, chunks)

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "pages": len(pages),
        "chunks": len(chunks),
    }


@app.post("/ask/")
def ask(req: AskRequest):
    if not get_document(req.doc_id):
        raise HTTPException(status_code=404, detail="Document not found")

    chunks, metas = query_chunks(req.doc_id, req.question)
    answer = ask_claude(req.question, chunks)

    return {
        "answer": answer,
        "pages": sorted({m["page"] for m in metas}),
        "context_used": chunks,
    }


@app.get("/status/")
def status():
    return {"documents": list_documents()}