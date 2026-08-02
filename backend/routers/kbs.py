"""知识库管理 API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from knowledge_loader import (
    DEFAULT_KB_ID, get_kb_list, create_kb, delete_kb, get_knowledge_stats,
)
from .deps import refresh_agent

router = APIRouter()


class CreateKbRequest(BaseModel):
    name: str


@router.get("/api/kbs")
async def list_kbs():
    """获取所有知识库"""
    return {"kbs": get_kb_list()}


@router.post("/api/kbs")
async def create_kb_endpoint(req: CreateKbRequest):
    """创建知识库"""
    if not req.name or not req.name.strip():
        raise HTTPException(400, "知识库名称不能为空")
    return create_kb(req.name.strip())


@router.delete("/api/kbs/{kb_id}")
async def remove_kb(kb_id: str):
    """删除知识库"""
    if kb_id == DEFAULT_KB_ID:
        raise HTTPException(400, "默认知识库不可删除")
    if not delete_kb(kb_id):
        raise HTTPException(404, "知识库不存在")
    refresh_agent()
    return {"success": True, "id": kb_id, **get_knowledge_stats()}
