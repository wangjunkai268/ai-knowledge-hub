"""
FastAPI 后端入口 — 提供 REST API 给 Vue 3 前端
"""
import os
import json
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import RAGAgent
from knowledge_loader import (
    KNOWLEDGE_DIR, CHROMA_DIR, UPLOADS_DIR,
    process_single_file, build_knowledge_base, delete_document,
    get_knowledge_stats, get_document_list
)

app = FastAPI(title="AI Knowledge Hub API")

# CORS 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局 agent 实例
_agent: Optional[RAGAgent] = None


def get_agent() -> RAGAgent:
    global _agent
    if _agent is None:
        _agent = RAGAgent()
    return _agent


# ─── Chat ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    temperature: float = 0.7
    max_tokens: int = 2048


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """SSE 流式返回 AI 回答"""
    agent = get_agent()

    def generate():
        try:
            for chunk in agent.query_stream(
                question=req.message,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
            ):
                # SSE 格式: data: {...}\n\n
                data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {data}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Documents ──────────────────────────────────────────

@app.get("/api/documents")
async def list_documents():
    """获取文档列表"""
    return {"documents": get_document_list()}


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文档并自动索引"""
    # 验证文件类型
    ext = Path(file.filename).suffix.lower()
    if ext not in (".txt", ".md", ".pdf"):
        raise HTTPException(400, f"不支持的文件格式: {ext}，仅支持 txt/md/pdf")

    # 确保文件名唯一
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = UPLOADS_DIR / safe_name

    content = await file.read()
    file_path.write_bytes(content)

    try:
        # 处理上传的文件：复制到 knowledge + 索引
        target = KNOWLEDGE_DIR / safe_name
        shutil.copy2(file_path, target)
        process_single_file(target)

        # 刷新 agent
        global _agent
        if _agent:
            _agent.reload()
        else:
            _agent = RAGAgent()

        return {
            "success": True,
            "id": safe_name,
            "name": file.filename,
            "size": len(content),
            "uploaded_at": datetime.now().isoformat(),
            **get_knowledge_stats(),
        }
    except Exception as e:
        raise HTTPException(500, f"处理文件失败: {e}")


@app.delete("/api/documents/{doc_id}")
async def remove_document(doc_id: str):
    """删除文档并重建知识库"""
    if not delete_document(doc_id):
        raise HTTPException(404, "文档不存在")

    # 用 ChromaDB API 清空旧数据 + 重建（不依赖文件系统操作）
    build_knowledge_base(force_rebuild=True)

    # 刷新 agent 连接
    global _agent
    if _agent:
        _agent.reload()

    return {"success": True, "id": doc_id, **get_knowledge_stats()}


# ─── Knowledge Base ─────────────────────────────────────

@app.get("/api/knowledge/stats")
async def knowledge_stats():
    """知识库统计"""
    return get_knowledge_stats()


@app.post("/api/knowledge/reload")
async def reload_knowledge():
    """重建知识库"""
    build_knowledge_base(force_rebuild=True)
    global _agent
    if _agent:
        _agent.reload()

    return {"success": True, **get_knowledge_stats()}


# ─── Health ─────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "agent_ready": get_agent().is_ready()}


# ─── Entry ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
