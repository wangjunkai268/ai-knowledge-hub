"""
FastAPI 应用入口 — 组装各功能模块路由
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chat_router, kbs_router, documents_router, system_router

app = FastAPI(title="AI Knowledge Hub API")

# CORS 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册各功能模块路由
app.include_router(chat_router)        # 对话流式
app.include_router(kbs_router)         # 知识库管理
app.include_router(documents_router)   # 文档管理
app.include_router(system_router)      # 统计 / 健康检查


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
