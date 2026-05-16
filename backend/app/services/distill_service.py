"""Chat distillation service.

Uses LLM to distill raw chat messages into structured knowledge notes.
"""

import json
from datetime import datetime

from openai import AsyncOpenAI

from app.config import settings
from app.loaders.wechat import (
    WeFlowClient,
    parse_message,
    group_messages_by_session,
    format_session_for_distill,
    _parse_timestamp,
)

DISTILL_PROMPT = """你是一个知识蒸馏助手。请将以下微信聊天记录提炼成结构化的知识笔记。

规则：
1. 提取关键信息：知识点、决策、待办事项、重要结论
2. 忽略无意义的寒暄、表情包、重复内容
3. 保留重要的时间、数字、人名等细节
4. 用中文输出，格式如下：

## 输出格式
```json
{
  "title": "简短标题（10字以内）",
  "summary": "一段话总结（50-100字）",
  "key_points": ["要点1", "要点2", ...],
  "action_items": ["待办1", "待办2", ...],
  "tags": ["标签1", "标签2", ...]
}
```

如果聊天内容没有实质性信息，返回：
```json
{"title": "", "summary": "", "key_points": [], "action_items": [], "tags": [], "skip": true}
```"""


async def distill_session(
    messages: list[dict],
    talker_name: str,
    client: AsyncOpenAI | None = None,
) -> dict | None:
    """Distill a single chat session into a structured note.

    Returns None if the session has no valuable content.
    """
    if not client:
        client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )

    formatted = format_session_for_distill(messages, talker_name)
    if len(formatted.strip()) < 30:
        return None

    response = await client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[
            {"role": "system", "content": DISTILL_PROMPT},
            {"role": "user", "content": formatted},
        ],
        temperature=0.2,
        max_tokens=500,
    )

    content = response.choices[0].message.content or ""

    # Extract JSON from response
    try:
        # Try to find JSON block
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content.strip()

        result = json.loads(json_str)
        if result.get("skip"):
            return None
        return result
    except (json.JSONDecodeError, IndexError):
        return None


async def distill_chat_history(
    talker: str,
    talker_name: str = "",
    weflow_url: str = "http://127.0.0.1:5031",
    weflow_token: str = "",
    max_messages: int = 2000,
) -> list[dict]:
    """Full distillation pipeline: fetch messages -> group -> distill -> return docs.

    Returns a list of document dicts ready for indexing.
    """
    client = WeFlowClient(weflow_url, weflow_token)
    messages = await client.get_all_messages(talker, max_messages)

    if not messages:
        return []

    parsed = [parse_message(m) for m in messages]
    sessions = group_messages_by_session(parsed)
    name = talker_name or talker

    llm_client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    documents = []
    for session_idx, session in enumerate(sessions):
        if len(session) < 3:  # Skip very short sessions
            continue

        distilled = await distill_session(session, name, llm_client)
        if not distilled:
            continue

        # Build document from distilled result
        start_time = _parse_timestamp(session[0].get("time", 0))
        end_time = _parse_timestamp(session[-1].get("time", 0))

        # Build rich text for indexing
        note_text = f"""# {distilled['title']}

{distilled['summary']}

## 要点
{chr(10).join(f'- {p}' for p in distilled['key_points'])}

## 待办
{chr(10).join(f'- {a}' for a in distilled.get('action_items', [])) if distilled.get('action_items') else '无'}

## 原始对话摘要
- 聊天对象: {name}
- 时间: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}
- 消息数: {len(session)}
- 标签: {', '.join(distilled.get('tags', []))}
"""

        import hashlib
        content_hash = hashlib.md5(note_text.encode()).hexdigest()[:8]

        documents.append({
            "id": f"wechat-distilled:{name}:{session_idx}:{content_hash}",
            "text": note_text,
            "metadata": {
                "source_type": "wechat",
                "file_name": f"微信-{name}",
                "heading_path": f"{name} > {distilled['title']}",
                "talker": name,
                "session_start": start_time.isoformat(),
                "session_end": end_time.isoformat(),
                "msg_count": len(session),
                "tags": ",".join(distilled.get("tags", [])),
                "content_hash": content_hash,
                "distilled": True,
            },
        })

    return documents
