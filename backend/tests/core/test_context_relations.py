"""context_relation 模型和 Context.relations 测试"""

from app.core.context import Context


class TestContextRelations:
    """Context 对象的 relations 属性测试"""

    def test_default_relations_empty(self):
        ctx = Context(uri="sk://skills/test")
        assert ctx.relations == []

    def test_relations_from_init(self):
        relations = [
            {"target_uri": "sk://documents/doc1", "relation_type": "derived_from", "reason": "test"}
        ]
        ctx = Context(uri="sk://skills/test", relations=relations)
        assert len(ctx.relations) == 1
        assert ctx.relations[0]["relation_type"] == "derived_from"

    def test_relations_in_to_dict(self):
        relations = [{"target_uri": "sk://documents/d1", "relation_type": "derived_from", "reason": ""}]
        ctx = Context(uri="sk://skills/test", relations=relations)
        d = ctx.to_dict()
        assert "relations" in d
        assert d["relations"] == relations

    def test_relations_from_dict(self):
        data = {
            "uri": "sk://skills/test",
            "relations": [
                {"target_uri": "sk://documents/d1", "relation_type": "derived_from", "reason": "origin"}
            ],
        }
        ctx = Context.from_dict(data)
        assert len(ctx.relations) == 1
        assert ctx.relations[0]["target_uri"] == "sk://documents/d1"

    def test_from_dict_without_relations(self):
        data = {"uri": "sk://skills/test"}
        ctx = Context.from_dict(data)
        assert ctx.relations == []
