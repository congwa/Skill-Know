"""models.dev API 集成

从 https://models.dev/api.json 拉取模型能力配置，
只返回支持 tool_calling 的模型。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger("models_dev")

# 模块级缓存
_cached_data: dict[str, Any] | None = None
_cache_timestamp: float = 0.0

# 默认配置
MODELS_DEV_API_URL = "https://models.dev/api.json"
MODELS_DEV_TIMEOUT = 10.0
MODELS_DEV_CACHE_TTL = 86400.0  # 24 小时


@dataclass
class ModelInfo:
    """模型信息"""
    id: str                    # 模型 ID（如 "gpt-4o-mini"）
    name: str                  # 显示名称（如 "GPT-4o Mini"）
    provider: str              # 提供商 ID
    tool_calling: bool         # 是否支持工具调用
    structured_output: bool    # 是否支持结构化输出
    reasoning: bool            # 是否支持推理
    max_input_tokens: int      # 最大输入 token
    max_output_tokens: int     # 最大输出 token
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "tool_calling": self.tool_calling,
            "structured_output": self.structured_output,
            "reasoning": self.reasoning,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
        }


@dataclass
class ProviderInfo:
    """提供商信息"""
    id: str                    # 提供商 ID
    name: str                  # 显示名称
    base_url: str              # 默认 Base URL
    models: list[ModelInfo]    # 支持的模型列表
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "base_url": self.base_url,
            "models": [m.to_dict() for m in self.models],
        }


# 提供商配置（ID -> 显示名称, 默认 Base URL）
PROVIDER_CONFIG = {
    "openai": ("OpenAI", "https://api.openai.com/v1"),
    "anthropic": ("Anthropic", "https://api.anthropic.com"),
    "deepseek": ("DeepSeek", "https://api.deepseek.com/v1"),
    "siliconflow": ("硅基流动", "https://api.siliconflow.cn/v1"),
    "openrouter": ("OpenRouter", "https://openrouter.ai/api/v1"),
    "groq": ("Groq", "https://api.groq.com/openai/v1"),
    "together": ("Together AI", "https://api.together.xyz/v1"),
    "fireworks": ("Fireworks AI", "https://api.fireworks.ai/inference/v1"),
    "mistral": ("Mistral AI", "https://api.mistral.ai/v1"),
}


def _fetch_models_dev_data(
    api_url: str = MODELS_DEV_API_URL,
    timeout: float = MODELS_DEV_TIMEOUT,
) -> dict[str, Any]:
    """从 models.dev 拉取数据"""
    global _cached_data, _cache_timestamp
    
    # 检查缓存
    now = time.time()
    if _cached_data is not None and (now - _cache_timestamp) < MODELS_DEV_CACHE_TTL:
        logger.debug("使用缓存的 models.dev 数据")
        return _cached_data
    
    logger.info("开始拉取 models.dev 数据", api_url=api_url)
    
    try:
        response = httpx.get(api_url, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, dict):
            _cached_data = data
            _cache_timestamp = now
            logger.info("models.dev 数据拉取成功", provider_count=len(data))
            return data
        else:
            logger.warning("models.dev 响应格式错误")
            return {}
            
    except httpx.TimeoutException:
        logger.warning("models.dev 请求超时", timeout=timeout)
        return _cached_data or {}
    except httpx.HTTPStatusError as e:
        logger.warning("models.dev 请求失败", status_code=e.response.status_code)
        return _cached_data or {}
    except Exception as e:
        logger.warning("models.dev 请求异常", error=str(e))
        return _cached_data or {}


def _parse_model_info(
    model_id: str,
    model_data: dict[str, Any],
    provider_id: str,
) -> ModelInfo | None:
    """解析模型信息"""
    if not isinstance(model_data, dict):
        return None
    
    name = model_data.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    
    limit = model_data.get("limit") or {}
    
    return ModelInfo(
        id=name.strip(),
        name=name.strip(),
        provider=provider_id,
        tool_calling=bool(model_data.get("tool_call", False)),
        structured_output=bool(model_data.get("structured_output", False)),
        reasoning=bool(model_data.get("reasoning", False)),
        max_input_tokens=limit.get("context", 0) or 0,
        max_output_tokens=limit.get("output", 0) or 0,
    )


def get_providers(
    tool_calling_only: bool = True,
    api_url: str = MODELS_DEV_API_URL,
) -> list[ProviderInfo]:
    """获取提供商列表
    
    Args:
        tool_calling_only: 是否只返回支持工具调用的模型
        api_url: models.dev API URL
        
    Returns:
        提供商列表（只包含有可用模型的提供商）
    """
    data = _fetch_models_dev_data(api_url)
    
    providers = []
    
    for provider_id, (provider_name, base_url) in PROVIDER_CONFIG.items():
        provider_data = data.get(provider_id)
        if not isinstance(provider_data, dict):
            continue
        
        models_data = provider_data.get("models")
        if not isinstance(models_data, dict):
            continue
        
        # 解析模型
        models = []
        for model_id, model_data in models_data.items():
            model_info = _parse_model_info(model_id, model_data, provider_id)
            if model_info is None:
                continue
            
            # 过滤：只保留支持工具调用的模型
            if tool_calling_only and not model_info.tool_calling:
                continue
            
            models.append(model_info)
        
        # 只添加有模型的提供商
        if models:
            # 按名称排序
            models.sort(key=lambda m: m.name.lower())
            providers.append(ProviderInfo(
                id=provider_id,
                name=provider_name,
                base_url=base_url,
                models=models,
            ))
    
    # 按提供商名称排序
    providers.sort(key=lambda p: p.name.lower())
    
    logger.info(
        "提供商列表生成完成",
        provider_count=len(providers),
        total_models=sum(len(p.models) for p in providers),
        tool_calling_only=tool_calling_only,
    )
    
    return providers


def get_provider_models(
    provider_id: str,
    tool_calling_only: bool = True,
    api_url: str = MODELS_DEV_API_URL,
) -> list[ModelInfo]:
    """获取指定提供商的模型列表
    
    Args:
        provider_id: 提供商 ID
        tool_calling_only: 是否只返回支持工具调用的模型
        api_url: models.dev API URL
        
    Returns:
        模型列表
    """
    providers = get_providers(tool_calling_only=tool_calling_only, api_url=api_url)
    
    for provider in providers:
        if provider.id == provider_id:
            return provider.models
    
    return []


def get_provider_base_url(provider_id: str) -> str:
    """获取提供商的默认 Base URL"""
    config = PROVIDER_CONFIG.get(provider_id)
    if config:
        return config[1]
    return ""
