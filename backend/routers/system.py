"""系统 API — 统计 / 重建 / 健康检查"""
from typing import Optional

from fastapi import APIRouter, Query

from knowledge_loader import get_knowledge_stats, build_knowledge_base
from .deps import get_agent, refresh_agent

router = APIRouter()


@router.get("/api/knowledge/stats")
def knowledge_stats(kb_id: Optional[str] = Query(None)):
    """知识库统计（None = 全局）"""
    return get_knowledge_stats(kb_id)


@router.post("/api/knowledge/reload")
def reload_knowledge():
    """重建整个知识库"""
    build_knowledge_base(force_rebuild=True)
    refresh_agent()
    return {"success": True, **get_knowledge_stats()}


@router.get("/api/health")
def health():
    return {"status": "ok", "agent_ready": get_agent().is_ready()}
