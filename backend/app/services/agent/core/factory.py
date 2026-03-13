"""Agent 工厂

从配置构建 LangGraph Agent 实例。
与 embedease-ai 项目保持一致的导入和使用方式。
"""

from typing import Any

from langchain.agents import create_agent
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from app.core.logging import get_logger
from app.services.agent.middleware.registry import build_middlewares
from app.services.streaming.context import ChatContext

logger = get_logger("agent.factory")


async def build_agent(
    model: Any,
    system_prompt: str,
    checkpointer: BaseCheckpointSaver,
    session: Any = None,
    emitter: Any = None,
) -> CompiledStateGraph:
    """构建 Agent 实例

    Args:
        model: LLM 模型实例
        system_prompt: 系统提示词
        checkpointer: LangGraph checkpoint saver
        session: 数据库会话
        emitter: 事件发射器

    Returns:
        编译后的 LangGraph Agent
    """
    # 初始工具列表为空，由 StatefulToolMiddleware 根据阶段动态注入
    tools: list = []

    # 构建中间件链（使用 LangChain 官方中间件）
    middlewares = build_middlewares(model=model, session=session, emitter=emitter)

    # 创建 Agent（与 embedease-ai 一致的方式）
    try:
        agent_kwargs: dict[str, Any] = {
            "model": model,
            "tools": tools,
            "system_prompt": system_prompt,
            "checkpointer": checkpointer,
            "middleware": middlewares,
            "context_schema": ChatContext,
        }

        # 打印传入 create_agent 的详细参数
        tool_names = [t.name for t in tools]
        middleware_types = [type(m).__name__ for m in middlewares] if middlewares else []
        model_name = getattr(model, "model_name", None) or getattr(model, "model", None)
        
        logger.info("📋 create_agent 参数:")
        logger.info(f"   - model: {type(model).__name__} ({model_name})")
        logger.info(f"   - tools ({len(tools)}): {tool_names}")
        logger.info(f"   - middlewares ({len(middlewares) if middlewares else 0}): {middleware_types}")
        logger.info(f"   - context_schema: {ChatContext.__name__}")
        logger.info(f"   - system_prompt_len: {len(system_prompt) if system_prompt else 0}")

        agent = create_agent(**agent_kwargs)

        logger.info(
            "✅ 构建 Agent 实例完成",
            tool_count=len(tools),
            middleware_count=len(middlewares) if middlewares else 0,
        )

        return agent

    except TypeError as e:
        # 兼容较老版本：不支持某些参数时回退
        logger.warning(f"使用兼容模式构建 Agent: {e}")
        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            checkpointer=checkpointer,
        )
        return agent
