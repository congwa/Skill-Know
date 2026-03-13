"""scoring.py 单元测试

测试热度评分和分数混合逻辑。
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.scoring import blend_scores, hotness_score


class TestHotnessScore:
    """hotness_score 函数测试"""

    def test_zero_activity_returns_low_score(self):
        """无活跃度应返回较低分数"""
        now = datetime.now(timezone.utc)
        score = hotness_score(active_count=0, updated_at=now, now=now)
        assert 0.0 < score < 0.6

    def test_high_activity_returns_higher_score(self):
        """高活跃度应返回更高分数"""
        now = datetime.now(timezone.utc)
        low = hotness_score(active_count=1, updated_at=now, now=now)
        high = hotness_score(active_count=100, updated_at=now, now=now)
        assert high > low

    def test_recent_update_scores_higher_than_old(self):
        """最近更新的知识应比旧知识分数更高"""
        now = datetime.now(timezone.utc)
        recent = hotness_score(active_count=5, updated_at=now, now=now)
        old = hotness_score(
            active_count=5,
            updated_at=now - timedelta(days=30),
            now=now,
        )
        assert recent > old

    def test_none_updated_at_returns_zero(self):
        """updated_at 为 None 时返回 0"""
        score = hotness_score(active_count=10, updated_at=None)
        assert score == 0.0

    def test_score_in_range(self):
        """分数应在 [0, 1] 范围内"""
        now = datetime.now(timezone.utc)
        for count in [0, 1, 10, 100, 10000]:
            for days_ago in [0, 1, 7, 30, 365]:
                score = hotness_score(
                    active_count=count,
                    updated_at=now - timedelta(days=days_ago),
                    now=now,
                )
                assert 0.0 <= score <= 1.0, f"score {score} out of range for count={count}, days={days_ago}"

    def test_half_life_decay(self):
        """验证半衰期衰减：7 天前的分数约为当前的一半"""
        now = datetime.now(timezone.utc)
        current = hotness_score(active_count=10, updated_at=now, now=now)
        half_life = hotness_score(
            active_count=10,
            updated_at=now - timedelta(days=7),
            now=now,
            half_life_days=7.0,
        )
        ratio = half_life / current if current > 0 else 0
        assert 0.45 <= ratio <= 0.55, f"half-life ratio {ratio} not ~0.5"

    def test_naive_datetime_handled(self):
        """无时区的 datetime 应被正确处理"""
        now = datetime(2026, 1, 1, 12, 0, 0)
        score = hotness_score(active_count=5, updated_at=now, now=now)
        assert 0.0 < score <= 1.0


class TestBlendScores:
    """blend_scores 函数测试"""

    def test_alpha_zero_returns_semantic_score(self):
        """alpha=0 时应返回纯语义分数"""
        now = datetime.now(timezone.utc)
        result = blend_scores(
            semantic_score=0.85,
            active_count=100,
            updated_at=now,
            alpha=0.0,
        )
        assert result == pytest.approx(0.85)

    def test_alpha_one_returns_hotness_score(self):
        """alpha=1 时应返回纯热度分数"""
        now = datetime.now(timezone.utc)
        h = hotness_score(active_count=10, updated_at=now, now=now)
        result = blend_scores(
            semantic_score=0.85,
            active_count=10,
            updated_at=now,
            alpha=1.0,
        )
        assert result == pytest.approx(h, abs=0.01)

    def test_default_alpha_mixes_both(self):
        """默认 alpha 应混合两种分数"""
        now = datetime.now(timezone.utc)
        result = blend_scores(
            semantic_score=0.8,
            active_count=50,
            updated_at=now,
        )
        assert 0.0 < result < 1.0
        assert result != 0.8
