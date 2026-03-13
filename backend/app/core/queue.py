"""异步任务队列

参考 OpenViking QueueManager / Observer 模式，提供基于 asyncio.Queue 的异步任务处理。
用于文档上传后的异步处理：解析 → 摘要生成 → 向量嵌入。
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable

from app.core.logging import get_logger

logger = get_logger("queue")


class TaskType(str, Enum):
    EMBEDDING = "embedding"
    SKILL_INDEXING = "skill_indexing"


@dataclass
class QueueTask:
    """队列任务"""
    task_type: TaskType
    payload: dict[str, Any]
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3


class QueueManager:
    """异步任务队列管理器

    管理多个命名队列，每个队列有独立的消费者协程。
    """

    def __init__(self):
        self._queues: dict[str, asyncio.Queue[QueueTask]] = {}
        self._handlers: dict[str, Callable[[QueueTask], Awaitable[None]]] = {}
        self._workers: dict[str, asyncio.Task] = {}
        self._running = False

    def register_handler(
        self, task_type: TaskType, handler: Callable[[QueueTask], Awaitable[None]]
    ) -> None:
        """注册任务处理器"""
        self._handlers[task_type.value] = handler
        self._queues[task_type.value] = asyncio.Queue()
        logger.info(f"注册队列处理器: {task_type.value}")

    async def enqueue(self, task: QueueTask) -> None:
        """将任务入队"""
        queue_name = task.task_type.value
        if queue_name not in self._queues:
            logger.warning(f"未注册的队列类型: {queue_name}")
            return
        await self._queues[queue_name].put(task)
        logger.debug(f"任务入队: {queue_name}", payload_keys=list(task.payload.keys()))

    async def start(self) -> None:
        """启动所有队列的消费者"""
        self._running = True
        for queue_name in self._queues:
            worker = asyncio.create_task(self._consume(queue_name))
            self._workers[queue_name] = worker
            logger.info(f"队列消费者启动: {queue_name}")

    async def stop(self) -> None:
        """停止所有消费者"""
        self._running = False
        for name, worker in self._workers.items():
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
            logger.info(f"队列消费者停止: {name}")
        self._workers.clear()

    async def _consume(self, queue_name: str) -> None:
        """消费队列任务"""
        queue = self._queues[queue_name]
        handler = self._handlers.get(queue_name)
        if not handler:
            return

        while self._running:
            try:
                task = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                await handler(task)
                logger.debug(f"任务完成: {queue_name}")
            except Exception as e:
                task.retry_count += 1
                if task.retry_count < task.max_retries:
                    await queue.put(task)
                    logger.warning(
                        f"任务失败，重试 {task.retry_count}/{task.max_retries}: {e}"
                    )
                else:
                    logger.error(f"任务达到最大重试次数: {queue_name}, error={e}")

    @property
    def pending_counts(self) -> dict[str, int]:
        return {name: q.qsize() for name, q in self._queues.items()}
