"""日志配置"""

import sys
from loguru import logger


def setup_logging(debug: bool = False) -> None:
    """配置日志"""
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG" if debug else "INFO",
        colorize=True,
    )


def get_logger(name: str):
    """获取命名日志器"""
    return logger.bind(name=name)
