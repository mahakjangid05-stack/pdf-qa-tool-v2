import sqlite3
import uuid
from datetime import datetime

DB_PATH = "documents.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            num_pages INTEGER,
            num_chunks INTEGER,
            uploaded_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def add_document(filename, num_pages, num_chunks):
    doc_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        "INSERT INTO documents VALUES (?, ?, ?, ?, ?)",
        (doc_id, filename, num_pages, num_chunks, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return doc_id


def get_document(doc_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM documents WHERE doc_id = ?", (doc_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_documents():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    did = add_document("test.pdf", 10, 42)
    print(get_document(did))
    print(list_documents())