"""Prompt 模板管理器

参考 OpenViking prompts/manager.py，使用 YAML 文件管理 Prompt 模板。
支持 Jinja2 模板渲染和变量替换。
"""

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Template

from app.core.logging import get_logger

logger = get_logger("prompt_manager")

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_CACHE: dict[str, dict[str, Any]] = {}
_JINJA_CACHE: dict[str, Template] = {}


def _load_template(prompt_id: str) -> dict[str, Any] | None:
    """加载 YAML 模板文件。

    prompt_id 格式: "category.name" -> templates/category/name.yaml
    """
    if prompt_id in _CACHE:
        return _CACHE[prompt_id]

    parts = prompt_id.split(".", 1)
    if len(parts) != 2:
        logger.warning(f"无效的 prompt_id 格式: {prompt_id}")
        return None

    category, name = parts
    yaml_path = _TEMPLATES_DIR / category / f"{name}.yaml"

    if not yaml_path.exists():
        logger.debug(f"模板文件不存在: {yaml_path}")
        return None

    try:
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        _CACHE[prompt_id] = data
        return data
    except Exception as e:
        logger.warning(f"加载模板失败: {yaml_path}, {e}")
        return None


def render_prompt(prompt_id: str, variables: dict[str, Any] | None = None) -> str:
    """渲染 Prompt 模板。

    Args:
        prompt_id: 模板 ID，格式为 "category.name"
        variables: 模板变量

    Returns:
        渲染后的 prompt 文本
    """
    template_data = _load_template(prompt_id)
    if not template_data:
        return ""

    template_str = template_data.get("template", "")
    if not template_str:
        return ""

    variables = variables or {}

    # 填充默认值
    for var_def in template_data.get("variables", []):
        var_name = var_def.get("name", "")
        if var_name and var_name not in variables and "default" in var_def:
            variables[var_name] = var_def["default"]

    try:
        if prompt_id not in _JINJA_CACHE:
            _JINJA_CACHE[prompt_id] = Template(template_str)
        template = _JINJA_CACHE[prompt_id]
        return template.render(**variables)
    except Exception as e:
        logger.warning(f"渲染模板失败: {prompt_id}, {e}")
        return template_str.format(**variables) if variables else template_str


def clear_cache() -> None:
    """清空所有缓存（模板更新后调用）"""
    _CACHE.clear()
    _JINJA_CACHE.clear()


def list_templates() -> list[str]:
    """列出所有可用模板 ID"""
    result = []
    if not _TEMPLATES_DIR.exists():
        return result

    for category_dir in sorted(_TEMPLATES_DIR.iterdir()):
        if not category_dir.is_dir() or category_dir.name.startswith("_"):
            continue
        for yaml_file in sorted(category_dir.glob("*.yaml")):
            result.append(f"{category_dir.name}.{yaml_file.stem}")

    return result


class PromptManager:
    """Prompt 管理器（兼容 class 风格调用）"""

    @staticmethod
    def render(prompt_id: str, variables: dict[str, Any] | None = None) -> str:
        return render_prompt(prompt_id, variables)

    @staticmethod
    def list_all() -> list[str]:
        return list_templates()

    @staticmethod
    def clear_cache() -> None:
        clear_cache()
