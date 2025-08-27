import pytest

from lightrag.base import QueryParam
from lightrag.operate import _get_node_data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_node_data_passes_tag_filters_to_vdb_query(lightrag_instance, monkeypatch):
    rag = lightrag_instance

    captured_kwargs = {}

    async def fake_entities_query(query, top_k, ids=None, **kwargs):
        captured_kwargs.update(kwargs)
        # Return a minimal fake vector result for entities
        return [
            {
                "entity_name": "Alice",
                "tags": {"project": "alpha", "region": ["us"]},
                "created_at": 0.0,
            }
        ]

    # Patch entities_vdb.query to accept and capture tag filters
    monkeypatch.setattr(rag.entities_vdb, "query", fake_entities_query)

    # Patch KG batch methods used by _get_node_data
    async def fake_get_nodes_batch(node_ids):
        return {
            nid: {"name": nid, "tags_json": {"project": "alpha", "region": ["us"]}}
            for nid in node_ids
        }

    async def fake_node_degrees_batch(node_ids):
        return {nid: 1 for nid in node_ids}

    monkeypatch.setattr(
        rag.chunk_entity_relation_graph, "get_nodes_batch", fake_get_nodes_batch
    )
    monkeypatch.setattr(
        rag.chunk_entity_relation_graph, "node_degrees_batch", fake_node_degrees_batch
    )

    qp = QueryParam(mode="local", top_k=3)
    qp.tag_equals = {"project": "alpha"}  # type: ignore[attr-defined]
    qp.tag_in = {"region": ["us"]}  # type: ignore[attr-defined]

    nodes, relations = await _get_node_data(
        query="Alice",
        knowledge_graph_inst=rag.chunk_entity_relation_graph,
        entities_vdb=rag.entities_vdb,
        query_param=qp,
    )

    # Ensure passthrough kwargs were provided to vector query
    assert captured_kwargs.get("tag_equals") == qp.tag_equals
    assert captured_kwargs.get("tag_in") == qp.tag_in

    # Function should return tuple of lists without raising
    assert isinstance(nodes, list)
    assert isinstance(relations, list)


