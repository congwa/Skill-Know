"""Prompt 模板注册表

参考 OpenViking prompts/manager.py，提供 YAML + Jinja2 的 Prompt 模板管理。
通过 render_prompt("category.name", vars) 渲染模板。
"""

from app.prompts.manager import PromptManager, render_prompt

__all__ = ["PromptManager", "render_prompt"]
