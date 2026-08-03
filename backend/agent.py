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

# 上下文压缩：保留最近 N 条原文，更早的折叠成摘要
MAX_WINDOW_MSGS = 20


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
        """
        构建工具 schema（OpenAI 风格 dict）
        知识库检索由代码默认执行（混合 RAG），不设为工具让模型猜；
        工具只有 search_web，在知识库结果不足时由模型自主决定调用
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "联网搜索获取最新信息。当知识库检索结果为空、不相关，或问题涉及实时/时效性数据时使用。",
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

    def _run_tool(self, tool_call: dict) -> str:
        """执行单个工具调用，返回结果文本"""
        name = tool_call.get("name", "")
        args = tool_call.get("args", {})
        query = args.get("query", "")

        if name == "search_web":
            key = os.getenv("SERPAPI_API_KEY")
            if not key:
                return "未配置 SERPAPI_API_KEY，无法联网搜索。请基于知识库或已有知识回答。"
            try:
                import requests
                resp = requests.get(
                    "https://serpapi.com/search.json",
                    params={
                        "q": query,
                        "api_key": key,
                        "engine": "google",
                        "hl": "zh-cn",
                        "num": 5,
                    },
                    timeout=15,
                )
                organic = resp.json().get("organic_results", [])
                if not organic:
                    return "联网搜索没有返回结果。"
                return "\n".join(
                    f"{item.get('title', '')}\n{item.get('snippet', '')}"
                    for item in organic
                )
            except Exception:
                return "联网搜索失败，请基于知识库或已有知识回答。"

        return f"未知工具: {name}"

    def _summarize(self, llm, early_msgs: list) -> str:
        """把窗口外早期对话压成一段中文摘要（上下文压缩）"""
        lines = []
        for item in early_msgs:
            role = "用户" if item.get("role") == "user" else "助手"
            content = item.get("content", "")
            if content:
                lines.append(f"{role}: {content}")
        if not lines:
            return ""

        transcript = "\n".join(lines)
        prompt = f"""以下是更早的对话记录，请总结成一段中文摘要（200字内）。
要求：保留主题、重要事实、关键指代关系，不要遗漏用户提到的偏好或背景信息。
只输出摘要文本，不要任何其他内容。

对话记录：
{transcript}"""
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.content.strip()

    # ─── 查询主流程 ──────────────────────────────────────

    def query_stream(self, question: str, top_k: int = 5, temperature: float = 0.7, max_tokens: int = 2048, kb_id: str | None = None, history: list | None = None):
        """
        Tool Calling 流式查询，逐事件 yield
        事件类型: text / tool / done / error
        - {"type": "tool", "name", "status": "calling"|"done"} — 工具调用过程
        - {"type": "text", "content"} — 最终回答全文（前端打字机逐字显示）
        kb_id=None → 全局检索；指定 → 限定该知识库
        history=[{"role","content"}...] → 多轮对话上下文
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

        # 混合 RAG：代码默认检索知识库（不设成工具让模型猜），真实结果注入给 LLM
        kb_docs = self._vectorstore.similarity_search(
            question, k=top_k, filter={"kb_id": kb_id} if kb_id else None
        )
        if kb_docs:
            kb_context = "\n\n---\n\n".join(
                f"[{d.metadata.get('source', '未知来源')}]\n{d.page_content}"
                for d in kb_docs
            )
            kb_context_text = f"\n\n【知识库检索结果】\n{kb_context}"
        else:
            kb_context_text = "\n\n【知识库检索结果】\n（知识库中未检索到相关内容）"

        system_prompt = """你是一个智能助手。已为你提供【知识库检索结果】作为参考。

规则：
1. 优先基于【知识库检索结果】回答，并引用来源
2. 当检索结果为空、不相关，或问题涉及实时/时效性信息时，调用 search_web 工具联网搜索补充
3. 简单常识或闲聊问题，即使有检索结果也可直接回答
4. 工具结果不足以回答时，诚实说明，然后基于已有知识补充
5. 回答要简洁、清晰、有条理，使用 Markdown 格式"""
        system_prompt += kb_context_text

        # 上下文压缩：最近 N 条保留原文，更早的折叠成摘要内联进 system prompt
        history = history or []
        early = history[:-MAX_WINDOW_MSGS]          # 窗口外早期对话
        recent = history[-MAX_WINDOW_MSGS:]         # 窗口内原文

        if early:
            summary = self._summarize(llm, early)
            if summary:
                system_prompt += f"\n\n【早期对话摘要】\n{summary}"

        # 构造 messages：System(含摘要) + 窗口原文 + 当前问题
        history_msgs = []
        for item in recent:
            role = item.get("role")
            content = item.get("content", "")
            if not content:
                continue
            if role == "user":
                history_msgs.append(HumanMessage(content=content))
            elif role == "assistant":
                history_msgs.append(AIMessage(content=content))

        messages = [
            SystemMessage(content=system_prompt),
            *history_msgs,
            HumanMessage(content=question),
        ]

        # Tool Calling 循环：LLM 自主决定是否调用工具
        for _ in range(MAX_TOOL_ITERATIONS):
            response = llm.invoke(messages, tools=tools)

            if response.tool_calls:
                # 有工具调用 → 逐个执行并回传结果
                for tc in response.tool_calls:
                    tool_name = tc.get("name", 
                                    "未知工具")
                    yield {"type": "tool", "name": tool_name, "status": "calling"}

                    result = self._run_tool(tc)

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
