"""Obsidian vault loader.

Parses Markdown files with Obsidian-specific features:
- Wikilinks [[page]] and [[page|alias]]
- Tags #tag
- YAML frontmatter
- Heading hierarchy for chunking context
"""

import re
import hashlib
from pathlib import Path
from datetime import datetime

import yaml


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and return (metadata, body)."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if match:
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            meta = {}
        body = content[match.end():]
        return meta, body
    return {}, content


def strip_wikilinks(text: str) -> str:
    """Convert [[wikilink]] and [[wikilink|alias]] to plain text."""
    # [[page|alias]] -> alias
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    # [[page]] -> page
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    return text


def extract_tags(content: str) -> list[str]:
    """Extract #tags from content."""
    tags = re.findall(r"(?:^|\s)#([a-zA-Z一-鿿][\w一-鿿/]*)", content)
    return list(set(tags))


def extract_headings(content: str) -> list[tuple[int, str]]:
    """Extract heading hierarchy: [(level, text), ...]."""
    headings = []
    for match in re.finditer(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE):
        headings.append((len(match.group(1)), match.group(2).strip()))
    return headings


def chunk_by_headings(content: str, file_name: str) -> list[dict]:
    """Split document by headings, preserving heading context."""
    lines = content.split("\n")
    chunks = []
    current_heading_path = []
    current_text = []
    current_start = 0

    for i, line in enumerate(lines):
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            # Save previous chunk
            if current_text:
                text = "\n".join(current_text).strip()
                if len(text) > 50:  # Skip very short chunks
                    chunks.append({
                        "text": text,
                        "heading_path": " > ".join(current_heading_path) if current_heading_path else None,
                        "start_line": current_start,
                        "end_line": i,
                    })

            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()

            # Update heading path
            while current_heading_path and len(current_heading_path) >= level:
                current_heading_path.pop()
            current_heading_path.append(heading_text)

            current_text = [line]
            current_start = i
        else:
            current_text.append(line)

    # Last chunk
    if current_text:
        text = "\n".join(current_text).strip()
        if len(text) > 50:
            chunks.append({
                "text": text,
                "heading_path": " > ".join(current_heading_path) if current_heading_path else None,
                "start_line": current_start,
                "end_line": len(lines),
            })

    # If no headings found, treat as single chunk
    if not chunks:
        text = content.strip()
        if len(text) > 50:
            chunks.append({
                "text": text,
                "heading_path": None,
                "start_line": 0,
                "end_line": len(lines),
            })

    return chunks


def long_chunk_fallback(text: str, heading_path: str | None, chunk_size: int = 512, overlap: int = 64) -> list[dict]:
    """Split long chunks by character count with overlap."""
    if len(text) <= chunk_size:
        return [{"text": text, "heading_path": heading_path}]

    sub_chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        sub_text = text[start:end]
        if len(sub_text.strip()) > 50:
            sub_chunks.append({
                "text": sub_text.strip(),
                "heading_path": heading_path,
            })
        start += chunk_size - overlap
    return sub_chunks


def load_obsidian_file(file_path: Path, vault_root: Path) -> list[dict]:
    """Load a single Obsidian markdown file and return document chunks."""
    content = file_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    # Clean content
    clean_body = strip_wikilinks(body)
    tags = extract_tags(content)
    file_name = file_path.stem
    relative_path = str(file_path.relative_to(vault_root))

    # Chunk by headings
    raw_chunks = chunk_by_headings(clean_body, file_name)

    # Further split long chunks
    chunks = []
    for chunk in raw_chunks:
        sub_chunks = long_chunk_fallback(chunk["text"], chunk.get("heading_path"))
        for sc in sub_chunks:
            chunks.append(sc)

    # Build documents for indexing
    documents = []
    for i, chunk in enumerate(chunks):
        doc_id = f"obsidian:{relative_path}:{i}"
        # Stable hash for dedup
        content_hash = hashlib.md5(chunk["text"].encode()).hexdigest()[:8]
        doc_id = f"obsidian:{relative_path}:{content_hash}"

        metadata = {
            "source_type": "obsidian",
            "file_name": file_name,
            "file_path": relative_path,
            "vault_path": str(file_path),
            "heading_path": chunk.get("heading_path"),
            "tags": ",".join(tags) if tags else "",
            "created": frontmatter.get("date", frontmatter.get("created", "")),
            "content_hash": content_hash,
        }

        documents.append({
            "id": doc_id,
            "text": chunk["text"],
            "metadata": metadata,
        })

    return documents


def load_vault(vault_path: Path, exclude_patterns: list[str] | None = None) -> list[dict]:
    """Load all markdown files from an Obsidian vault."""
    if exclude_patterns is None:
        exclude_patterns = [
            ".obsidian/**",
            ".claude/**",
            ".claudian/**",
            ".infio_json_db/**",
            ".smtcmp_json_db/**",
            "**/.git/**",
            "**/node_modules/**",
        ]

    all_documents = []
    md_files = list(vault_path.rglob("*.md"))

    for md_file in md_files:
        relative = md_file.relative_to(vault_path)
        parts = relative.parts
        # Skip hidden dirs, node_modules, .git
        if any(part.startswith(".") or part in ("node_modules", ".git") for part in parts):
            continue

        try:
            docs = load_obsidian_file(md_file, vault_path)
            all_documents.extend(docs)
        except Exception as e:
            print(f"Error loading {relative}: {e}")

    return all_documents


def scan_vault(vault_path: Path) -> list[dict]:
    """Scan vault and return file info without full parsing (for sync status)."""
    md_files = list(vault_path.rglob("*.md"))
    files = []
    for md_file in md_files:
        relative = md_file.relative_to(vault_path)
        if any(part.startswith(".") for part in relative.parts):
            continue
        stat = md_file.stat()
        files.append({
            "path": str(relative),
            "name": md_file.stem,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return files
