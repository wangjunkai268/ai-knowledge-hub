"""文档管理 API — 上传 / 列表 / 删除"""
import shutil
import uuid
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel

from knowledge_loader import (
    KNOWLEDGE_DIR, UPLOADS_DIR, DEFAULT_KB_ID, UPLOADING_SUFFIX,
    process_single_file, build_knowledge_base, delete_document,
    get_document_list, get_knowledge_stats,
)
from .deps import refresh_agent

router = APIRouter()


class BatchDeleteRequest(BaseModel):
    kb_id: str = DEFAULT_KB_ID
    doc_ids: list[str]

router = APIRouter()


@router.get("/api/documents")
def list_documents(kb_id: str = Query(DEFAULT_KB_ID)):
    """获取指定知识库的文档列表"""
    return {"documents": get_document_list(kb_id)}


@router.post("/api/documents/upload")
def upload_document(
    file: UploadFile = File(...),
    kb_id: str = Query(DEFAULT_KB_ID),
):
    """上传文档并自动索引到指定知识库（同步 def，FastAPI 放入线程池，避免阻塞 event loop）"""
    ext = Path(file.filename).suffix.lower()
    if ext not in (".txt", ".md", ".pdf"):
        raise HTTPException(400, f"不支持的文件格式: {ext}，仅支持 txt/md/pdf")

    # 确保目标知识库存在
    kb_dir = KNOWLEDGE_DIR / kb_id
    kb_dir.mkdir(parents=True, exist_ok=True)

    # 确保文件名唯一
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = UPLOADS_DIR / safe_name

    content = file.file.read()   # 同步读取（def 端点中 UploadFile 用 .file）
    file_path.write_bytes(content)

    # 先复制为 .uploading 临时文件（向量化前不出现在文档列表）
    temp_target = kb_dir / (safe_name + UPLOADING_SUFFIX)
    shutil.copy2(file_path, temp_target)

    try:
        # 向量化成功后才重命名为正式文件名
        chunk_count = process_single_file(temp_target, kb_id)
        if not chunk_count:
            # 没有产生任何向量片段 → 视为失败，不保留文件
            raise ValueError("文档未能被解析或向量化")

        temp_target.rename(kb_dir / safe_name)

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
        # 失败清理临时文件，不留下未完成的文档
        temp_target.unlink(missing_ok=True)
        raise HTTPException(500, f"处理文件失败: {e}")


@router.delete("/api/documents/{doc_id}")
def remove_document(doc_id: str, kb_id: str = Query(DEFAULT_KB_ID)):
    """删除文档并重建知识库"""
    if not delete_document(doc_id, kb_id):
        raise HTTPException(404, "文档不存在")

    build_knowledge_base(force_rebuild=True)
    refresh_agent()

    return {"success": True, "id": doc_id, **get_knowledge_stats(kb_id)}


@router.post("/api/documents/batch-delete")
def batch_delete_documents(req: BatchDeleteRequest):
    """批量删除文档（一次删多个，只重建一次）"""
    if not req.doc_ids:
        raise HTTPException(400, "没有选择要删除的文档")

    deleted = 0
    for doc_id in req.doc_ids:
        if delete_document(doc_id, req.kb_id):
            deleted += 1

    if deleted == 0:
        raise HTTPException(404, "没有文档被删除")

    build_knowledge_base(force_rebuild=True)
    refresh_agent()

    return {"success": True, "deleted": deleted, **get_knowledge_stats(req.kb_id)}
