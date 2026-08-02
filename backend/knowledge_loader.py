"""
知识库加载模块 — 多知识库文档加载、切片、向量化、管理
所有知识库共享一个 ChromaDB 集合，用 metadata.kb_id 隔离
"""
import uuid
import shutil
from pathlib import Path
from datetime import datetime

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# 目录路径
ROOT = Path(__file__).parent
KNOWLEDGE_DIR = ROOT / "knowledge"
CHROMA_DIR = ROOT / "chroma_db"
UPLOADS_DIR = ROOT / "uploads"

# 默认知识库
DEFAULT_KB_ID = "kb_default"
DEFAULT_KB_NAME = "默认知识库"

# 确保目录存在
KNOWLEDGE_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

EMBEDDING_MODEL = "shibing624/text2vec-base-chinese"

# 上传中文件的临时后缀（向量化完成前不可见）
UPLOADING_SUFFIX = ".uploading"


def _is_visible_file(filename: str) -> bool:
    """是否为可见文档（排除 kb.json 和上传中的临时文件）"""
    return filename != "kb.json" and not filename.endswith(UPLOADING_SUFFIX)


def _get_embeddings():
    """懒加载 embedding 模型"""
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _get_splitter():
    """文档切片器"""
    return RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
    )


def _load_file(filepath: Path):
    """加载单个文件为文档（支持 .uploading 临时文件，用真实扩展名判断类型）"""
    # .uploading 后缀会覆盖真实扩展名（如 xxx.md.uploading），用 stem 还原
    real_name = filepath.name
    if real_name.endswith(UPLOADING_SUFFIX):
        real_name = real_name[: -len(UPLOADING_SUFFIX)]
    suffix = Path(real_name).suffix.lower()

    loader = None
    if suffix in (".txt", ".md"):
        loader = TextLoader(str(filepath), encoding="utf-8")
    elif suffix == ".pdf":
        loader = PyPDFLoader(str(filepath))
    if loader:
        return loader.load()
    return []


# ─── 知识库管理 ───────────────────────────────────────

def get_kb_dir(kb_id: str) -> Path:
    """获取知识库目录"""
    return KNOWLEDGE_DIR / kb_id


def _kb_meta_path(kb_id: str) -> Path:
    """知识库元数据文件路径"""
    return get_kb_dir(kb_id) / "kb.json"


def _read_kb_meta(kb_id: str) -> dict:
    """读取知识库元数据"""
    import json
    meta_path = _kb_meta_path(kb_id)
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"name": kb_id}


def _write_kb_meta(kb_id: str, meta: dict):
    """写入知识库元数据"""
    import json
    _kb_meta_path(kb_id).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_default_kb():
    """确保默认知识库存在（含元数据）"""
    kb_dir = get_kb_dir(DEFAULT_KB_ID)
    if not kb_dir.exists():
        kb_dir.mkdir(parents=True, exist_ok=True)
    if not _kb_meta_path(DEFAULT_KB_ID).exists():
        _write_kb_meta(DEFAULT_KB_ID, {"name": DEFAULT_KB_NAME, "created_at": datetime.now().isoformat()})


def get_kb_list() -> list:
    """获取所有知识库列表"""
    ensure_default_kb()
    kbs = []
    for kb_dir in sorted(KNOWLEDGE_DIR.iterdir()):
        if not kb_dir.is_dir():
            continue
        meta = _read_kb_meta(kb_dir.name)
        docs = get_document_list(kb_dir.name)
        kbs.append({
            "id": kb_dir.name,
            "name": meta.get("name", kb_dir.name),
            "document_count": len(docs),
            "documents": docs,
        })
    return kbs


def create_kb(name: str) -> dict:
    """创建知识库"""
    kb_id = "kb_" + uuid.uuid4().hex[:8]
    kb_dir = get_kb_dir(kb_id)
    kb_dir.mkdir(parents=True, exist_ok=True)
    _write_kb_meta(kb_id, {"name": name, "created_at": datetime.now().isoformat()})
    return {"id": kb_id, "name": name, "document_count": 0, "documents": []}


def delete_kb(kb_id: str) -> bool:
    """删除知识库（目录 + 向量片段）"""
    if kb_id == DEFAULT_KB_ID:
        return False  # 默认库不可删

    kb_dir = get_kb_dir(kb_id)
    if not kb_dir.exists():
        return False
    shutil.rmtree(str(kb_dir), ignore_errors=True)

    # 删除该库在向量库中的片段
    try:
        vectorstore = Chroma(
            embedding_function=_get_embeddings(),
            persist_directory=str(CHROMA_DIR),
        )
        vectorstore.delete(where={"kb_id": kb_id})
    except Exception:
        pass
    return True


def get_kb_name(kb_id: str) -> str:
    """获取知识库名称"""
    return _read_kb_meta(kb_id).get("name", kb_id)


# ─── 文档处理 ─────────────────────────────────────────

def process_single_file(filepath: Path, kb_id: str):
    """处理单个文件并添加到向量库"""
    if not filepath.exists():
        return

    chunks = _load_file(filepath)
    if not chunks:
        return

    splitter = _get_splitter()
    split_chunks = splitter.split_documents(chunks)
    for c in split_chunks:
        c.metadata["kb_id"] = kb_id

    if not split_chunks:
        return

    embeddings = _get_embeddings()
    vectorstore = Chroma(
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )
    vectorstore.add_documents(split_chunks)
    return len(split_chunks)


def build_knowledge_base(force_rebuild=False):
    """构建/重建整个知识库（遍历所有知识库目录）"""
    existing = list(CHROMA_DIR.glob("*.parquet")) + list(CHROMA_DIR.glob("*sqlite*"))
    if existing and not force_rebuild:
        return True

    ensure_default_kb()

    # 遍历所有知识库目录
    all_chunks = []
    for kb_dir in sorted(KNOWLEDGE_DIR.iterdir()):
        if not kb_dir.is_dir():
            continue
        kb_id = kb_dir.name
        for filepath in kb_dir.iterdir():
            if not filepath.is_file() or not _is_visible_file(filepath.name):
                continue
            try:
                docs = _load_file(filepath)
                splitter = _get_splitter()
                chunks = splitter.split_documents(docs)
                for c in chunks:
                    c.metadata["kb_id"] = kb_id
                all_chunks.extend(chunks)
            except Exception:
                continue

    if not all_chunks:
        _reset_chroma_db()
        return True

    embeddings = _get_embeddings()
    _reset_chroma_db()
    CHROMA_DIR.mkdir(exist_ok=True)
    Chroma.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
    )
    return True


def _reset_chroma_db():
    """彻底清空 ChromaDB"""
    import chromadb
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        for col in client.list_collections():
            client.delete_collection(col.name)
    except Exception:
        pass


def delete_document(doc_id: str, kb_id: str = DEFAULT_KB_ID):
    """删除文档（只删文件，由 server.py 负责重建）"""
    deleted = False
    kb_dir = get_kb_dir(kb_id)
    for f in list(kb_dir.iterdir()):
        if f.name == doc_id or f.name.endswith(f"_{doc_id}"):
            f.unlink()
            deleted = True
    for f in list(UPLOADS_DIR.iterdir()):
        if f.name == doc_id or f.name.endswith(f"_{doc_id}"):
            f.unlink()
    return deleted


def get_document_list(kb_id: str = DEFAULT_KB_ID) -> list:
    """获取指定知识库的文档列表"""
    kb_dir = get_kb_dir(kb_id)
    if not kb_dir.exists():
        return []
    files = []
    for filepath in sorted(kb_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if filepath.is_file() and _is_visible_file(filepath.name):
            stat = filepath.stat()
            files.append({
                "id": filepath.name,
                "name": filepath.name.split("_", 1)[-1] if "_" in filepath.name else filepath.name,
                "size": stat.st_size,
                "format_size": _format_size(stat.st_size),
                "type": filepath.suffix,
                "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    return files


def get_knowledge_stats(kb_id: str | None = None) -> dict:
    """
    获取知识库统计信息
    kb_id=None → 全局统计；指定 → 该库统计
    """
    if kb_id:
        docs = get_document_list(kb_id)
        chunk_count = _count_chunks(kb_id)
        return {
            "document_count": len(docs),
            "chunk_count": chunk_count,
            "documents": docs,
        }

    # 全局
    total_docs = []
    total_chunks = 0
    for kb_dir in KNOWLEDGE_DIR.iterdir():
        if not kb_dir.is_dir():
            continue
        total_docs.extend(get_document_list(kb_dir.name))
        total_chunks += _count_chunks(kb_dir.name)
    return {
        "document_count": len(total_docs),
        "chunk_count": total_chunks,
        "documents": total_docs,
    }


def _count_chunks(kb_id: str) -> int:
    """统计指定知识库的向量片段数"""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        col = client.get_or_create_collection("langchain")
        result = col.get(where={"kb_id": kb_id})
        return len(result["ids"]) if result else 0
    except Exception:
        return 0


def _format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
