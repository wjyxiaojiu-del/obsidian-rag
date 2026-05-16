"""WeChat chat history loader via WeFlow HTTP API.

WeFlow (https://github.com/hicccc77/WeFlow) is an Electron app that
reads local WeChat database and exposes HTTP API at localhost:5031.

Key endpoints:
  GET /api/v1/messages?talker=wxid_xxx&limit=100&chatlab=1
  GET /api/v1/contacts (if available)
"""

import hashlib
from datetime import datetime
from typing import Optional

import httpx


class WeFlowClient:
    """Client for WeFlow HTTP API."""

    def __init__(self, base_url: str = "http://127.0.0.1:5031", token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    async def _get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}{path}",
                params=params,
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_contacts(self) -> list[dict]:
        """Get contact list."""
        data = await self._get("/api/v1/contacts")
        if isinstance(data, list):
            return data
        return data.get("data", data.get("contacts", []))

    async def get_messages(
        self,
        talker: str,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        """Get messages for a specific chat.

        Args:
            talker: wxid of the contact or group
            limit: max messages to fetch
            offset: pagination offset
        """
        params = {
            "talker": talker,
            "limit": limit,
            "offset": offset,
            "chatlab": 1,
        }
        data = await self._get("/api/v1/messages", params=params)

        if isinstance(data, list):
            return data
        return data.get("data", data.get("messages", []))

    async def get_all_messages(
        self,
        talker: str,
        max_messages: int = 2000,
    ) -> list[dict]:
        """Fetch all messages for a talker with pagination."""
        all_msgs = []
        offset = 0
        batch_size = 200

        while len(all_msgs) < max_messages:
            msgs = await self.get_messages(talker, limit=batch_size, offset=offset)
            if not msgs:
                break
            all_msgs.extend(msgs)
            offset += len(msgs)
            if len(msgs) < batch_size:
                break

        return all_msgs[:max_messages]


def parse_message(msg: dict) -> dict:
    """Parse a single WeFlow message into a normalized format."""
    return {
        "sender": msg.get("senderUsername", msg.get("sender", "unknown")),
        "content": msg.get("content", msg.get("msg", "")),
        "time": msg.get("createTime", msg.get("timestamp", "")),
        "type": msg.get("mediaType", msg.get("type", 1)),
        "is_group": msg.get("isGroup", False),
        "talker": msg.get("talker", ""),
    }


def group_messages_by_session(
    messages: list[dict],
    gap_minutes: int = 30,
) -> list[list[dict]]:
    """Group messages into conversation sessions by time gap.

    Messages within `gap_minutes` of each other are considered one session.
    """
    if not messages:
        return []

    # Sort by time
    sorted_msgs = sorted(messages, key=lambda m: m.get("time", 0))

    sessions = []
    current_session = [sorted_msgs[0]]

    for i in range(1, len(sorted_msgs)):
        prev_time = _parse_timestamp(sorted_msgs[i - 1].get("time", 0))
        curr_time = _parse_timestamp(sorted_msgs[i].get("time", 0))

        gap = (curr_time - prev_time).total_seconds() / 60

        if gap > gap_minutes:
            sessions.append(current_session)
            current_session = [sorted_msgs[i]]
        else:
            current_session.append(sorted_msgs[i])

    if current_session:
        sessions.append(current_session)

    return sessions


def _parse_timestamp(ts) -> datetime:
    """Parse various timestamp formats."""
    if isinstance(ts, (int, float)):
        if ts > 1e12:  # milliseconds
            return datetime.fromtimestamp(ts / 1000)
        return datetime.fromtimestamp(ts)
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return datetime.now()
    return datetime.now()


def format_session_for_distill(messages: list[dict], talker_name: str = "") -> str:
    """Format a message session into readable text for LLM distillation."""
    lines = []
    for msg in messages:
        sender = msg.get("sender", "unknown")
        content = msg.get("content", "")
        ts = _parse_timestamp(msg.get("time", 0))
        time_str = ts.strftime("%Y-%m-%d %H:%M")

        # Skip empty or system messages
        if not content or content.startswith("<?xml"):
            continue
        if "[图片]" in content or "[视频]" in content or "[语音]" in content:
            content = content  # keep as-is

        lines.append(f"[{time_str}] {sender}: {content}")

    header = f"## 聊天对象: {talker_name}\n" if talker_name else ""
    return header + "\n".join(lines)


def chunk_chat_sessions(
    sessions: list[list[dict]],
    talker_name: str = "",
    max_chunk_chars: int = 2000,
) -> list[dict]:
    """Convert chat sessions into document chunks for indexing.

    Each session becomes one or more chunks.
    """
    documents = []

    for session_idx, session in enumerate(sessions):
        if not session:
            continue

        formatted = format_session_for_distill(session, talker_name)

        if len(formatted) < 50:
            continue

        # Split long sessions
        chunks = _split_text(formatted, max_chunk_chars)

        for chunk_idx, chunk_text in enumerate(chunks):
            first_msg = session[0]
            last_msg = session[-1]
            start_time = _parse_timestamp(first_msg.get("time", 0))
            end_time = _parse_timestamp(last_msg.get("time", 0))

            content_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
            doc_id = f"wechat:{talker_name}:{session_idx}:{chunk_idx}:{content_hash}"

            documents.append({
                "id": doc_id,
                "text": chunk_text,
                "metadata": {
                    "source_type": "wechat",
                    "file_name": f"微信-{talker_name}",
                    "heading_path": f"{talker_name} > {start_time.strftime('%Y-%m-%d')}",
                    "talker": talker_name,
                    "session_start": start_time.isoformat(),
                    "session_end": end_time.isoformat(),
                    "msg_count": len(session),
                    "content_hash": content_hash,
                },
            })

    return documents


def _split_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks respecting line boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    lines = text.split("\n")
    current = []

    for line in lines:
        current.append(line)
        if sum(len(l) for l in current) >= max_chars:
            chunks.append("\n".join(current))
            current = []

    if current:
        chunks.append("\n".join(current))

    return chunks


async def load_wechat_chat(
    talker: str,
    talker_name: str = "",
    weflow_url: str = "http://127.0.0.1:5031",
    weflow_token: str = "",
    max_messages: int = 2000,
) -> list[dict]:
    """Load and chunk WeChat messages for a specific talker."""
    client = WeFlowClient(weflow_url, weflow_token)
    messages = await client.get_all_messages(talker, max_messages)

    if not messages:
        return []

    parsed = [parse_message(m) for m in messages]
    sessions = group_messages_by_session(parsed)
    return chunk_chat_sessions(sessions, talker_name or talker)
