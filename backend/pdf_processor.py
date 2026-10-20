import re

from PyPDF2 import PdfReader


def extract_text(pdf_source):
    """pdf_source: file path ya file-like object (io.BytesIO).
    Return: [{"page": 1, "text": "..."}, ...]"""
    reader = PdfReader(pdf_source)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({"page": i + 1, "text": text})
    return pages


def chunk_text(text, chunk_size=500, overlap=50):
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # word ke beech me mat kaato: last space tak peeche aao
            space = text.rfind(" ", start + overlap + 1, end)
            if space != -1:
                end = space
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


if __name__ == "__main__":
    pages = extract_text("test.pdf")  # apni PDF ka naam do
    for p in pages[:2]:
        for c in chunk_text(p["text"]):
            print(p["page"], "|", c)