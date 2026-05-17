"""Batch distill WeChat HTML exports into the RAG knowledge base.

Run: python batch_distill_html.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))

from app.loaders.wechat import (
    load_html_export,
    group_messages_by_session,
    _parse_timestamp,
)
from app.services.distill_service import distill_session, _get_client
from app.rag.pipeline import index_documents

EXPORT_DIR = r"E:\小九\聊天记录导出\texts"
PROGRESS_FILE = Path(__file__).parent / "distill_html_progress.json"


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {"done": [], "results": []}


def save_progress(progress: dict):
    PROGRESS_FILE.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


async def distill_html_export():
    """Process all HTML exports: parse -> group sessions -> distill -> index."""
    all_contacts = load_html_export(EXPORT_DIR)
    print(f"Found {len(all_contacts)} contacts in HTML export")

    progress = load_progress()
    done_set = set(progress["done"])
    results = progress["results"]

    print(f"Already processed: {len(done_set)}")

    llm_client = _get_client()

    for contact_name, messages in all_contacts.items():
        if contact_name in done_set:
            print(f"[skip] {contact_name} - already done")
            continue

        print(f"\n[process] {contact_name} ({len(messages)} messages)")

        sessions = group_messages_by_session(messages)
        print(f"  Grouped into {len(sessions)} sessions")

        documents = []
        for session_idx, session in enumerate(sessions):
            if len(session) < 3:
                continue

            try:
                distilled = await distill_session(session, contact_name, llm_client)
            except Exception as e:
                print(f"  Session {session_idx} distill error: {e}")
                continue

            if not distilled:
                continue

            start_time = _parse_timestamp(session[0].get("time", 0))
            end_time = _parse_timestamp(session[-1].get("time", 0))

            note_text = f"""# {distilled['title']}

{distilled['summary']}

## 要点
{chr(10).join(f'- {p}' for p in distilled['key_points'])}

## 待办
{chr(10).join(f'- {a}' for a in distilled.get('action_items', [])) if distilled.get('action_items') else '无'}

## 原始对话摘要
- 聊天对象: {contact_name}
- 时间: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}
- 消息数: {len(session)}
- 标签: {', '.join(distilled.get('tags', []))}
"""

            import hashlib
            content_hash = hashlib.md5(note_text.encode()).hexdigest()[:8]

            documents.append({
                "id": f"wechat-html:{contact_name}:{session_idx}:{content_hash}",
                "text": note_text,
                "metadata": {
                    "source_type": "wechat",
                    "file_name": f"微信-{contact_name}",
                    "heading_path": f"{contact_name} > {distilled['title']}",
                    "talker": contact_name,
                    "session_start": start_time.isoformat(),
                    "session_end": end_time.isoformat(),
                    "msg_count": len(session),
                    "tags": ",".join(distilled.get("tags", [])),
                    "content_hash": content_hash,
                    "distilled": True,
                },
            })

        if documents:
            count = index_documents(documents)
            print(f"  -> {count} chunks indexed")
            results.append({"name": contact_name, "chunks": count, "status": "ok", "msg_count": len(messages)})
        else:
            print(f"  -> no valuable content")
            results.append({"name": contact_name, "chunks": 0, "status": "skip", "msg_count": len(messages)})

        done_set.add(contact_name)
        progress["done"] = list(done_set)
        progress["results"] = results
        save_progress(progress)

    # Summary
    ok = [r for r in results if r["status"] == "ok"]
    skipped = [r for r in results if r["status"] == "skip"]
    total_chunks = sum(r["chunks"] for r in results)

    print(f"\n{'='*50}")
    print(f"Done! {len(ok)} imported, {len(skipped)} skipped")
    print(f"Total chunks: {total_chunks}")


if __name__ == "__main__":
    print("Starting HTML export distillation...")
    print("Press Ctrl+C to stop. Progress will be saved.\n")
    try:
        asyncio.run(distill_html_export())
    except KeyboardInterrupt:
        print("\nInterrupted. Progress saved, run again to resume.")
