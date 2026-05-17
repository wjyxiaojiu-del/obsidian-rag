from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models import SourceType
from app.loaders.wechat import load_wechat_chat, WeFlowClient
from app.services.distill_service import distill_chat_history
from app.rag.pipeline import index_documents

router = APIRouter(prefix="/api/wechat", tags=["wechat"])


@router.get("/contacts")
async def get_contacts(
    weflow_url: str = "",
    weflow_token: str = "",
):
    """Get WeChat contact list from WeFlow."""
    try:
        client = WeFlowClient(
            weflow_url or settings.weflow_url,
            weflow_token or settings.weflow_token,
        )
        contacts = await client.get_contacts()
        return {"contacts": contacts, "count": len(contacts)}
    except Exception as e:
        raise HTTPException(500, f"Failed to connect to WeFlow: {e}")


@router.post("/import")
async def import_chat(
    talker: str,
    talker_name: str = "",
    distill: bool = False,
    max_messages: int = 2000,
    weflow_url: str = "",
    weflow_token: str = "",
):
    """Import WeChat chat history into knowledge base.

    Args:
        talker: wxid of the contact/group
        talker_name: display name (optional)
        distill: if True, use LLM to distill messages into structured notes
        max_messages: max messages to fetch
        weflow_url: WeFlow HTTP API URL
        weflow_token: WeFlow auth token
    """
    try:
        _url = weflow_url or settings.weflow_url
        _token = weflow_token or settings.weflow_token
        if distill:
            docs = await distill_chat_history(
                talker=talker,
                talker_name=talker_name,
                weflow_url=_url,
                weflow_token=_token,
                max_messages=max_messages,
            )
        else:
            docs = await load_wechat_chat(
                talker=talker,
                talker_name=talker_name,
                weflow_url=_url,
                weflow_token=_token,
                max_messages=max_messages,
            )

        if not docs:
            raise HTTPException(404, "No messages found or no valuable content to index")

        count = index_documents(docs)
        mode = "distilled" if distill else "raw"
        return {
            "message": f"Indexed {count} chunks from {talker_name or talker} ({mode} mode)",
            "chunks": count,
            "mode": mode,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error importing chat: {e}")


@router.post("/import-batch")
async def import_batch(
    talkers: list[dict],
    distill: bool = True,
    max_messages: int = 1000,
    weflow_url: str = "",
    weflow_token: str = "",
):
    """Batch import multiple chats.

    Body: [{"talker": "wxid_xxx", "name": "张三"}, ...]
    """
    _url = weflow_url or settings.weflow_url
    _token = weflow_token or settings.weflow_token
    results = []
    for item in talkers:
        talker = item.get("talker", "")
        name = item.get("name", "")
        if not talker:
            continue

        try:
            if distill:
                docs = await distill_chat_history(
                    talker, name, _url, _token, max_messages
                )
            else:
                docs = await load_wechat_chat(
                    talker, name, _url, _token, max_messages
                )

            if docs:
                count = index_documents(docs)
                results.append({"talker": talker, "name": name, "chunks": count, "status": "ok"})
            else:
                results.append({"talker": talker, "name": name, "chunks": 0, "status": "no_data"})
        except Exception as e:
            results.append({"talker": talker, "name": name, "chunks": 0, "status": f"error: {e}"})

    return {"results": results}
