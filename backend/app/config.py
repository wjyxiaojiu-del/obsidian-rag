from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # LLM
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

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

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
