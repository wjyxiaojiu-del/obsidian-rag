from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # LLM (Anthropic-compatible)
    llm_api_key: str = ""
    llm_base_url: str = "https://token-plan-sgp.xiaomimimo.com/anthropic"
    llm_model: str = "mimo-v2.5-pro"

    # Embedding
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_device: str = "cuda"

    # Vector Store
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection_name: str = "obsidian_rag"

    # Obsidian
    obsidian_vault_path: str = r"F:\小九\小九的obisidian"
    obsidian_sync_interval: int = 300  # seconds

    # RAG
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5
    rerank_top_k: int = 3

    # WeFlow
    weflow_url: str = "http://127.0.0.1:5031"
    weflow_token: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
