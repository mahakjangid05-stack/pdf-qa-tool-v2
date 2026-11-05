# PDF Q&A API (v2)

Upload a PDF and ask questions about it. Answers are generated from the document's own content using RAG + Claude.

## Features
- PDF upload with text extraction and chunking
- Retrieval using ChromaDB
- Answers from the Anthropic Claude API
- SQLite chat history per document
- Duplicate upload detection
- X-API-Key authentication
- Mock mode (runs without an API key, for testing)
- Automated tests with pytest

## Tech Stack
Python, FastAPI, ChromaDB, SQLite, PyPDF2, Anthropic API, pytest

## Setup
```bash
git clone https://github.com/mahakjangid05-stack/pdf-qa-tool-v2.git
cd pdf-qa-tool-v2
pip install -r requirements.txt
```
Create a `.env` file:
```
ANTHROPIC_API_KEY=your_key_here
API_KEY=your_api_key_here   # <- apne code ke hisaab se naam likho
```
Run:
```bash
uvicorn main:app --reload
```
Docs: http://127.0.0.1:8000/docs

## Endpoints
| Method | Endpoint | Description |
|---|---|---|
| GET | /status/ | Server status and mode |
| GET | /documents/ | List uploaded documents |
| GET | /history/{doc_id} | Chat history of a document |
| POST | /upload-pdf/ | Upload a PDF |
| POST | /ask/ | Ask a question about a document |

## Example
(yahan `/ask/` ka ek real request aur response paste karo)

## Tests
```bash
pytest -v
```

## Demo
(demo video ka link, baad mein daalna)
