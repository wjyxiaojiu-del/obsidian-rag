import chromadb
from rank_bm25 import BM25Okapi
import jieba
from app.config import settings
from app.rag.embedder import embed_query
from app.models import SourceRef, SourceType

_chroma_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None
_bm25_corpus: list[dict] = []
_bm25_index: BM25Okapi | None = None


def get_chroma_collection() -> chromadb.Collection:
    global _chroma_client, _collection
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        _collection = _chroma_client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def rebuild_bm25_index():
    """Rebuild BM25 index from all documents in ChromaDB."""
    global _bm25_corpus, _bm25_index
    collection = get_chroma_collection()
    result = collection.get(include=["documents", "metadatas"])
    if not result["ids"]:
        _bm25_corpus = []
        _bm25_index = None
        return

    _bm25_corpus = [
        {
            "id": id_,
            "text": doc,
            "metadata": meta,
        }
        for id_, doc, meta in zip(result["ids"], result["documents"], result["metadatas"])
    ]

    tokenized = [list(jieba.cut(item["text"])) for item in _bm25_corpus]
    _bm25_index = BM25Okapi(tokenized)


def vector_search(query: str, top_k: int = 5) -> list[dict]:
    """Semantic vector search via ChromaDB."""
    collection = get_chroma_collection()
    query_embedding = embed_query(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for i in range(len(results["ids"][0])):
        hits.append({
            "id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "score": 1 - results["distances"][0][i],  # cosine distance -> similarity
        })
    return hits


def bm25_search(query: str, top_k: int = 5) -> list[dict]:
    """BM25 keyword search."""
    if _bm25_index is None:
        rebuild_bm25_index()
    if _bm25_index is None or not _bm25_corpus:
        return []

    tokenized_query = list(jieba.cut(query))
    scores = _bm25_index.get_scores(tokenized_query)

    # Get top-k indices
    top_indices = scores.argsort()[-top_k:][::-1]
    hits = []
    for idx in top_indices:
        if scores[idx] > 0:
            item = _bm25_corpus[idx]
            hits.append({
                "id": item["id"],
                "text": item["text"],
                "metadata": item["metadata"],
                "score": float(scores[idx]),
            })
    return hits


def hybrid_search(query: str, top_k: int = 5) -> list[dict]:
    """Combine vector and BM25 search with RRF (Reciprocal Rank Fusion)."""
    vector_hits = vector_search(query, top_k=top_k * 2)
    bm25_hits = bm25_search(query, top_k=top_k * 2)

    # Reciprocal Rank Fusion
    k = 60
    scores: dict[str, float] = {}
    hit_map: dict[str, dict] = {}

    for rank, hit in enumerate(vector_hits):
        doc_id = hit["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
        hit_map[doc_id] = hit

    for rank, hit in enumerate(bm25_hits):
        doc_id = hit["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
        if doc_id not in hit_map:
            hit_map[doc_id] = hit

    # Sort by fused score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]

    results = []
    for doc_id in sorted_ids:
        hit = hit_map[doc_id]
        hit["score"] = scores[doc_id]
        results.append(hit)

    return results


def retrieve(query: str, top_k: int | None = None) -> list[SourceRef]:
    """Main retrieval function. Returns ranked SourceRef list."""
    k = top_k or settings.top_k
    hits = hybrid_search(query, top_k=k)

    sources = []
    for hit in hits:
        meta = hit.get("metadata", {})
        source_type = meta.get("source_type", "obsidian")

        sources.append(SourceRef(
            doc_id=hit["id"],
            file_name=meta.get("file_name", "unknown"),
            source_type=SourceType(source_type),
            chunk_text=hit["text"],
            score=hit["score"],
            vault_path=meta.get("vault_path"),
            heading_path=meta.get("heading_path"),
            url=meta.get("url"),
        ))

    return sources
