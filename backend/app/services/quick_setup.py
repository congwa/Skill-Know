"""快速设置服务"""

import time

from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.schemas.quick_setup import (
    QuickSetupState,
    SetupStep,
    SetupStepStatus,
    ChecklistItem,
    ChecklistItemStatus,
    ChecklistResponse,
    TestConnectionResponse,
)
from app.services.system_config import SystemConfigService

logger = get_logger("quick_setup_service")


# 设置步骤定义
SETUP_STEPS = [
    SetupStep(
        index=0,
        key="welcome",
        title="欢迎",
        description="欢迎使用 Skill-Know 知识库系统",
        is_required=False,
    ),
    SetupStep(
        index=1,
        key="llm",
        title="LLM 配置",
        description="配置语言模型 API",
        is_required=True,
    ),
    SetupStep(
        index=2,
        key="complete",
        title="完成",
        description="配置完成，开始使用",
        is_required=False,
    ),
]


class QuickSetupService:
    """快速设置服务"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._config_service = SystemConfigService(session)

    async def get_state(self) -> QuickSetupState:
        """获取设置状态"""
        is_completed = await self._config_service.is_setup_completed()

        steps = [step.model_copy() for step in SETUP_STEPS]

        if is_completed:
            for step in steps:
                step.status = SetupStepStatus.COMPLETED
            return QuickSetupState(
                current_step=len(steps) - 1,
                steps=steps,
                essential_completed=True,
                setup_level="essential",
            )

        return QuickSetupState(
            current_step=0,
            steps=steps,
            essential_completed=False,
            setup_level="none",
        )

    async def complete_essential_setup(
        self,
        llm_provider: str,
        llm_api_key: str,
        llm_base_url: str,
        llm_chat_model: str,
    ) -> QuickSetupState:
        """完成精简设置"""
        await self._config_service.set_llm_config(
            provider=llm_provider,
            api_key=llm_api_key,
            base_url=llm_base_url,
            chat_model=llm_chat_model,
        )
        logger.info("完成精简设置")
        return await self.get_state()

    async def test_connection(
        self,
        llm_provider: str,
        llm_api_key: str,
        llm_base_url: str,
        llm_chat_model: str,
    ) -> TestConnectionResponse:
        """测试 LLM 连接"""
        try:
            start_time = time.time()

            llm = ChatOpenAI(
                api_key=llm_api_key,
                base_url=llm_base_url,
                model=llm_chat_model,
                max_tokens=10,
            )

            # 简单测试
            response = await llm.ainvoke("Hi")
            latency_ms = int((time.time() - start_time) * 1000)

            return TestConnectionResponse(
                success=True,
                message="连接成功",
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.error("LLM 连接测试失败", error=str(e))
            return TestConnectionResponse(
                success=False,
                message=f"连接失败: {str(e)}",
            )

    async def get_checklist(self) -> ChecklistResponse:
        """获取配置检查清单"""
        items: list[ChecklistItem] = []

        llm_config = await self._config_service.get_llm_config()

        # LLM 配置检查
        items.append(
            ChecklistItem(
                key="llm_provider",
                label="LLM 提供商",
                category="llm",
                status=(
                    ChecklistItemStatus.OK
                    if llm_config["provider"]
                    else ChecklistItemStatus.DEFAULT
                ),
                current_value=llm_config["provider"],
                default_value="openai",
            )
        )

        items.append(
            ChecklistItem(
                key="llm_api_key",
                label="LLM API Key",
                category="llm",
                status=(
                    ChecklistItemStatus.OK
                    if llm_config["api_key"]
                    else ChecklistItemStatus.MISSING
                ),
                current_value="***" if llm_config["api_key"] else None,
                description="必须配置有效的 API Key",
            )
        )

        items.append(
            ChecklistItem(
                key="llm_base_url",
                label="LLM Base URL",
                category="llm",
                status=ChecklistItemStatus.OK,
                current_value=llm_config["base_url"],
            )
        )

        items.append(
            ChecklistItem(
                key="llm_chat_model",
                label="LLM 模型",
                category="llm",
                status=(
                    ChecklistItemStatus.OK
                    if llm_config["chat_model"]
                    else ChecklistItemStatus.MISSING
                ),
                current_value=llm_config["chat_model"],
            )
        )

        ok_count = sum(1 for item in items if item.status == ChecklistItemStatus.OK)
        default_count = sum(
            1 for item in items if item.status == ChecklistItemStatus.DEFAULT
        )
        missing_count = sum(
            1 for item in items if item.status == ChecklistItemStatus.MISSING
        )

        return ChecklistResponse(
            items=items,
            total=len(items),
            ok_count=ok_count,
            default_count=default_count,
            missing_count=missing_count,
        )

    async def reset(self) -> QuickSetupState:
        """重置设置"""
        await self._config_service.delete("llm_provider")
        await self._config_service.delete("llm_api_key")
        await self._config_service.delete("llm_base_url")
        await self._config_service.delete("llm_chat_model")
        logger.info("重置设置")
        return await self.get_state()
