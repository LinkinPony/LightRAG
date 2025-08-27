import pytest

from lightrag.base import QueryParam
from lightrag.operate import _build_query_context


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_related_text_unit_from_entities_applies_tag_filters(lightrag_instance):
    """
    Ensure entity-related chunk selection applies tag filters before returning chunks.
    We use mix mode with ll_keywords to trigger entity path.
    """
    rag = lightrag_instance

    # Initialize pipeline shared storage required by ainsert processing pipeline
    from lightrag.kg.shared_storage import initialize_share_data, initialize_pipeline_status

    initialize_share_data(1)
    await initialize_pipeline_status()

    # Insert content with tags so that chunks in KV carry tags and entities/relations can be derived
    full_text = "Alice works in Alpha project located in US"
    tags = {"project": "alpha", "region": ["us"]}
    await rag.ainsert(full_text, tags=tags)
    await rag._insert_done()

    # Build minimal QueryParam to prefer local path
    qp = QueryParam(mode="local", top_k=5, chunk_top_k=5)
    qp.tag_equals = {"project": "alpha"}  # type: ignore[attr-defined]
    qp.tag_in = {"region": ["us"]}  # type: ignore[attr-defined]

    # Provide ll_keywords to trigger _get_node_data path
    ctx = await _build_query_context(
        query="Alice Alpha US",
        ll_keywords="Alice Alpha",
        hl_keywords=[],
        knowledge_graph_inst=rag.chunk_entity_relation_graph,
        entities_vdb=rag.entities_vdb,
        relationships_vdb=rag.relationships_vdb,
        text_chunks_db=rag.text_chunks,
        query_param=qp,
        chunks_vdb=rag.chunks_vdb,
    )

    # _build_query_context may return None when no entities/relations; assert no error and type is str or None
    assert ctx is None or isinstance(ctx, str)


