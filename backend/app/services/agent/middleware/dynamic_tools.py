"""状态驱动的动态工具注入中间件

根据当前阶段（Phase）动态注入不同的工具：
- INIT → INTENT_ANALYSIS: 注入 extract_keywords 工具，使用 llm 提取关键词
- INTENT_ANALYSIS → SKILL_RETRIEVAL: 注入 search_skills 工具 ,执行 sql 语句查询相关的 skill，之前步骤的工具都不需要注入
- TOOL_PREPARATION → EXECUTION: 注入检索到的 Skill 工具，之前步骤的工具都不需要具都不需要注入
- EXECUTION: Agent 自主决策调用工具

学习 TodoListMiddleware 的状态管理模式实现。
"""

from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, Literal

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
    OmitFromInput,
    ToolCallRequest,
)
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.runtime import Runtime
from typing_extensions import NotRequired

from app.core.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger("middleware.dynamic_tools")


class SkillPhase(str, Enum):
    """技能搜索阶段"""
    INIT = "init"
    INTENT_ANALYSIS = "intent_analysis"
    SKILL_RETRIEVAL = "skill_retrieval"
    TOOL_PREPARATION = "tool_preparation"
    EXECUTION = "execution"


class SkillSearchState(AgentState[Any]):
    """技能搜索状态 schema"""
    
    phase: Annotated[NotRequired[Literal[
        "init", "intent_analysis", "skill_retrieval", "tool_preparation", "execution"
    ]], OmitFromInput]
    """当前阶段"""
    
    keywords: Annotated[NotRequired[list[str]], OmitFromInput]
    """提取的关键词"""
    
    skill_ids: Annotated[NotRequired[list[str]], OmitFromInput]
    """检索到的技能 ID"""


class StatefulToolMiddleware(AgentMiddleware):
    """状态驱动的动态工具注入中间件
    
    根据 state.phase 状态动态注入不同工具。
    """
    
    state_schema = SkillSearchState
    
    def __init__(
        self,
        session: "AsyncSession | None" = None,
        emitter: Any = None,
        llm: Any = None,
    ):
        super().__init__()
        self._session = session
        self._emitter = emitter
        self._llm = llm
        
        # 动态工具缓存
        self._phase_tools: dict[SkillPhase, list[BaseTool]] = {}
        self._skill_tools: dict[str, BaseTool] = {}  # 从 Skill 创建的工具
        
        # 注册所有工具（让 ToolNode 能够找到它们）
        from app.services.agent.tools.skill import (
            extract_keywords,
            get_skill_content,
            search_skills,
        )
        self.tools: list[BaseTool] = [
            extract_keywords,
            search_skills,
            get_skill_content,
        ]
        logger.info(f"✓ StatefulToolMiddleware 注册工具: {[t.name for t in self.tools]}")
        
    def _get_current_phase(self, state: AgentState) -> SkillPhase:
        """从状态获取当前阶段"""
        phase_str = state.get("phase", "init")
        try:
            return SkillPhase(phase_str)
        except ValueError:
            return SkillPhase.INIT
    
    async def _get_phase_tools(self, phase: SkillPhase) -> list[BaseTool]:
        """根据阶段获取工具列表
        
        使用 @tool 装饰器定义的工具，通过 ToolRuntime 访问上下文。
        """
        if phase in self._phase_tools:
            return self._phase_tools[phase]
            
        tools: list[BaseTool] = []
        
        logger.info(f"📦 获取阶段工具: {phase.value}")
        
        if phase == SkillPhase.INIT or phase == SkillPhase.INTENT_ANALYSIS:
            # 阶段 1: 意图分析 - 注入关键词提取工具
            try:
                from app.services.agent.tools.skill import extract_keywords
                tools.append(extract_keywords)
                logger.info("✓ 注入 extract_keywords 工具")
            except Exception as e:
                logger.warning(f"注入 extract_keywords 工具失败: {e}")
                
        elif phase == SkillPhase.SKILL_RETRIEVAL:
            # 阶段 2: 技能检索 - 注入搜索工具
            try:
                from app.services.agent.tools.skill import search_skills
                tools.append(search_skills)
                logger.info("✓ 注入 search_skills 工具")
            except Exception as e:
                logger.warning(f"注入 search_skills 工具失败: {e}")
                
        elif phase == SkillPhase.TOOL_PREPARATION:
            # 阶段 3: 工具准备 - 注入获取内容工具
            try:
                from app.services.agent.tools.skill import get_skill_content
                tools.append(get_skill_content)
                logger.info("✓ 注入 get_skill_content 工具")
            except Exception as e:
                logger.warning(f"注入 get_skill_content 工具失败: {e}")
                
        elif phase == SkillPhase.EXECUTION:
            # 阶段 4: 执行 - 注入从 Skill 创建的工具
            tools.extend(list(self._skill_tools.values()))
            if self._skill_tools:
                logger.info(f"✓ 注入 {len(self._skill_tools)} 个 Skill 工具")
        
        self._phase_tools[phase] = tools
        return tools

    def _register_skill_from_result(self, result_content: str) -> None:
        """Parse get_skill_content result and register skill as an available context tool"""
        try:
            import json

            from langchain_core.tools import StructuredTool

            data = json.loads(result_content)
            skill_id = data.get("skill_id")
            skill_name = data.get("name", "unknown")
            content = data.get("content", "")
            if skill_id and skill_id not in self._skill_tools:
                tool_name = f"skill_{skill_id}"
                content_capture = content

                async def _return_content(**kwargs: Any) -> str:
                    return content_capture

                tool = StructuredTool.from_function(
                    coroutine=_return_content,
                    name=tool_name,
                    description=f"已加载的技能内容: {skill_name}。调用此工具可获取完整技能内容用于执行任务。",
                )
                self._skill_tools[skill_id] = tool
                logger.info(f"注册 Skill 工具: {skill_name} ({skill_id})")
                # Clear EXECUTION phase cache so new tools get picked up
                self._phase_tools.pop(SkillPhase.EXECUTION, None)
        except Exception as e:
            logger.warning(f"注册 Skill 工具失败: {e}")

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """在模型调用前根据阶段动态添加工具"""
        # 获取当前阶段
        state = request.state
        current_phase = self._get_current_phase(state)
        
        # 获取当前阶段的工具
        phase_tools = await self._get_phase_tools(current_phase)
        
        # 记录当前状态
        current_tools = [t.name for t in request.tools]
        logger.info(
            "📋 wrap_model_call",
            phase=current_phase.value,
            base_tools=current_tools,
            phase_tools=[t.name for t in phase_tools],
        )
        
        # 添加阶段工具到请求
        if phase_tools:
            updated_tools = [*request.tools, *phase_tools]
            updated_request = request.override(tools=updated_tools)
            
            logger.info(
                "➕ 动态注入工具",
                phase=current_phase.value,
                injected=[t.name for t in phase_tools],
                total=len(updated_tools),
            )
            
            return await handler(updated_request)
        
        return await handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage]],
    ) -> ToolMessage:
        """处理工具调用，记录执行信息
        
        工具已经通过 awrap_model_call 注入到模型请求中，
        这里只需要记录日志和处理结果。
        """
        tool_name = request.tool_call.get("name")
        tool_args = request.tool_call.get("args", {})
        
        # 记录工具调用信息
        logger.info(f"🔧 开始执行工具: {tool_name}")
        logger.info(f"│  参数: {tool_args}")
        
        # 执行工具
        result = await handler(request)
        result_content = result.content if hasattr(result, "content") else str(result)

        # After get_skill_content succeeds, register the skill as a context tool for EXECUTION phase
        if tool_name == "get_skill_content" and "error" not in result_content.lower():
            self._register_skill_from_result(result_content)

        # 记录工具结果
        logger.info(f"│  结果: {result_content[:200]}..." if len(str(result_content)) > 200 else f"│  结果: {result_content}")
        logger.info(f"└── 工具 {tool_name} 执行完成")
        
        return result

    async def aafter_model(
        self, state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:
        """模型调用后更新阶段状态"""
        messages = state.get("messages", [])
        if not messages:
            return None
            
        last_ai_msg = next(
            (msg for msg in reversed(messages) if isinstance(msg, AIMessage)),
            None
        )
        if not last_ai_msg or not last_ai_msg.tool_calls:
            return None
            
        current_phase = self._get_current_phase(state)
        
        # 根据工具调用更新阶段
        for tc in last_ai_msg.tool_calls:
            tool_name = tc.get("name")
            
            if tool_name == "extract_keywords" and current_phase == SkillPhase.INIT:
                logger.info("🔄 阶段转换: INIT → SKILL_RETRIEVAL")
                return {"phase": SkillPhase.SKILL_RETRIEVAL.value}
                
            elif tool_name == "search_skills" and current_phase == SkillPhase.SKILL_RETRIEVAL:
                logger.info("🔄 阶段转换: SKILL_RETRIEVAL → TOOL_PREPARATION")
                return {"phase": SkillPhase.TOOL_PREPARATION.value}
                
            elif tool_name == "get_skill_content" and current_phase == SkillPhase.TOOL_PREPARATION:
                logger.info("🔄 阶段转换: TOOL_PREPARATION → EXECUTION")
                return {"phase": SkillPhase.EXECUTION.value}
        
        return None
