from PyPDF2 import PdfReader


def extract_text(pdf_path):
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({"page": i + 1, "text": text})
    return pages


def chunk_text(text, chunk_size=500, overlap=50):
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


if __name__ == "__main__":
    pages = extract_text("test.pdf")  # apni PDF ka naam do
    for p in pages[:2]:
        for c in chunk_text(p["text"]):
            print(p["page"], "|", c)
            print("-----")