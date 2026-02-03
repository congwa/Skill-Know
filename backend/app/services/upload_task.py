"""批量上传任务管理

管理批量上传任务状态和进度推送。
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, AsyncGenerator

from app.core.logging import get_logger

logger = get_logger("upload_task")


class UploadStep(StrEnum):
    """上传步骤"""
    QUEUED = "queued"           # 排队中
    UPLOADING = "uploading"     # 上传中
    PARSING = "parsing"         # 解析中
    ANALYZING = "analyzing"     # 分析中
    GENERATING = "generating"   # 生成 Skill 中
    SAVING = "saving"           # 保存中
    COMPLETED = "completed"     # 完成
    FAILED = "failed"           # 失败


class StepStatus(StrEnum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class FileProgress:
    """单个文件的进度"""
    file_id: str
    filename: str
    step: UploadStep = UploadStep.QUEUED
    status: StepStatus = StepStatus.PENDING
    progress: int = 0           # 0-100
    message: str = ""
    error: str | None = None
    result: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskState:
    """任务状态"""
    task_id: str
    files: dict[str, FileProgress] = field(default_factory=dict)
    total: int = 0
    completed: int = 0
    failed: int = 0
    status: str = "running"  # running | completed | failed
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ProgressEvent:
    """进度事件"""
    task_id: str
    file_id: str
    filename: str
    step: str
    status: str
    progress: int
    message: str = ""
    error: str | None = None
    result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "file_id": self.file_id,
            "filename": self.filename,
            "step": self.step,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "error": self.error,
            "result": self.result,
        }


class TaskManager:
    """任务管理器（单例）"""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tasks = {}
            cls._instance._subscribers = {}
            cls._instance._task_locks = {}  # 每个任务一个锁
        return cls._instance
    
    def _get_task_lock(self, task_id: str) -> asyncio.Lock:
        """获取任务锁"""
        if task_id not in self._task_locks:
            self._task_locks[task_id] = asyncio.Lock()
        return self._task_locks[task_id]
    
    def create_task(self, filenames: list[str]) -> str:
        """创建新任务
        
        Args:
            filenames: 文件名列表
            
        Returns:
            task_id
        """
        task_id = str(uuid.uuid4())
        
        files = {}
        for filename in filenames:
            file_id = str(uuid.uuid4())
            files[file_id] = FileProgress(
                file_id=file_id,
                filename=filename,
            )
        
        self._tasks[task_id] = TaskState(
            task_id=task_id,
            files=files,
            total=len(filenames),
        )
        
        self._subscribers[task_id] = []
        
        logger.info(f"创建上传任务: {task_id}, 文件数: {len(filenames)}")
        
        return task_id
    
    def get_task(self, task_id: str) -> TaskState | None:
        """获取任务状态"""
        return self._tasks.get(task_id)
    
    def get_file_ids(self, task_id: str) -> list[str]:
        """获取任务中的文件 ID 列表"""
        task = self._tasks.get(task_id)
        if not task:
            return []
        return list(task.files.keys())
    
    async def update_progress(
        self,
        task_id: str,
        file_id: str,
        step: UploadStep,
        status: StepStatus,
        progress: int = 0,
        message: str = "",
        error: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        """更新进度（线程安全）
        
        Args:
            task_id: 任务 ID
            file_id: 文件 ID
            step: 当前步骤
            status: 步骤状态
            progress: 进度百分比
            message: 提示信息
            error: 错误信息
            result: 完成结果
        """
        task = self._tasks.get(task_id)
        if not task or file_id not in task.files:
            return
        
        # 使用锁保护更新操作
        task_lock = self._get_task_lock(task_id)
        async with task_lock:
            file_progress = task.files[file_id]
            
            # 防止重复计数
            was_completed = file_progress.step in (UploadStep.COMPLETED, UploadStep.FAILED)
            
            file_progress.step = step
            file_progress.status = status
            file_progress.progress = progress
            file_progress.message = message
            file_progress.error = error
            file_progress.result = result
            file_progress.updated_at = datetime.now()
            
            # 更新任务统计（只在首次完成/失败时计数）
            if not was_completed:
                if step == UploadStep.COMPLETED:
                    task.completed += 1
                elif step == UploadStep.FAILED:
                    task.failed += 1
            
            # 检查任务是否完成
            if task.completed + task.failed >= task.total:
                task.status = "completed" if task.failed == 0 else "partial"
        
        # 创建事件
        event = ProgressEvent(
            task_id=task_id,
            file_id=file_id,
            filename=file_progress.filename,
            step=step.value,
            status=status.value,
            progress=progress,
            message=message,
            error=error,
            result=result,
        )
        
        # 通知订阅者（在锁外执行，避免死锁）
        await self._notify_subscribers(task_id, event)
    
    async def _notify_subscribers(
        self,
        task_id: str,
        event: ProgressEvent,
    ) -> None:
        """通知订阅者（非阻塞）"""
        subscribers = self._subscribers.get(task_id, [])
        for queue in subscribers:
            try:
                # 使用 put_nowait 避免阻塞，如果队列满则丢弃
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"事件队列已满，丢弃事件: {event.file_id}")
    
    def subscribe(self, task_id: str) -> asyncio.Queue:
        """订阅任务进度
        
        Args:
            task_id: 任务 ID
            
        Returns:
            事件队列（有界，防止内存泄漏）
        """
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        
        # 使用有界队列，防止消费者断开时内存泄漏
        queue = asyncio.Queue(maxsize=100)
        self._subscribers[task_id].append(queue)
        
        logger.debug(f"新订阅者加入任务: {task_id}")
        
        return queue
    
    def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        """取消订阅"""
        if task_id in self._subscribers:
            try:
                self._subscribers[task_id].remove(queue)
            except ValueError:
                pass
    
    async def get_event_stream(
        self,
        task_id: str,
    ) -> AsyncGenerator[ProgressEvent, None]:
        """获取事件流
        
        Args:
            task_id: 任务 ID
            
        Yields:
            ProgressEvent
        """
        task = self._tasks.get(task_id)
        if not task:
            return
        
        queue = self.subscribe(task_id)
        
        try:
            # 先发送当前状态
            for file_progress in task.files.values():
                yield ProgressEvent(
                    task_id=task_id,
                    file_id=file_progress.file_id,
                    filename=file_progress.filename,
                    step=file_progress.step.value,
                    status=file_progress.status.value,
                    progress=file_progress.progress,
                    message=file_progress.message,
                    error=file_progress.error,
                    result=file_progress.result,
                )
            
            # 持续监听新事件
            while task.status == "running":
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                    
                    # 检查是否所有文件都完成
                    if task.completed + task.failed >= task.total:
                        break
                except asyncio.TimeoutError:
                    # 发送心跳
                    continue
        finally:
            self.unsubscribe(task_id, queue)
    
    def cleanup_task(self, task_id: str) -> None:
        """清理任务"""
        if task_id in self._tasks:
            del self._tasks[task_id]
        if task_id in self._subscribers:
            del self._subscribers[task_id]


# 全局单例
task_manager = TaskManager()
