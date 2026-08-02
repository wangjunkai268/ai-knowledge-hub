"""API 路由模块汇总"""
from .chat import router as chat_router
from .kbs import router as kbs_router
from .documents import router as documents_router
from .system import router as system_router

__all__ = ["chat_router", "kbs_router", "documents_router", "system_router"]
