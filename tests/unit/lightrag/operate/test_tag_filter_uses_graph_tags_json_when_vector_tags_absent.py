import pytest

from lightrag.base import QueryParam
from lightrag.operate import _get_node_data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tag_filter_uses_graph_tags_json_when_vector_tags_absent(lightrag_instance, monkeypatch):
    rag = lightrag_instance

    # Monkeypatch entities_vdb.query to drop tags from vector payload
    async def fake_query(query, top_k, ids=None, **_kwargs):
        # Return entity results without 'tags'
        return [
            {
                "entity_name": "Alice",
                "created_at": 0.0,
            }
        ]

    monkeypatch.setattr(rag.entities_vdb, "query", fake_query)

    # Provide graph node with tags_json to be used as fallback
    async def fake_get_nodes_batch(node_ids):
        return {
            nid: {"tags_json": {"project": "alpha", "region": ["us"]}}
            for nid in node_ids
        }

    async def fake_node_degrees_batch(node_ids):
        return {nid: 1 for nid in node_ids}

    monkeypatch.setattr(rag.chunk_entity_relation_graph, "get_nodes_batch", fake_get_nodes_batch)
    monkeypatch.setattr(rag.chunk_entity_relation_graph, "node_degrees_batch", fake_node_degrees_batch)

    qp = QueryParam(mode="local", top_k=5)
    qp.tag_equals = {"project": "alpha"}  # type: ignore[attr-defined]
    qp.tag_in = {"region": ["us"]}  # type: ignore[attr-defined]

    nodes, rels = await _get_node_data(
        query="Alice",
        knowledge_graph_inst=rag.chunk_entity_relation_graph,
        entities_vdb=rag.entities_vdb,
        query_param=qp,
    )

    # Fallback from graph tags_json should allow the node to pass filter
    assert isinstance(nodes, list) and len(nodes) == 1
    assert isinstance(rels, list)


