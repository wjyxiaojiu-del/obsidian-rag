from openai import AsyncOpenAI
from app.config import settings

_client: AsyncOpenAI | None = None

COMPRESS_PROMPT = """你是一个对话摘要助手。将对话历史压缩为简短摘要，保留关键信息。

规则：
1. 保留用户的核心问题和需求
2. 保留助手回答中的关键结论
3. 丢弃寒暄、重复、格式细节
4. 摘要控制在200字以内
5. 使用第三人称叙述（"用户询问了...助手回答了..."）
"""


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _client


async def compress_history(history: list[dict], keep_recent: int = 4) -> list[dict]:
    """Compress old conversation turns into a summary.

    Args:
        history: Full chat history [{role, content}, ...]
        keep_recent: Number of recent messages to keep in full (default 4 = 2 turns)

    Returns:
        Compressed history: [summary_message, ...recent_messages]
    """
    if len(history) <= keep_recent:
        return history

    old_messages = history[:-keep_recent]
    recent_messages = history[-keep_recent:]

    client = get_client()

    old_text = "\n".join(
        f"{'用户' if m['role'] == 'user' else '助手'}: {m['content'][:300]}"
        for m in old_messages
    )

    try:
        response = await client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": COMPRESS_PROMPT},
                {"role": "user", "content": f"请压缩以下对话历史：\n\n{old_text}"},
            ],
            temperature=0.1,
            max_tokens=300,
            stream=False,
        )
        summary = response.choices[0].message.content.strip()
    except Exception:
        # Fallback: just truncate
        summary = f"（之前的对话包含 {len(old_messages)} 条消息，已省略）"

    compressed = [{"role": "system", "content": f"对话历史摘要：{summary}"}]
    compressed.extend(recent_messages)
    return compressed
