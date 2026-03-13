"""健康监控 Observer

参考 OpenViking BaseObserver 模式，提供各组件的健康状态监控。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger("observer")


@dataclass
class ComponentStatus:
    """单个组件的状态"""

    name: str
    healthy: bool
    detail: dict[str, Any] = field(default_factory=dict)


class QueueObserver:
    """队列观察者"""

    async def get_status(self) -> ComponentStatus:
        try:
            from app.core.service import get_service

            svc = get_service()
            if svc.queue_manager:
                counts = svc.queue_manager.pending_counts
                return ComponentStatus(
                    name="queue",
                    healthy=True,
                    detail={"pending": counts, "running": svc.queue_manager._running},
                )
            return ComponentStatus(name="queue", healthy=False, detail={"error": "未初始化"})
        except Exception as e:
            return ComponentStatus(name="queue", healthy=False, detail={"error": str(e)})


class VectorObserver:
    """向量存储观察者"""

    async def get_status(self) -> ComponentStatus:
        try:
            from app.core.database import get_db_context
            from app.core.service import get_service

            svc = get_service()
            async with get_db_context() as session:
                vs = svc.get_vector_store(session)
                stats = await vs.get_activity_stats()
                return ComponentStatus(
                    name="vector_store",
                    healthy=True,
                    detail=stats,
                )
        except Exception as e:
            return ComponentStatus(name="vector_store", healthy=False, detail={"error": str(e)})


class DatabaseObserver:
    """数据库观察者"""

    async def get_status(self) -> ComponentStatus:
        try:
            from sqlalchemy import text

            from app.core.database import get_db_context

            async with get_db_context() as session:
                await session.execute(text("SELECT 1"))
                return ComponentStatus(name="database", healthy=True, detail={"status": "connected"})
        except Exception as e:
            return ComponentStatus(name="database", healthy=False, detail={"error": str(e)})


class LLMConfigObserver:
    """LLM 配置观察者"""

    async def get_status(self) -> ComponentStatus:
        try:
            from app.core.database import get_db_context
            from app.services.system_config import SystemConfigService

            async with get_db_context() as session:
                config_service = SystemConfigService(session)
                config = await config_service.get_llm_config()
                has_key = bool(config.get("api_key"))
                return ComponentStatus(
                    name="llm_config",
                    healthy=has_key,
                    detail={
                        "provider": config.get("provider", "unknown"),
                        "model": config.get("chat_model", "unknown"),
                        "has_api_key": has_key,
                        "base_url": (config.get("base_url") or "")[:50],
                    },
                )
        except Exception as e:
            return ComponentStatus(name="llm_config", healthy=False, detail={"error": str(e)})


class HealthMonitor:
    """综合健康监控"""

    def __init__(self):
        self._observers = [
            DatabaseObserver(),
            QueueObserver(),
            VectorObserver(),
            LLMConfigObserver(),
        ]

    async def check_health(self) -> dict[str, Any]:
        """执行全面健康检查"""
        statuses = []
        for obs in self._observers:
            status = await obs.get_status()
            statuses.append(status)

        all_healthy = all(s.healthy for s in statuses)
        return {
            "status": "healthy" if all_healthy else "degraded",
            "components": {
                s.name: {"healthy": s.healthy, **s.detail}
                for s in statuses
            },
        }

    async def check_simple(self) -> dict[str, str]:
        """简单健康检查（快速响应）"""
        return {"status": "healthy"}
