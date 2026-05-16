from openai import AsyncOpenAI
from app.config import settings
from app.models import SourceRef

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _client


SYSTEM_PROMPT = """你是一个知识库问答助手。根据用户的问题和检索到的参考资料生成回答。

规则：
1. 只基于提供的参考资料回答，不要编造信息
2. 如果参考资料不足以回答，明确说明"根据现有知识库，暂未找到相关信息"
3. 在回答中引用来源，格式：[来源: 文件名]
4. 回答要结构化、清晰，使用中文
5. 如果涉及专业术语，适当解释"""


def build_context(sources: list[SourceRef]) -> str:
    """Build context string from retrieved sources."""
    parts = []
    for i, src in enumerate(sources, 1):
        source_label = src.file_name
        if src.heading_path:
            source_label += f" > {src.heading_path}"
        parts.append(f"[{i}] 来源: {source_label}\n{src.chunk_text}")
    return "\n\n---\n\n".join(parts)


async def generate_answer(question: str, sources: list[SourceRef]) -> str:
    """Generate answer using DeepSeek API with retrieved context."""
    client = get_client()

    context = build_context(sources)
    user_message = f"""参考资料：
{context}

用户问题：{question}"""

    response = await client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=2000,
        stream=True,
    )

    answer = ""
    async for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            answer += delta

    return answer


async def generate_answer_stream(question: str, sources: list[SourceRef]):
    """Stream answer tokens."""
    client = get_client()

    context = build_context(sources)
    user_message = f"""参考资料：
{context}

用户问题：{question}"""

    response = await client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=2000,
        stream=True,
    )

    async for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
