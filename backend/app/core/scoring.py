"""知识热度与时间衰减评分

参考 OpenViking memory_lifecycle.py 的热度评分机制。
通过访问频次 (active_count) 和时间衰减 (updated_at) 计算 0.0-1.0 的热度分数，
与语义相似度混合后进行重排，让高频使用、最近更新的知识排在前面。

公式:
    score = sigmoid(log1p(active_count)) * time_decay(updated_at)

    - sigmoid 将 log1p(active_count) 映射到 (0, 1)
    - time_decay 是指数衰减函数，半衰期可配置（默认 7 天）
"""

import math
from datetime import datetime, timezone

DEFAULT_HALF_LIFE_DAYS: float = 7.0


def hotness_score(
    active_count: int,
    updated_at: datetime | None,
    now: datetime | None = None,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> float:
    """计算 0.0-1.0 的知识热度分数。

    Args:
        active_count: 该知识被检索/使用的次数
        updated_at: 最后一次更新或访问的时间戳
        now: 当前时间（用于测试可注入）
        half_life_days: 时间衰减半衰期（天）

    Returns:
        [0.0, 1.0] 范围内的热度分数
    """
    if now is None:
        now = datetime.now(timezone.utc)

    freq = 1.0 / (1.0 + math.exp(-math.log1p(max(active_count, 0))))

    if updated_at is None:
        return 0.0

    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    age_days = max((now - updated_at).total_seconds() / 86400.0, 0.0)
    decay_rate = math.log(2) / half_life_days
    recency = math.exp(-decay_rate * age_days)

    return freq * recency


def blend_scores(
    semantic_score: float,
    active_count: int,
    updated_at: datetime | None,
    alpha: float = 0.2,
) -> float:
    """将语义相似度与热度分数混合。

    Args:
        semantic_score: 向量检索的语义相似度 [0, 1]
        active_count: 访问计数
        updated_at: 最后更新时间
        alpha: 热度权重 (0=纯语义, 1=纯热度)

    Returns:
        混合后的最终分数
    """
    h = hotness_score(active_count, updated_at)
    return (1.0 - alpha) * semantic_score + alpha * h
