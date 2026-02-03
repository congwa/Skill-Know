"""Skill-Know 知识库系统主应用"""

import warnings

# 过滤 Pydantic 序列化警告（ToolRuntime.context 类型不匹配）
# message 使用正则匹配，.*表示匹配任意字符
warnings.filterwarnings(
    "ignore",
    message=r"Pydantic serializer warnings:.*",
    category=UserWarning,
    module=r"pydantic\.main",
)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging, get_logger
from app.routers import (
    documents,
    skills,
    prompts,
    conversations,
    chat,
    quick_setup,
    search,
    upload,
)
from app.services.skill_initializer import init_system_skills

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    setup_logging(settings.DEBUG)
    logger.info("启动 Skill-Know 知识库系统", version=settings.APP_VERSION)

    # 初始化数据库
    await init_db()

    # 初始化系统技能
    await init_system_skills()

    yield

    logger.info("关闭 Skill-Know 知识库系统")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="以 Skill 搜索为主的知识库系统",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(documents.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(prompts.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(quick_setup.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(upload.router, prefix="/api")


@app.get("/")
async def root():
    """根路由"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
