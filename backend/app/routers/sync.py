from fastapi import APIRouter, BackgroundTasks

from app.services.sync_service import sync_vault, get_sync_status
from app.models import SyncStatus

router = APIRouter(prefix="/api/sync", tags=["sync"])

_sync_in_progress = False


@router.post("", response_model=dict)
async def trigger_sync(background_tasks: BackgroundTasks):
    """Trigger Obsidian vault sync."""
    global _sync_in_progress
    if _sync_in_progress:
        return {"message": "Sync already in progress"}

    _sync_in_progress = True

    def do_sync():
        global _sync_in_progress
        try:
            sync_vault()
        finally:
            _sync_in_progress = False

    background_tasks.add_task(do_sync)
    return {"message": "Sync started in background"}


@router.post("/full", response_model=dict)
async def trigger_full_sync():
    """Full re-index of Obsidian vault (blocking)."""
    global _sync_in_progress
    if _sync_in_progress:
        return {"message": "Sync already in progress"}

    _sync_in_progress = True
    try:
        result = sync_vault()
        return {"message": "Full sync completed", **result}
    finally:
        _sync_in_progress = False


@router.get("/status", response_model=SyncStatus)
async def sync_status():
    """Get current sync status."""
    status = get_sync_status()
    return SyncStatus(
        total_files=status["total_files"],
        indexed_files=status["indexed_files"],
        new_files=0,
        updated_files=0,
        removed_files=0,
        is_syncing=_sync_in_progress,
    )
