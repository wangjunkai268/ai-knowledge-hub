# AI Knowledge Hub

基于 RAG（检索增强生成）的智能知识库管理平台。上传文档构建私有知识库，通过自然语言对话检索答案。

**技术栈**：Vue 3 + TypeScript + TailwindCSS v4 / FastAPI + LangChain + ChromaDB / DeepSeek API

[![GitHub stars](https://img.shields.io/github/stars/wangjunkai268/ai-knowledge-hub?style=flat)](https://github.com/wangjunkai268/ai-knowledge-hub)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## ✨ 功能

- **流式对话** — SSE 实时逐字输出，打字机动画效果
- **知识库管理** — 拖拽上传 TXT / Markdown / PDF，自动切片向量化
- **文档溯源** — AI 回答附带引用来源，可展开查看
- **多轮对话** — 会话历史持久化存储，支持新建/切换/删除
- **暗色模式** — 一键切换，全局适配
- **多文件上传** — 独立进度条，并行上传互不干扰

## 🏗️ 架构

```
┌─────────────────────┐     ┌──────────────────────────────────┐
│   Vue 3 前端         │────▶│   FastAPI 后端 (SSE 流式)         │
│   Vite + Tailwind   │◀────│   LangChain + ChromaDB            │
│   Pinia 状态管理      │     │   DeepSeek API                    │
└─────────────────────┘     └──────────────────────────────────┘
```

| 层 | 技术 | 说明 |
|---|------|------|
| 前端框架 | Vue 3 + Composition API + TypeScript | 响应式 UI |
| 样式 | TailwindCSS v4 | 暗色模式内置 |
| 状态管理 | Pinia + persistedstate | 对话 & 主题持久化 |
| 构建 | Vite | 开发秒启 |
| 后端 | FastAPI | 异步 SSE 流式 |
| AI | LangChain + DeepSeek | RAG 检索增强生成 |
| 向量库 | ChromaDB | 本地持久化 |
| 嵌入模型 | text2vec-base-chinese | 中文语义向量 |

## 📁 项目结构

```
ai-knowledge-hub/
├── backend/
│   ├── server.py             # FastAPI 入口 + REST + SSE
│   ├── agent.py              # RAG Agent：检索 + 流式生成
│   └── knowledge_loader.py   # 文档加载、切片、向量化
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── ChatPage.vue       # 流式对话
│       │   ├── KnowledgePage.vue  # 知识库管理
│       │   └── SettingsPage.vue   # 系统设置
│       ├── components/
│       │   ├── Sidebar.vue        # 侧边栏（对话列表+暗色切换）
│       │   ├── ChatMessage.vue    # 消息气泡（Markdown 渲染）
│       │   ├── FileUpload.vue     # 拖拽上传
│       │   └── SourceCard.vue     # 引用来源卡片
│       ├── stores/
│       │   ├── chat.ts            # 对话 Pinia Store
│       │   └── theme.ts           # 主题 Pinia Store
│       ├── types/chat.ts          # 类型定义
│       └── api/index.ts           # API 封装 (axios + SSE)
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- DeepSeek API Key → [申请地址](https://platform.deepseek.com)

### 1. 克隆项目

```bash
git clone https://github.com/wangjunkai268/ai-knowledge-hub.git
cd ai-knowledge-hub
```

### 2. 配置 API Key

编辑根目录 `.env` 文件：

```env
DEEPSEEK_API_KEY=sk-xxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 3. 启动后端

```bash
cd backend
pip install fastapi uvicorn python-multipart langchain langchain-openai langchain-chroma langchain-huggingface langchain-community chromadb sentence-transformers pypdf python-dotenv
python server.py
```

后端运行在 http://localhost:8000

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端运行在 http://localhost:5173

### 5. 使用

1. 打开浏览器访问 http://localhost:5173
2. 进入「知识库」页面上传文档（支持 TXT / Markdown / PDF）
3. 回到「对话」页面提问

## 📡 API

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/api/chat` | 发送消息，SSE 流式返回 |
| `POST` | `/api/documents/upload` | 上传文档 |
| `GET` | `/api/documents` | 文档列表 |
| `DELETE` | `/api/documents/{id}` | 删除文档 |
| `GET` | `/api/knowledge/stats` | 知识库统计 |
| `POST` | `/api/knowledge/reload` | 重建知识库 |
| `GET` | `/api/health` | 健康检查 |

## 📝 License

MIT
