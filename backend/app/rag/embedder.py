from fastembed import TextEmbedding
from app.config import settings

_model: TextEmbedding | None = None


def get_embedder() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=settings.embedding_model)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    embeddings = list(model.embed(texts, normalize=True))
    return [e.tolist() for e in embeddings]


def embed_query(query: str) -> list[float]:
    model = get_embedder()
    embedding = list(model.embed([query], normalize=True))
    return embedding[0].tolist()
