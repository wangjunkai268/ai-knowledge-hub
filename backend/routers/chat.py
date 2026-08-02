"""聊天 API — SSE 流式对话"""
import json
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .deps import get_agent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    temperature: float = 0.7
    max_tokens: int = 2048
    kb_id: Optional[str] = None   # None = 全局检索


@router.post("/api/chat")
async def chat(req: ChatRequest):
    """SSE 流式返回 AI 回答"""
    def generate():
        # get_agent() 首次会加载 embedding 模型，放这里由 StreamingResponse 线程池执行
        agent = get_agent()
        try:
            for chunk in agent.query_stream(
                question=req.message,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                kb_id=req.kb_id,
            ):
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
