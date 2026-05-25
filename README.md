> **中文** | [English](README_en.md)

# Obsidian RAG - 个人知识库问答系统

基于 RAG (Retrieval-Augmented Generation) 的多源知识库问答系统，支持 Obsidian 笔记、PDF 文献和网页内容。

## 功能特性

- **多源文档接入** — Obsidian Vault 自动同步、PDF 文献上传、网页 URL 抓取
- **混合检索** — 向量语义检索 + BM25 关键词检索，RRF 融合排序
- **引用溯源** — 回答附带源文档引用，点击可查看原文
- **增量同步** — Obsidian 笔记修改后自动检测变更，增量更新索引
- **流式输出** — SSE 实时流式返回回答
- **本地 Embedding** — 使用 BGE-small-zh 模型本地推理，无需外部 Embedding API

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + Python 3.12 |
| RAG Pipeline | ChromaDB + BM25 + RRF |
| Embedding | BAAI/bge-small-zh-v1.5 (sentence-transformers) |
| LLM | DeepSeek API |
| 前端 | Next.js 15 + Tailwind CSS 4 |
| 部署 | Docker Compose |

## 快速开始

### 1. 配置环境变量

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

### 2. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 启动后端

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### 4. 安装前端依赖并启动

```bash
cd frontend
npm install
npm run dev
```

### 5. 同步 Obsidian 知识库

```bash
curl -X POST http://localhost:8000/api/sync/full
```

访问 http://localhost:3001 开始使用。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 对话问答（非流式） |
| POST | `/api/chat/stream` | 对话问答（SSE 流式） |
| GET | `/api/knowledge/stats` | 索引统计 |
| POST | `/api/knowledge/pdf` | 上传 PDF 文献 |
| POST | `/api/knowledge/web` | 导入网页内容 |
| POST | `/api/sync` | 触发 Obsidian 同步（后台） |
| POST | `/api/sync/full` | 全量同步（阻塞） |
| GET | `/api/sync/status` | 同步状态 |

## 项目结构

```
obsidian-rag/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置管理
│   │   ├── models.py            # Pydantic 数据模型
│   │   ├── rag/
│   │   │   ├── pipeline.py      # RAG 核心流水线
│   │   │   ├── embedder.py      # Embedding 服务
│   │   │   ├── retriever.py     # 混合检索器
│   │   │   └── generator.py     # LLM 生成
│   │   ├── loaders/
│   │   │   ├── obsidian.py      # Obsidian 文档加载器
│   │   │   ├── pdf.py           # PDF 加载器
│   │   │   └── web.py           # 网页加载器
│   │   ├── routers/
│   │   │   ├── chat.py          # 对话 API
│   │   │   ├── knowledge.py     # 知识库管理 API
│   │   │   └── sync.py          # 同步 API
│   │   └── services/
│   │       └── sync_service.py  # 同步服务
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # 主页面
│   │   │   ├── layout.tsx       # 布局
│   │   │   └── globals.css      # 全局样式
│   │   ├── components/
│   │   │   ├── ChatBox.tsx      # 对话组件
│   │   │   ├── MessageBubble.tsx # 消息气泡
│   │   │   ├── SourcePanel.tsx  # 引用溯源面板
│   │   │   ├── Sidebar.tsx      # 侧边栏
│   │   │   └── KnowledgePanel.tsx # 知识库管理
│   │   └── lib/
│   │       └── api.ts           # API 客户端
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 架构设计

```
用户问题 → 混合检索 (向量 + BM25) → RRF 融合 → Top-K 上下文 → LLM 生成回答 + 引用
```

- **向量检索**: BGE-small-zh Embedding → ChromaDB cosine similarity
- **关键词检索**: jieba 分词 → BM25Okapi
- **融合策略**: Reciprocal Rank Fusion (RRF, k=60)
- **生成模型**: DeepSeek Chat, temperature=0.3
