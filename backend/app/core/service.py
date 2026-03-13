"""SkillKnowService 聚合服务

参考 OpenViking OpenVikingService 的组合模式，统一管理所有子服务的生命周期。
提供 get_service() / set_service() 依赖注入机制。
"""

from typing import Any

from app.core.logging import get_logger
from app.core.queue import QueueManager, QueueTask, TaskType
from app.core.vector_store import VectorStore
from app.parse.registry import ParserRegistry, get_registry

logger = get_logger("service")


class SkillKnowService:
    """Skill-Know 核心聚合服务

    组合所有子服务，统一初始化和生命周期管理。
    """

    def __init__(self):
        self.parser_registry: ParserRegistry | None = None
        self.vector_store: VectorStore | None = None
        self.queue_manager: QueueManager | None = None
        self._embedder: Any = None
        self._initialized = False

    async def initialize(self) -> None:
        """初始化所有子服务"""
        if self._initialized:
            return

        # 1. 初始化解析器注册表
        self.parser_registry = get_registry()
        logger.info(
            "解析器注册表初始化完成",
            parsers=self.parser_registry.list_parsers(),
            extensions=self.parser_registry.list_supported_extensions(),
        )

        # 2. 初始化异步任务队列
        self.queue_manager = QueueManager()
        self.queue_manager.register_handler(TaskType.EMBEDDING, self._handle_embedding)
        self.queue_manager.register_handler(
            TaskType.SKILL_INDEXING, self._handle_skill_indexing
        )
        await self.queue_manager.start()
        logger.info("异步任务队列启动完成")

        # 3. 尝试初始化 Embedder
        await self._init_embedder()

        self._initialized = True
        logger.info("SkillKnowService 初始化完成")

    async def shutdown(self) -> None:
        """关闭所有子服务"""
        if self.queue_manager:
            await self.queue_manager.stop()
        self._initialized = False
        logger.info("SkillKnowService 已关闭")

    async def _init_embedder(self) -> None:
        """尝试初始化向量嵌入器"""
        try:
            from app.core.database import get_db_context
            from app.services.system_config import SystemConfigService

            async with get_db_context() as session:
                config_service = SystemConfigService(session)
                llm_config = await config_service.get_llm_config()

                if llm_config.get("api_key"):
                    from langchain_openai import OpenAIEmbeddings
                    self._embedder = OpenAIEmbeddings(
                        api_key=llm_config["api_key"],
                        base_url=llm_config.get("base_url", "https://api.openai.com/v1"),
                        model="text-embedding-3-small",
                    )
                    logger.info("向量嵌入器初始化完成")
                else:
                    logger.info("未配置 API Key，跳过向量嵌入器初始化")
        except Exception as e:
            logger.warning(f"向量嵌入器初始化失败: {e}")

    def get_vector_store(self, session: Any) -> VectorStore:
        """获取绑定了 session 的 VectorStore 实例"""
        return VectorStore(session=session, embedder=self._embedder)

    async def _handle_embedding(self, task: QueueTask) -> None:
        """处理嵌入任务"""
        from app.core.context import Context
        from app.core.database import get_db_context

        ctx_data = task.payload.get("context")
        if not ctx_data:
            return

        context = Context.from_dict(ctx_data)
        async with get_db_context() as session:
            vs = self.get_vector_store(session)
            from app.core.context import ContextLevel
            await vs.index_context(context, ContextLevel.ABSTRACT)
            logger.info("异步嵌入完成", uri=context.uri)

    async def _handle_skill_indexing(self, task: QueueTask) -> None:
        """处理技能索引任务"""
        from app.core.context import Context, ContextLevel
        from app.core.database import get_db_context

        ctx_data = task.payload.get("context")
        if not ctx_data:
            return

        context = Context.from_dict(ctx_data)
        async with get_db_context() as session:
            vs = self.get_vector_store(session)
            await vs.index_context(context, ContextLevel.ABSTRACT)
            if context.overview:
                await vs.index_context(context, ContextLevel.OVERVIEW)
            logger.info("异步技能索引完成", uri=context.uri)


_service: SkillKnowService | None = None


def get_service() -> SkillKnowService:
    """获取全局 SkillKnowService 实例"""
    global _service
    if _service is None:
        _service = SkillKnowService()
    return _service


def set_service(service: SkillKnowService) -> None:
    """设置全局 SkillKnowService 实例"""
    global _service
    _service = service
