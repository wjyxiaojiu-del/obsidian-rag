"""Obsidian vault sync service.

Tracks file changes and incrementally updates the index.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.loaders.obsidian import load_obsidian_file
from app.rag.pipeline import index_documents, delete_by_source

# Sync state file
_STATE_FILE = Path(settings.chroma_persist_dir) / "sync_state.json"


def _load_state() -> dict:
    if _STATE_FILE.exists():
        return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    return {"indexed_files": {}, "last_sync": None}


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _file_hash(file_path: Path) -> str:
    """Quick hash based on file size + mtime (not content)."""
    stat = file_path.stat()
    return hashlib.md5(f"{stat.st_size}:{stat.st_mtime}".encode()).hexdigest()


def sync_vault(vault_path: Path | None = None) -> dict:
    """Sync Obsidian vault with the vector index.

    Returns sync stats: {new, updated, removed, total_indexed}.
    """
    vault = vault_path or Path(settings.obsidian_vault_path)
    state = _load_state()
    indexed = state.get("indexed_files", {})

    # Scan current files
    current_files: dict[str, dict] = {}
    for md_file in vault.rglob("*.md"):
        relative = str(md_file.relative_to(vault))
        parts = Path(relative).parts
        # Skip hidden dirs and node_modules
        if any(part.startswith(".") or part == "node_modules" for part in parts):
            continue
        current_files[relative] = {
            "path": str(md_file),
            "hash": _file_hash(md_file),
        }

    new_files = []
    updated_files = []
    removed_files = []

    # Find new and updated files
    for rel_path, info in current_files.items():
        if rel_path not in indexed:
            new_files.append(rel_path)
        elif indexed[rel_path]["hash"] != info["hash"]:
            updated_files.append(rel_path)

    # Find removed files
    for rel_path in indexed:
        if rel_path not in current_files:
            removed_files.append(rel_path)

    # Process removals
    for rel_path in removed_files:
        # Delete all chunks from this file
        collection_chunks = indexed[rel_path].get("chunk_ids", [])
        if collection_chunks:
            from app.rag.retriever import get_chroma_collection
            collection = get_chroma_collection()
            try:
                collection.delete(ids=collection_chunks)
            except Exception:
                pass
        del indexed[rel_path]

    # Process new and updated files
    files_to_index = new_files + updated_files
    for rel_path in files_to_index:
        md_file = Path(current_files[rel_path]["path"])
        try:
            # Remove old chunks if updating
            if rel_path in indexed:
                old_chunk_ids = indexed[rel_path].get("chunk_ids", [])
                if old_chunk_ids:
                    from app.rag.retriever import get_chroma_collection
                    collection = get_chroma_collection()
                    try:
                        collection.delete(ids=old_chunk_ids)
                    except Exception:
                        pass

            # Index new chunks
            docs = load_obsidian_file(md_file, vault)
            if docs:
                index_documents(docs)
                indexed[rel_path] = {
                    "hash": current_files[rel_path]["hash"],
                    "chunk_ids": [d["id"] for d in docs],
                    "indexed_at": datetime.now().isoformat(),
                }
        except Exception as e:
            print(f"Error indexing {rel_path}: {e}")

    # Save state
    state["indexed_files"] = indexed
    state["last_sync"] = datetime.now().isoformat()
    _save_state(state)

    return {
        "new": len(new_files),
        "updated": len(updated_files),
        "removed": len(removed_files),
        "total_indexed": len(indexed),
        "total_files": len(current_files),
    }


def get_sync_status() -> dict:
    """Get current sync status without performing sync."""
    state = _load_state()
    vault = Path(settings.obsidian_vault_path)

    # Count current files
    total_files = 0
    for md_file in vault.rglob("*.md"):
        relative = str(md_file.relative_to(vault))
        parts = Path(relative).parts
        if not any(part.startswith(".") or part == "node_modules" for part in parts):
            total_files += 1

    return {
        "total_files": total_files,
        "indexed_files": len(state.get("indexed_files", {})),
        "last_sync": state.get("last_sync"),
        "is_syncing": False,
    }
