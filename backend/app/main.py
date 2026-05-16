from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, knowledge, sync, wechat

app = FastAPI(
    title="Obsidian RAG",
    description="Personal knowledge base Q&A system with Obsidian integration",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(sync.router)
app.include_router(wechat.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.on_event("startup")
async def startup():
    # Lazy init: embedding model and chromadb will be initialized on first request
    print(f"Obsidian RAG starting...")
    print(f"  Vault: {settings.obsidian_vault_path}")
    print(f"  ChromaDB: {settings.chroma_persist_dir}")
    print(f"  Embedding: {settings.embedding_model}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
