from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models import ChatRequest, ChatResponse
from app.rag.pipeline import chat, chat_stream

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """RAG chat endpoint (non-streaming)."""
    result = await chat(request.question, request.session_id)
    return result


@router.post("/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """RAG chat endpoint with SSE streaming."""
    return StreamingResponse(
        chat_stream(request.question, request.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
