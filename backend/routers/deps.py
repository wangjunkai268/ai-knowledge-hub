"""共享依赖 — agent 全局单例管理"""
from typing import Optional

from agent import RAGAgent

# 全局 agent 实例（各 router 共享）
_agent: Optional[RAGAgent] = None


def get_agent() -> RAGAgent:
    """获取 agent 单例"""
    global _agent
    if _agent is None:
        _agent = RAGAgent()
    return _agent


def refresh_agent():
    """重建/上传/删除后刷新 agent 连接"""
    global _agent
    if _agent:
        _agent.reload()
    else:
        _agent = RAGAgent()
