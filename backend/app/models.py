from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class SourceType(str, Enum):
    OBSIDIAN = "obsidian"
    PDF = "pdf"
    WEB = "web"


class SourceRef(BaseModel):
    """A reference to the source document for citation."""
    doc_id: str
    file_name: str
    source_type: SourceType
    chunk_text: str
    score: float = 0.0
    # Obsidian-specific
    vault_path: Optional[str] = None
    heading_path: Optional[str] = None
    # Web-specific
    url: Optional[str] = None


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceRef]
    session_id: str


class DocumentInfo(BaseModel):
    doc_id: str
    file_name: str
    source_type: SourceType
    chunk_count: int
    last_indexed: str


class SyncStatus(BaseModel):
    total_files: int
    indexed_files: int
    new_files: int
    updated_files: int
    removed_files: int
    is_syncing: bool


class WebIngestRequest(BaseModel):
    url: str = Field(..., min_length=1)
    title: Optional[str] = None


class PDFIngestRequest(BaseModel):
    file_name: str


class IndexStats(BaseModel):
    total_documents: int
    total_chunks: int
    source_breakdown: dict[str, int]
