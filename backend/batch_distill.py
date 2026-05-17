"""Batch distill all WeChat contacts via WeFlow API.

Features:
- Auto-retry when hook disconnects
- Resume from last position (saves progress)
- Skip already-processed contacts

Run: python batch_distill.py
"""

import asyncio
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.loaders.wechat import WeFlowClient
from app.services.distill_service import distill_chat_history
from app.rag.pipeline import index_documents

WEFLOW_TOKEN = settings.weflow_token
PROGRESS_FILE = Path(__file__).parent / "distill_progress.json"
RETRY_WAIT = 30  # seconds to wait before retry on hook disconnect
MAX_RETRIES = 10


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {"done": [], "results": []}


def save_progress(progress: dict):
    PROGRESS_FILE.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


async def wait_for_hook(client: WeFlowClient) -> bool:
    """Wait until hook reconnects."""
    for attempt in range(MAX_RETRIES):
        try:
            contacts = await client.get_contacts()
            if contacts:
                # Test if messages work
                test_id = contacts[0].get("username", "")
                if test_id:
                    msgs = await client.get_all_messages(test_id, 3)
                    if len(msgs) > 0:
                        return True
            print(f"  Hook disconnected, waiting {RETRY_WAIT}s... (attempt {attempt+1}/{MAX_RETRIES})")
        except Exception:
            print(f"  WeFlow API error, waiting {RETRY_WAIT}s... (attempt {attempt+1}/{MAX_RETRIES})")
        await asyncio.sleep(RETRY_WAIT)
    return False


async def batch_distill():
    """Batch distill all friend and group contacts with auto-retry."""
    client = WeFlowClient(settings.weflow_url, WEFLOW_TOKEN)
    progress = load_progress()
    done_set = set(progress["done"])

    contacts = await client.get_contacts()
    print(f"Total contacts: {len(contacts)}")

    targets = [
        c for c in contacts
        if c.get("type") in ("friend", "group")
    ]
    print(f"Friends + Groups: {len(targets)}")
    print(f"Already processed: {len(done_set)}")

    results = progress["results"]
    consecutive_errors = 0

    for i, contact in enumerate(targets):
        talker = contact.get("username", "")
        name = contact.get("displayName") or contact.get("nickname") or talker

        if talker in done_set:
            print(f"[{i+1}/{len(targets)}] {name} - already done, skip")
            continue

        print(f"\n[{i+1}/{len(targets)}] {name}")

        # Try with retry on hook disconnect
        success = False
        for attempt in range(3):
            try:
                docs = await distill_chat_history(
                    talker=talker,
                    talker_name=name,
                    weflow_url=settings.weflow_url,
                    weflow_token=WEFLOW_TOKEN,
                    max_messages=2000,
                )

                if docs:
                    count = index_documents(docs)
                    print(f"  -> {count} chunks indexed")
                    results.append({"name": name, "talker": talker, "chunks": count, "status": "ok"})
                else:
                    print(f"  -> no valuable content")
                    results.append({"name": name, "talker": talker, "chunks": 0, "status": "skip"})

                done_set.add(talker)
                progress["done"] = list(done_set)
                progress["results"] = results
                save_progress(progress)
                consecutive_errors = 0
                success = True
                break

            except Exception as e:
                err = str(e)
                if "401" in err or "empty" in err.lower() or "count" in err.lower():
                    # Hook likely disconnected
                    print(f"  -> hook issue, waiting for reconnect...")
                    reconnected = await wait_for_hook(client)
                    if not reconnected:
                        print(f"  -> hook not reconnecting, skipping")
                        break
                    print(f"  -> hook reconnected, retrying...")
                else:
                    print(f"  -> error: {err[:80]}")
                    break

        if not success:
            consecutive_errors += 1
            results.append({"name": name, "talker": talker, "chunks": 0, "status": "error"})
            done_set.add(talker)
            progress["done"] = list(done_set)
            progress["results"] = results
            save_progress(progress)

            if consecutive_errors >= 5:
                print(f"\n{consecutive_errors} consecutive errors. Hook seems unstable.")
                print("Please reconnect WeFlow hook and run again.")
                print(f"Progress saved ({len(done_set)}/{len(targets)} done)")
                return

    # Summary
    ok = [r for r in results if r["status"] == "ok"]
    skipped = [r for r in results if r["status"] == "skip"]
    errors = [r for r in results if r["status"] == "error"]
    total_chunks = sum(r["chunks"] for r in results)

    print(f"\n{'='*50}")
    print(f"Done! {len(ok)} imported, {len(skipped)} skipped, {len(errors)} errors")
    print(f"Total chunks: {total_chunks}")

    with open("distill_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Results saved to distill_results.json")


if __name__ == "__main__":
    print("Starting batch distillation (with auto-retry)...")
    print("Press Ctrl+C to stop. Progress will be saved.\n")
    try:
        asyncio.run(batch_distill())
    except KeyboardInterrupt:
        print("\nInterrupted. Progress saved, run again to resume.")
