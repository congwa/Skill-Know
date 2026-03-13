"""通用异步重试机制

参考 OpenViking 的指数退避重试模式，为外部调用提供健壮性保障。
"""

import asyncio
import functools
from typing import Any, Callable

from app.core.logging import get_logger

logger = get_logger("retry")


async def async_retry(
    func: Callable,
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple = (Exception,),
    **kwargs: Any,
) -> Any:
    """执行带重试的异步调用。

    Args:
        func: 异步函数
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒），每次重试翻倍
        exceptions: 需要重试的异常类型
    """
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except exceptions as e:
            last_error = e
            if attempt < max_retries:
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"调用失败，{delay:.1f}s 后重试 ({attempt + 1}/{max_retries}): {e}"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"达到最大重试次数 ({max_retries}): {e}")
    raise last_error  # type: ignore[misc]


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple = (Exception,),
):
    """重试装饰器。

    Usage:
        @with_retry(max_retries=3, base_delay=1.0)
        async def call_api():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await async_retry(
                func,
                *args,
                max_retries=max_retries,
                base_delay=base_delay,
                exceptions=exceptions,
                **kwargs,
            )

        return wrapper

    return decorator
