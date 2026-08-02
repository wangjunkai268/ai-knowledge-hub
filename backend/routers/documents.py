"""文档管理 API — 上传 / 列表 / 删除"""
import shutil
import uuid
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Query

from knowledge_loader import (
    KNOWLEDGE_DIR, UPLOADS_DIR, DEFAULT_KB_ID,
    process_single_file, build_knowledge_base, delete_document,
    get_document_list, get_knowledge_stats,
)
from .deps import refresh_agent

router = APIRouter()


@router.get("/api/documents")
async def list_documents(kb_id: str = Query(DEFAULT_KB_ID)):
    """获取指定知识库的文档列表"""
    return {"documents": get_document_list(kb_id)}


@router.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    kb_id: str = Query(DEFAULT_KB_ID),
):
    """上传文档并自动索引到指定知识库"""
    ext = Path(file.filename).suffix.lower()
    if ext not in (".txt", ".md", ".pdf"):
        raise HTTPException(400, f"不支持的文件格式: {ext}，仅支持 txt/md/pdf")

    # 确保目标知识库存在
    kb_dir = KNOWLEDGE_DIR / kb_id
    kb_dir.mkdir(parents=True, exist_ok=True)

    # 确保文件名唯一
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = UPLOADS_DIR / safe_name

    content = await file.read()
    file_path.write_bytes(content)

    try:
        # 处理上传的文件：复制到 knowledge + 索引
        target = kb_dir / safe_name
        shutil.copy2(file_path, target)
        process_single_file(target, kb_id)

        # 刷新 agent
        refresh_agent()

        return {
            "success": True,
            "id": safe_name,
            "name": file.filename,
            "size": len(content),
            "uploaded_at": datetime.now().isoformat(),
            **get_knowledge_stats(kb_id),
        }
    except Exception as e:
        raise HTTPException(500, f"处理文件失败: {e}")


@router.delete("/api/documents/{doc_id}")
async def remove_document(doc_id: str, kb_id: str = Query(DEFAULT_KB_ID)):
    """删除文档并重建知识库"""
    if not delete_document(doc_id, kb_id):
        raise HTTPException(404, "文档不存在")

    build_knowledge_base(force_rebuild=True)
    refresh_agent()

    return {"success": True, "id": doc_id, **get_knowledge_stats(kb_id)}
