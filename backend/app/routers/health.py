"""健康检查路由

参考 OpenViking Observer API，提供系统健康状态端点。
"""

from fastapi import APIRouter

from app.core.observer import HealthMonitor

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """简单健康检查"""
    monitor = HealthMonitor()
    return await monitor.check_simple()


@router.get("/detail")
async def health_detail():
    """详细健康检查（含各组件状态）"""
    monitor = HealthMonitor()
    return await monitor.check_health()
