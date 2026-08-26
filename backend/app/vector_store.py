import chromadb

from app.config import settings

_COLLECTION_NAME = "criminal_law_provisions"

_client = chromadb.PersistentClient(path=settings.vector_store_dir)


def get_collection():
    return _client.get_or_create_collection(_COLLECTION_NAME)


def query_provisions(query_text: str, n_results: int = 5) -> list[dict]:
    """Query the ingested statutory corpus. Returns [] if the collection is
    empty or has no relevant hits — callers must treat that as "no verified
    source found," never as license to fall back on the model's own
    parametric knowledge of section numbers (CLAUDE.md §8.4, §12.7)."""
    collection = get_collection()
    if collection.count() == 0:
        return []

    result = collection.query(query_texts=[query_text], n_results=min(n_results, collection.count()))
    hits = []
    ids = result.get("ids") or [[]]
    documents = result.get("documents") or [[]]
    metadatas = result.get("metadatas") or [[]]
    distances = result.get("distances") or [[]]
    for chunk_id, doc, meta, distance in zip(ids[0], documents[0], metadatas[0], distances[0]):
        hits.append({"chunk_id": chunk_id, "text": doc, "metadata": meta, "distance": distance})
    return hits
