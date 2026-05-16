"""PDF document loader with text extraction."""

import hashlib
from pathlib import Path

from pypdf import PdfReader


def load_pdf(file_path: Path, chunk_size: int = 512, overlap: int = 64) -> list[dict]:
    """Load a PDF file and return document chunks."""
    reader = PdfReader(str(file_path))
    file_name = file_path.stem

    full_text = ""
    page_map = []  # (char_start, page_number)

    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        page_map.append((len(full_text), i + 1))
        full_text += page_text + "\n\n"

    if not full_text.strip():
        return []

    # Chunk by character count with overlap
    documents = []
    start = 0
    chunk_idx = 0

    while start < len(full_text):
        end = min(start + chunk_size, len(full_text))
        chunk_text = full_text[start:end].strip()

        if len(chunk_text) < 50:
            start += chunk_size - overlap
            continue

        # Find which page this chunk belongs to
        page_num = 1
        for char_start, pn in page_map:
            if char_start <= start:
                page_num = pn

        content_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
        doc_id = f"pdf:{file_name}:{content_hash}"

        documents.append({
            "id": doc_id,
            "text": chunk_text,
            "metadata": {
                "source_type": "pdf",
                "file_name": file_name,
                "file_path": str(file_path),
                "page_number": page_num,
                "heading_path": f"Page {page_num}",
                "content_hash": content_hash,
            },
        })

        start += chunk_size - overlap
        chunk_idx += 1

    return documents
