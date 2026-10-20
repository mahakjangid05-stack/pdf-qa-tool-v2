import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# project root me documents.db (backend/ ke ek level upar)
DB_PATH = Path(__file__).resolve().parent.parent / "documents.db"


def _now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_doc ON chat_history(doc_id)")


def save_document(doc_id, filename, num_pages, num_chunks):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO documents (doc_id, filename, num_pages, num_chunks, uploaded_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (doc_id, filename, num_pages, num_chunks, _now()),
        )


def get_document(doc_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
    return dict(row) if row else None


def list_documents():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
    return [dict(r) for r in rows]


def save_chat(doc_id, question, answer):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_history (doc_id, question, answer, created_at) VALUES (?, ?, ?, ?)",
            (doc_id, question, answer, _now()),
        )


def get_chat_history(doc_id, limit=50):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT question, answer, created_at FROM chat_history "
            "WHERE doc_id = ? ORDER BY id DESC LIMIT ?",
            (doc_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    save_document("test-id", "test.pdf", 10, 42)
    save_chat("test-id", "Who is Daudet?", "A French novelist.")
    print(get_document("test-id"))
    print(get_chat_history("test-id"))