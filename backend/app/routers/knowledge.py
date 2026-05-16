import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import settings
from app.models import WebIngestRequest, IndexStats
from app.loaders.pdf import load_pdf
from app.loaders.web import load_webpage
from app.rag.pipeline import index_documents, delete_by_source, get_index_stats
from app.rag.retriever import rebuild_bm25_index

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/stats", response_model=IndexStats)
async def stats():
    """Get index statistics."""
    data = get_index_stats()
    return IndexStats(**data)


@router.post("/pdf")
async def ingest_pdf(file: UploadFile = File(...)):
    """Upload and index a PDF file."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    # Save to temp location
    tmp_dir = Path(settings.chroma_persist_dir) / "pdfs"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / file.filename

    with open(tmp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        docs = load_pdf(tmp_path)
        if not docs:
            raise HTTPException(400, "Could not extract text from PDF")
        count = index_documents(docs)
        return {"message": f"Indexed {count} chunks from {file.filename}", "chunks": count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error processing PDF: {e}")


@router.post("/web")
async def ingest_web(request: WebIngestRequest):
    """Fetch and index a web page."""
    try:
        docs = await load_webpage(request.url)
        if not docs:
            raise HTTPException(400, "Could not extract text from URL")
        if request.title:
            for doc in docs:
                doc["metadata"]["file_name"] = request.title
        count = index_documents(docs)
        return {"message": f"Indexed {count} chunks from {request.url}", "chunks": count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error fetching URL: {e}")


@router.delete("/{source_type}")
async def delete_source(source_type: str, file_name: str | None = None):
    """Delete all chunks from a specific source type."""
    count = delete_by_source(source_type, file_name)
    return {"message": f"Deleted {count} chunks", "deleted": count}


@router.post("/rebuild-index")
async def rebuild_index():
    """Rebuild BM25 index from current ChromaDB data."""
    rebuild_bm25_index()
    return {"message": "BM25 index rebuilt successfully"}
