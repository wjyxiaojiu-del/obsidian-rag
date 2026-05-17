import asyncio
import uuid
from app.rag.retriever import retrieve, hybrid_search, get_chroma_collection, rebuild_bm25_index
from app.rag.embedder import embed_texts
from app.rag.generator import generate_answer, generate_answer_stream
from app.rag.query_rewriter import rewrite_query
from app.rag.context_compressor import compress_history
from app.models import ChatResponse, SourceRef

# In-memory session store (lightweight, no DB needed)
_sessions: dict[str, list[dict]] = {}

# Simple query rewrite cache
_rewrite_cache: dict[str, str] = {}
_CACHE_MAX = 256


def index_documents(documents: list[dict]) -> int:
    """Index a batch of document chunks into ChromaDB.

    Each document dict should have:
        - id: str
        - text: str
        - metadata: dict
    """
    if not documents:
        return 0

    collection = get_chroma_collection()

    texts = [doc["text"] for doc in documents]
    embeddings = embed_texts(texts)

    ids = [doc["id"] for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]

    # Upsert to handle re-indexing
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    # Rebuild BM25 index after indexing
    rebuild_bm25_index()

    return len(documents)


def delete_by_source(source_type: str, file_name: str | None = None):
    """Delete all chunks from a specific source."""
    collection = get_chroma_collection()

    where_filter = {"source_type": source_type}
    if file_name:
        where_filter["file_name"] = file_name

    # Get matching docs
    result = collection.get(where=where_filter)
    if result["ids"]:
        collection.delete(ids=result["ids"])
        rebuild_bm25_index()

    return len(result["ids"])


def get_index_stats() -> dict:
    """Get statistics about the current index."""
    collection = get_chroma_collection()
    count = collection.count()

    if count == 0:
        return {"total_documents": 0, "total_chunks": 0, "source_breakdown": {}}

    # Sample to get source breakdown
    result = collection.get(include=["metadatas"])
    breakdown: dict[str, int] = {}
    for meta in result["metadatas"]:
        source_type = meta.get("source_type", "unknown")
        breakdown[source_type] = breakdown.get(source_type, 0) + 1

    # Count unique files
    seen_files = set()
    for meta in result["metadatas"]:
        seen_files.add(meta.get("file_name", "unknown"))

    return {
        "total_documents": len(seen_files),
        "total_chunks": count,
        "source_breakdown": breakdown,
    }


def _get_rewrite_cache_key(question: str, history: list[dict] | None) -> str:
    """Cache key based on question + last 2 history messages."""
    import hashlib
    h = question
    if history:
        recent = history[-2:]
        h += "".join(m.get("content", "")[:50] for m in recent)
    return hashlib.md5(h.encode()).hexdigest()


async def _rewrite_with_cache(question: str, history: list[dict] | None) -> str:
    """Rewrite query with caching."""
    key = _get_rewrite_cache_key(question, history)
    if key in _rewrite_cache:
        return _rewrite_cache[key]
    result = await rewrite_query(question, history)
    if len(_rewrite_cache) >= _CACHE_MAX:
        _rewrite_cache.pop(next(iter(_rewrite_cache)))
    _rewrite_cache[key] = result
    return result


async def chat(question: str, session_id: str | None = None) -> ChatResponse:
    """Optimized RAG pipeline: rewrite+retrieve in parallel, skip compression for short history."""
    sid = session_id or str(uuid.uuid4())
    history = _sessions.get(sid)

    # Parallel: rewrite query + retrieve with original query simultaneously
    rewrite_task = asyncio.create_task(_rewrite_with_cache(question, history))

    # Start retrieval with original query immediately
    original_sources = retrieve(question)
    search_query = await rewrite_task

    # If rewritten query differs, do a second retrieval and merge
    if search_query != question:
        rewritten_sources = retrieve(search_query)
        seen = {s.doc_id for s in original_sources}
        for src in rewritten_sources:
            if src.doc_id not in seen:
                original_sources.append(src)
                seen.add(src.doc_id)
    sources = original_sources[:settings.top_k]

    # Only compress history when it's long (>4 messages)
    compressed = None
    if history and len(history) > 4:
        compressed = await compress_history(history)

    answer = await generate_answer(question, sources, compressed)

    if sid not in _sessions:
        _sessions[sid] = []
    _sessions[sid].append({"role": "user", "content": question})
    _sessions[sid].append({"role": "assistant", "content": answer})

    return ChatResponse(
        answer=answer,
        sources=sources,
        session_id=sid,
    )


async def chat_stream(question: str, session_id: str | None = None):
    """Optimized streaming RAG pipeline."""
    import json

    sid = session_id or str(uuid.uuid4())
    history = _sessions.get(sid)

    # Parallel: rewrite + retrieve
    rewrite_task = asyncio.create_task(_rewrite_with_cache(question, history))
    original_sources = retrieve(question)
    search_query = await rewrite_task

    if search_query != question:
        rewritten_sources = retrieve(search_query)
        seen = {s.doc_id for s in original_sources}
        for src in rewritten_sources:
            if src.doc_id not in seen:
                original_sources.append(src)
                seen.add(src.doc_id)
    sources = original_sources[:settings.top_k]

    compressed = None
    if history and len(history) > 4:
        compressed = await compress_history(history)

    yield f"data: {json.dumps({'type': 'sources', 'sources': [s.model_dump() for s in sources], 'session_id': sid, 'search_query': search_query})}\n\n"

    full_answer = ""
    async for token in generate_answer_stream(question, sources, compressed):
        full_answer += token
        yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"

    if sid not in _sessions:
        _sessions[sid] = []
    _sessions[sid].append({"role": "user", "content": question})
    _sessions[sid].append({"role": "assistant", "content": full_answer})
