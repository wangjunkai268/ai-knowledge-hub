"""
知识库加载模块 — 文档加载、切片、向量化、管理
"""
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

# 确保目录存在
KNOWLEDGE_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

EMBEDDING_MODEL = "shibing624/text2vec-base-chinese"


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


def process_single_file(filepath: Path):
    """处理单个文件并添加到现有向量库"""
    if not filepath.exists():
        return

    # 加载文档
    loader = None
    if filepath.suffix in (".txt", ".md"):
        loader = TextLoader(str(filepath), encoding="utf-8")
    elif filepath.suffix == ".pdf":
        loader = PyPDFLoader(str(filepath))

    if loader is None:
        return

    docs = loader.load()
    chunks = _get_splitter().split_documents(docs)

    if not chunks:
        return

    # 追加到现有向量库
    embeddings = _get_embeddings()
    vectorstore = Chroma(
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )
    vectorstore.add_documents(chunks)
    return len(chunks)


def build_knowledge_base(force_rebuild=False):
    """构建/重建整个知识库"""
    # 检查是否已有
    existing = list(CHROMA_DIR.glob("*.parquet")) + list(CHROMA_DIR.glob("*sqlite*"))
    if existing and not force_rebuild:
        return True

    # 加载所有文档
    docs = []
    for filepath in KNOWLEDGE_DIR.iterdir():
        if not filepath.is_file():
            continue
        try:
            loader = None
            if filepath.suffix in (".txt", ".md"):
                loader = TextLoader(str(filepath), encoding="utf-8")
            elif filepath.suffix == ".pdf":
                loader = PyPDFLoader(str(filepath))
            if loader:
                docs.extend(loader.load())
        except Exception:
            continue

    if not docs:
        _reset_chroma_db()        # ← 用 API 清数据，不删文件
        return True

    chunks = _get_splitter().split_documents(docs)
    embeddings = _get_embeddings()

    _reset_chroma_db()            # ← 先清空旧数据
    CHROMA_DIR.mkdir(exist_ok=True)
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
    )
    return True


def _reset_chroma_db():
    """彻底清空 ChromaDB —— API 删集合 + 删数据文件，双保险"""
    import chromadb
    import shutil

    # 方法1: 用 ChromaDB API 删除所有集合
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        for col in client.list_collections():
            client.delete_collection(col.name)
    except Exception:
        pass


def delete_document(doc_id: str):
    """删除文档（只删文件，不重建——由 server.py 负责重建）"""
    deleted = False
    for f in list(KNOWLEDGE_DIR.iterdir()):
        if f.name == doc_id or f.name.endswith(f"_{doc_id}"):
            f.unlink()
            deleted = True
    for f in list(UPLOADS_DIR.iterdir()):
        if f.name == doc_id or f.name.endswith(f"_{doc_id}"):
            f.unlink()
    return deleted


def get_document_list() -> list:
    """获取文档列表"""
    files = []
    for filepath in sorted(KNOWLEDGE_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if filepath.is_file():
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


def get_knowledge_stats() -> dict:
    """获取知识库统计信息"""
    docs = get_document_list()
    # 从 ChromaDB 获取片段数
    chunk_count = 0
    try:
        vectorstore = Chroma(
            embedding_function=_get_embeddings(),
            persist_directory=str(CHROMA_DIR),
        )
        chunk_count = vectorstore._collection.count()
    except Exception:
        pass

    return {
        "document_count": len(docs),
        "chunk_count": chunk_count,
        "documents": docs,
    }


def _format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
