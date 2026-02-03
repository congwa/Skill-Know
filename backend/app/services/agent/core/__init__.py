"""Agent 核心模块

提供 Agent 服务和工厂功能。
"""

from app.services.agent.core.service import AgentService, agent_service
from app.services.agent.core.factory import build_agent

__all__ = ["AgentService", "agent_service", "build_agent"]
