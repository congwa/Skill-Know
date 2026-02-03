"""系统配置服务"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.system_config import SystemConfig

logger = get_logger("system_config_service")


class SystemConfigService:
    """系统配置服务"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, key: str) -> SystemConfig | None:
        """获取配置"""
        stmt = select(SystemConfig).where(SystemConfig.key == key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_value(self, key: str, default=None):
        """获取配置值"""
        config = await self.get(key)
        if config is None:
            return default
        return config.value

    async def set(
        self,
        key: str,
        value,
        description: str | None = None,
        group: str = "general",
        is_sensitive: bool = False,
    ) -> SystemConfig:
        """设置配置"""
        config = await self.get(key)
        if config:
            config.value = value
            if description is not None:
                config.description = description
        else:
            config = SystemConfig(
                key=key,
                value=value,
                description=description,
                group=group,
                is_sensitive=is_sensitive,
            )
            self._session.add(config)

        await self._session.flush()
        logger.info("设置配置", key=key)
        return config

    async def delete(self, key: str) -> bool:
        """删除配置"""
        config = await self.get(key)
        if not config:
            return False

        await self._session.delete(config)
        await self._session.flush()
        logger.info("删除配置", key=key)
        return True

    async def list_by_group(self, group: str) -> list[SystemConfig]:
        """按组列出配置"""
        stmt = select(SystemConfig).where(SystemConfig.group == group)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self, include_sensitive: bool = False) -> list[SystemConfig]:
        """列出所有配置"""
        stmt = select(SystemConfig)
        if not include_sensitive:
            stmt = stmt.where(SystemConfig.is_sensitive == False)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_llm_config(self) -> dict:
        """获取 LLM 配置"""
        return {
            "provider": await self.get_value("llm_provider", "openai"),
            "api_key": await self.get_value("llm_api_key", ""),
            "base_url": await self.get_value("llm_base_url", "https://api.openai.com/v1"),
            "chat_model": await self.get_value("llm_chat_model", "gpt-4o-mini"),
        }

    async def set_llm_config(
        self,
        provider: str,
        api_key: str,
        base_url: str,
        chat_model: str,
    ) -> None:
        """设置 LLM 配置"""
        await self.set("llm_provider", provider, "LLM 提供商", "llm")
        await self.set("llm_api_key", api_key, "LLM API Key", "llm", is_sensitive=True)
        await self.set("llm_base_url", base_url, "LLM Base URL", "llm")
        await self.set("llm_chat_model", chat_model, "LLM 聊天模型", "llm")
        logger.info("更新 LLM 配置", provider=provider, model=chat_model)

    async def is_setup_completed(self) -> bool:
        """检查是否完成初始设置"""
        api_key = await self.get_value("llm_api_key")
        return bool(api_key)
