from sentence_transformers import SentenceTransformer
from app.config import settings

_model: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(
            settings.embedding_model,
            device=settings.embedding_device,
        )
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    model = get_embedder()
    embedding = model.encode([query], normalize_embeddings=True)
    return embedding[0].tolist()
