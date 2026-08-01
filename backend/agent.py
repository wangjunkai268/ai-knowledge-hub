"""
Agent 核心 — 检索知识库 + 调用 DeepSeek 生成回答（支持流式输出）
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv()

ROOT = Path(__file__).parent
CHROMA_DIR = ROOT / "chroma_db"
EMBEDDING_MODEL = "shibing624/text2vec-base-chinese"


class RAGAgent:
    def __init__(self):
        # 懒加载 embedding（首次使用才初始化，节省启动时间）
        self._embeddings = None
        self._llm = None
        self._vectorstore = None
        self._init_vectorstore()

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        return self._embeddings

    def _init_vectorstore(self):
        """连接 ChromaDB"""
        if CHROMA_DIR.exists() and any(CHROMA_DIR.iterdir()):
            self._vectorstore = Chroma(
                embedding_function=self.embeddings,
                persist_directory=str(CHROMA_DIR),
            )
        else:
            self._vectorstore = None

    def is_ready(self) -> bool:
        return self._vectorstore is not None

    def close(self):
        """释放 ChromaDB 连接（删库/重建前必须调用，否则 Windows 锁文件）"""
        self._vectorstore = None

    def reload(self):
        """重新加载向量库（知识库更新后调用）"""
        self.close()
        self._init_vectorstore()

    def query_stream(self, question: str, top_k: int = 5, temperature: float = 0.7, max_tokens: int = 2048):
        """
        流式查询，逐 chunk yield
        每个 chunk 格式: {"type": "text"|"sources"|"done"|"error", "content": str}
        """
        if not self._vectorstore:
            yield {"type": "error", "content": "知识库为空，请先上传文档。"}
            return

        # 1. 检索相关文档
        docs = self._vectorstore.similarity_search(question, k=top_k)

        # 2. 拼接上下文
        context_parts = []
        sources = []
        for i, doc in enumerate(docs, 1):
            src = doc.metadata.get("source", "未知来源")
            context_parts.append(f"[来源{i}: {src}]\n{doc.page_content}")
            sources.append(src)

        context = "\n\n---\n\n".join(context_parts)

        # 3. 构建 prompt
        system_prompt = """你是一个基于知识库的智能助手。请根据以下规则回答用户问题：

1. 优先使用下方【参考资料】中的内容回答问题
2. 如果参考资料中有相关信息，请基于这些信息给出准确答案
3. 如果参考资料中没有相关信息，请诚实地说"知识库中暂无相关信息"，然后可以根据你的知识做补充说明
4. 回答要简洁、清晰、有条理，使用 Markdown 格式"""

        user_prompt = f"""【参考资料】
{context}

【用户问题】
{question}"""

        # 4. 调用 LLM 流式生成
        from langchain_core.messages import SystemMessage, HumanMessage

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # 每次请求创建新的 LLM 实例，确保参数生效
        llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True,
        )

        full_text = ""
        for chunk in llm.stream(messages):
            if chunk.content:
                full_text += chunk.content
                yield {"type": "text", "content": chunk.content}

        # 最后返回来源
        yield {"type": "sources", "sources": sources}
        yield {"type": "done", "content": full_text}


# 全局单例
_agent: RAGAgent | None = None


def get_agent() -> RAGAgent:
    global _agent
    if _agent is None:
        _agent = RAGAgent()
    return _agent
