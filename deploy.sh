#!/bin/bash
set -e

echo "=== Obsidian RAG Deployment ==="

# Clone or pull
if [ -d /root/obsidian-rag ]; then
    cd /root/obsidian-rag
    git pull
else
    git clone https://github.com/wjyxiaojiu-del/obsidian-rag.git /root/obsidian-rag
    cd /root/obsidian-rag
fi

# Create data dir
mkdir -p data/chroma_db

# Create .env if not exists
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo ">>> Please edit backend/.env and set DEEPSEEK_API_KEY"
    exit 1
fi

# Login to GHCR (needs token)
echo ">>> Pulling pre-built images from ghcr.io..."
docker compose -f docker-compose.server.yml pull

# Start services
docker compose -f docker-compose.server.yml up -d

echo "=== Deployment complete ==="
echo "Frontend: http://$(hostname -I | awk '{print $1}'):3001"
echo "Backend:  http://$(hostname -I | awk '{print $1}'):8000"
