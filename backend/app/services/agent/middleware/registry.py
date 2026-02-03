"""中间件注册表

集中管理所有中间件，支持按顺序构建中间件链。
与 embedease-ai 项目保持一致的导入和使用方式。
"""

from typing import Any

from app.core.logging import get_logger

logger = get_logger("middleware.registry")


def build_middlewares(model: Any, session: Any = None, emitter: Any = None) -> list[Any]:
    """构建中间件链（与 embedease-ai 一致）
    
    Args:
        model: LLM 模型实例
        session: 数据库会话（用于动态工具加载）
        emitter: 事件发射器
        
    Returns:
        按顺序排列的中间件列表
    """
    from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
    from app.services.agent.middleware.logging import LoggingMiddleware
    from app.services.agent.middleware.dynamic_tools import StatefulToolMiddleware
    
    middlewares: list[Any] = []
    
    # 状态驱动的动态工具注入中间件（需要在最前面，以便注册额外工具）
    stateful_tool_middleware = StatefulToolMiddleware(
        session=session,
        emitter=emitter,
        llm=model,
    )
    middlewares.append(stateful_tool_middleware)
    logger.info(
        "✓ 注入中间件: StatefulToolMiddleware",
        has_session=session is not None,
        has_emitter=emitter is not None,
        has_llm=model is not None,
    )
    
    # 工具调用限制中间件
    tool_limit = ToolCallLimitMiddleware(
        thread_limit=20,
        run_limit=10,
        exit_behavior="error",
    )
    middlewares.append(tool_limit)
    logger.info(
        "✓ 注入中间件: ToolCallLimitMiddleware",
        thread_limit=20,
        run_limit=10,
        exit_behavior="error",
    )
    
    # 日志中间件（记录 LLM 调用详情，并发送事件到前端）
    logging_middleware = LoggingMiddleware(emitter=emitter)
    middlewares.append(logging_middleware)
    logger.info("✓ 注入中间件: LoggingMiddleware", has_emitter=emitter is not None)
    
    # 打印所有注入的中间件
    logger.info(
        "🔧 构建中间件链完成",
        middleware_count=len(middlewares),
        middlewares=[type(m).__name__ for m in middlewares],
    )
    
    return middlewares
