import os
from pathlib import Path

import chromadb

from backend.pdf_processor import chunk_text

CHROMA_PATH = Path(__file__).resolve().parent.parent / "chroma_data"
COLLECTION_NAME = "pdf_chunks"
BATCH_SIZE = 100

# Cosine distance: chhota = zyada similar.
# Sahi sawaalon pe bhi "nahi mila" aaye to badhao (1.1, 1.2),
# bekaar sawaalon pe bhi answer aaye to ghatao (0.9, 0.8).
MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "1.0"))

_collection = None


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_document(doc_id, pages):
    """pages: [{"page": 1, "text": "..."}]  ->  stored chunks ki count"""
    ids, docs, metas = [], [], []
    for p in pages:
        for i, chunk in enumerate(chunk_text(p["text"])):
            ids.append(f"{doc_id}_p{p['page']}_c{i}")
            docs.append(chunk)
            metas.append({"doc_id": doc_id, "page": p["page"]})

    if not ids:
        return 0

    collection = get_collection()
    try:
        for s in range(0, len(ids), BATCH_SIZE):
            collection.add(
                ids=ids[s : s + BATCH_SIZE],
                documents=docs[s : s + BATCH_SIZE],
                metadatas=metas[s : s + BATCH_SIZE],
            )
    except Exception:
        delete_document(doc_id)
        raise
    return len(ids)


def search(doc_id, question, top_k=4):
    """Sirf is doc_id ke chunks me dhundo. Return: [{"text", "page", "distance"}]"""
    collection = get_collection()
    res = collection.query(
        query_texts=[question],
        n_results=top_k,
        where={"doc_id": doc_id},
    )

    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]

    results = []
    for text, meta, dist in zip(docs, metas, dists):
        if dist <= MAX_DISTANCE:
            results.append({"text": text, "page": meta.get("page"), "distance": round(dist, 4)})
    return results


def delete_document(doc_id):
    get_collection().delete(where={"doc_id": doc_id})

