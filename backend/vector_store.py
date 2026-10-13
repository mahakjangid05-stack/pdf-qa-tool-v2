import chromadb

client = chromadb.PersistentClient(path="chroma_data")
collection = client.get_or_create_collection("pdf_chunks")


def add_chunks(doc_id, chunks):
    # chunks = [{"text": "...", "page": 1}, ...]
    collection.add(
        ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
        documents=[c["text"] for c in chunks],
        metadatas=[{"doc_id": doc_id, "page": c["page"]} for c in chunks],
    )


def query_chunks(doc_id, question, n_results=3):
    res = collection.query(
        query_texts=[question],
        n_results=n_results,
        where={"doc_id": doc_id},  # sirf isi PDF ke chunks mein search
    )
    return res["documents"][0], res["metadatas"][0]