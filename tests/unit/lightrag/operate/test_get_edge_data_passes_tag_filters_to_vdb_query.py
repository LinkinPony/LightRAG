import pytest

from lightrag.base import QueryParam
from lightrag.operate import _get_edge_data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_edge_data_passes_tag_filters_to_vdb_query(lightrag_instance, monkeypatch):
    rag = lightrag_instance

    captured_kwargs = {}

    async def fake_relationships_query(query, top_k, ids=None, **kwargs):
        captured_kwargs.update(kwargs)
        # Return a minimal fake vector result for relationships
        return [
            {
                "src_id": "Alice",
                "tgt_id": "Bob",
                "tags": {"project": "alpha", "region": ["us"]},
                "created_at": 0.0,
            }
        ]

    # Patch relationships_vdb.query to accept and capture tag filters
    monkeypatch.setattr(rag.relationships_vdb, "query", fake_relationships_query)

    # Patch KG edges batch used by _get_edge_data
    async def fake_get_edges_batch(edge_pairs_dicts):
        # Map (src, tgt) to properties
        return {
            (d["src"], d["tgt"]): {"weight": 1.0, "tags_json": {"project": "alpha", "region": ["us"]}}
            for d in edge_pairs_dicts
        }

    monkeypatch.setattr(
        rag.chunk_entity_relation_graph, "get_edges_batch", fake_get_edges_batch
    )

    qp = QueryParam(mode="global", top_k=3)
    qp.tag_equals = {"project": "alpha"}  # type: ignore[attr-defined]
    qp.tag_in = {"region": ["us"]}  # type: ignore[attr-defined]

    edges, entities = await _get_edge_data(
        keywords="Alice Bob",
        knowledge_graph_inst=rag.chunk_entity_relation_graph,
        relationships_vdb=rag.relationships_vdb,
        query_param=qp,
    )

    # Ensure passthrough kwargs were provided to vector query
    assert captured_kwargs.get("tag_equals") == qp.tag_equals
    assert captured_kwargs.get("tag_in") == qp.tag_in

    # Function should return tuple of lists without raising
    assert isinstance(edges, list)
    assert isinstance(entities, list)


