from anthropic import AsyncAnthropic
from app.config import settings

_client: AsyncAnthropic | None = None

REWRITE_PROMPT = """你是一个查询改写助手。根据用户的问题和对话历史，将问题改写为更适合知识库检索的形式。

规则：
1. 补充代词指代（"这个"→具体名词，"它"→具体对象）
2. 补充上下文中的关键信息
3. 保持原意，不要过度扩展
4. 只输出改写后的查询，不要解释
5. 如果问题已经很明确，直接返回原文

示例：
用户: obsidian怎么用？
改写: obsidian笔记软件的使用方法

用户: 那它的插件呢？(历史: 讨论了obsidian)
改写: obsidian插件的安装和使用方法

用户: 今天天气怎么样？
改写: 今天天气怎么样
"""


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
    return _client


async def rewrite_query(
    question: str,
    history: list[dict] | None = None,
) -> str:
    """Rewrite user query for better retrieval, using chat history for context."""
    if not history:
        return question

    client = get_client()

    recent = history[-6:] if len(history) > 6 else history
    history_text = "\n".join(
        f"{'用户' if m['role'] == 'user' else '助手'}: {m['content'][:200]}"
        for m in recent
    )

    user_msg = f"""对话历史：
{history_text}

当前问题：{question}

请改写为更适合知识库检索的查询："""

    try:
        response = await client.messages.create(
            model=settings.llm_model,
            system=REWRITE_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
            temperature=0.1,
            max_tokens=200,
        )
        rewritten = ""
        for block in response.content:
            if block.type == "text":
                rewritten += block.text
        return rewritten.strip() if rewritten.strip() else question
    except Exception:
        return question
