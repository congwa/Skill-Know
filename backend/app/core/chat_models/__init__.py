"""Chat Models 统一入口 - v1 版本

基于 LangChain v1 输出格式，使用 content_blocks 标准化消息内容。
现已统一使用 langgraph-agent-kit SDK 提供的 chat_models 模块。

使用方式：
```python
from app.core.chat_models import V1ChatModel, parse_content_blocks

# 创建模型（强制 v1 输出）
model = V1ChatModel(
    model="...",
    openai_api_base="...",
    openai_api_key="...",
)

# 解析消息内容（v1 方式）
parsed = parse_content_blocks(message)
print(parsed.text)       # 合并后的文本
print(parsed.reasoning)  # 合并后的推理
```
"""

from langgraph_agent_kit import (
    V1ChatModel,
    is_v1_model,
    ParsedContent,
    parse_content_blocks,
    parse_content_blocks_from_chunk,
    ContentBlock,
    TextContentBlock,
    ReasoningContentBlock,
    ToolCallBlock,
    ToolCallChunk,
    InvalidToolCall,
    ImageContentBlock,
    is_text_block,
    is_reasoning_block,
    is_tool_call_block,
    is_tool_call_chunk_block,
    is_image_block,
    get_block_type,
    create_chat_model,
    SiliconFlowV1ChatModel,
)

__all__ = [
    # v1 模型
    "V1ChatModel",
    "SiliconFlowV1ChatModel",
    "create_chat_model",
    # v1 解析器
    "ParsedContent",
    "parse_content_blocks",
    "parse_content_blocks_from_chunk",
    # v1 类型守卫
    "is_text_block",
    "is_reasoning_block",
    "is_tool_call_block",
    "is_tool_call_chunk_block",
    "is_image_block",
    "get_block_type",
    # 版本检测
    "is_v1_model",
    # v1 类型
    "ContentBlock",
    "TextContentBlock",
    "ReasoningContentBlock",
    "ToolCallBlock",
    "ToolCallChunk",
    "InvalidToolCall",
    "ImageContentBlock",
]
