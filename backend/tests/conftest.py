"""Pytest 配置"""

import os

import pytest

# 测试环境下为 Settings 提供必要的必填配置
os.environ.setdefault("LLM_PROVIDER", "test")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_BASE_URL", "https://example.invalid")
os.environ.setdefault("LLM_CHAT_MODEL", "test-model")
os.environ.setdefault("EMBEDDING_MODEL", "test-embedding")
os.environ.setdefault("EMBEDDING_DIMENSION", "1024")


@pytest.fixture
def anyio_backend():
    return "asyncio"
