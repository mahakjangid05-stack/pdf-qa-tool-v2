# PDF Q&A Tool v2

Upload a PDF and ask questions about it. Answers come from the document's content, with page numbers.

## What's new in v2
- Keyword search replaced with semantic search (ChromaDB)
- In-memory storage replaced with SQLite + ChromaDB, so documents survive a server restart
- Multiple PDFs supported, each with its own `doc_id`

## Tech Stack
Python, FastAPI, ChromaDB, SQLite, PyPDF2, Anthropic API

## How it works
1. `/upload-pdf/` extracts text, splits it into chunks and stores them in ChromaDB
2. `/ask/` finds the most relevant chunks for the question
3. Claude answers using only those chunks

## Setup
```
git clone