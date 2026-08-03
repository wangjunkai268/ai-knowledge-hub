"""
Agent 核心 — 基于 Tool Calling 的智能体

LLM 自主决定是否调用工具（知识库检索 / 联网搜索），
根据工具结果组织回答。这是从"RAG 应用"到"Agent"的关键。
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

load_dotenv()

ROOT = Path(__file__).parent
CHROMA_DIR = ROOT / "chroma_db"
EMBEDDING_MODEL = "shibing624/text2vec-base-chinese"

# 工具调用循环上限（防止 LLM 无限调用工具）
MAX_TOOL_ITERATIONS = 5


class RAGAgent:
    def __init__(self):
        self._embeddings = None
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

    # ─── 工具定义 ────────────────────────────────────────

    def _make_tools(self) -> list:
        """构建工具 schema（OpenAI 风格 dict，避免 LangChain 工具类序列化问题）"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_kb",
                    "description": "在知识库中检索信息，返回相关文档片段。当用户问题需要基于已有文档/资料回答时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "用于检索知识库的关键词或问题",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "联网搜索获取最新信息。当知识库没有答案、或问题涉及实时/时效性数据时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "用于联网搜索的关键词或问题",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
        ]

    def _run_tool(self, tool_call: dict, kb_id: str | None, top_k: int = 5) -> str:
        """执行单个工具调用，返回结果文本"""
        name = tool_call.get("name", "")
        args = tool_call.get("args", {})
        query = args.get("query", "")

        if name == "search_kb":
            docs = self._vectorstore.similarity_search(
                query, k=top_k, filter={"kb_id": kb_id} if kb_id else None
            )
            if not docs:
                return "知识库中没有找到相关信息。"
            return "\n\n---\n\n".join(
                f"[{d.metadata.get('source', '未知来源')}]\n{d.page_content}"
                for d in docs
            )

        if name == "search_web":
            try:
                from duckduckgo_search import DDGS
                results = DDGS().text(query, max_results=5)
                if not results:
                    return "联网搜索没有返回结果。"
                return "\n".join(f"{r['title']}\n{r['body']}" for r in results)
            except Exception:
                return "联网搜索暂时不可用，请基于知识库或已有知识回答。"

        return f"未知工具: {name}"

    # ─── 查询主流程 ──────────────────────────────────────

    def query_stream(self, question: str, top_k: int = 5, temperature: float = 0.7, max_tokens: int = 2048, kb_id: str | None = None):
        """
        Tool Calling 流式查询，逐事件 yield
        事件类型: text / tool / done / error
        - {"type": "tool", "name", "status": "calling"|"done"} — 工具调用过程
        - {"type": "text", "content"} — 最终回答全文（前端打字机逐字显示）
        kb_id=None → 全局检索；指定 → 限定该知识库
        """
        if not self._vectorstore:
            yield {"type": "error", "content": "知识库为空，请先上传文档。"}
            return

        llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True,
        )

        tools = self._make_tools()

        system_prompt = """你是一个智能助手，可以使用工具获取信息来回答问题。

规则：
1. 当用户问题需要基于文档/资料回答时，调用 search_kb 工具检索知识库
2. 当问题涉及实时信息、且知识库可能没有答案时，调用 search_web 工具联网搜索
3. 简单常识问题（如数学计算）可直接回答，不需要调用工具
4. 根据工具返回的结果组织回答，引用信息来源
5. 如果工具结果不足以回答问题，诚实说明，然后基于已有知识补充
6. 回答要简洁、清晰、有条理，使用 Markdown 格式"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question),
        ]

        # Tool Calling 循环：LLM 自主决定是否调用工具
        for _ in range(MAX_TOOL_ITERATIONS):
            response = llm.invoke(messages, tools=tools)

            if response.tool_calls:
                # 有工具调用 → 逐个执行并回传结果
                for tc in response.tool_calls:
                    tool_name = tc.get("name", "未知工具")
                    yield {"type": "tool", "name": tool_name, "status": "calling"}

                    result = self._run_tool(tc, kb_id, top_k)

                    yield {"type": "tool", "name": tool_name, "status": "done"}
                    messages.append(AIMessage(content="", tool_calls=[tc]))
                    messages.append(ToolMessage(content=result, tool_call_id=tc.get("id", "")))
                continue

            # 无工具调用 → 最终回答
            if response.content:
                yield {"type": "text", "content": response.content}
                yield {"type": "done", "content": response.content}
            return

        # 超过循环上限仍未完成
        yield {"type": "error", "content": "工具调用次数过多，请换个问法试试。"}


# 全局单例
_agent: RAGAgent | None = None


def get_agent() -> RAGAgent:
    global _agent
    if _agent is None:
        _agent = RAGAgent()
    return _agent
