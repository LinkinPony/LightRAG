import pytest

from lightrag.base import QueryParam
from lightrag.operate import _get_vector_context


@pytest.mark.unit
@pytest.mark.asyncio
async def test_untagged_items_excluded_when_filters_present(lightrag_instance):
    rag = lightrag_instance

    # Insert one tagged via full pipeline and one untagged via deprecated helper
    from lightrag.kg.shared_storage import initialize_share_data, initialize_pipeline_status
    initialize_share_data(1)
    await initialize_pipeline_status()

    await rag.ainsert("alpha content", tags={"project": "alpha"})
    await rag._insert_done()

    await rag.ainsert_custom_chunks("untagged", ["untagged one"])
    await rag._insert_done()

    qp = QueryParam(mode="naive", chunk_top_k=10)
    qp.tag_equals = {"project": "alpha"}  # type: ignore[attr-defined]

    results = await _get_vector_context("content", rag.chunks_vdb, qp, rag.text_chunks)
    # All returned chunks must have tags.project == 'alpha'
    for r in results:
        tags = r.get("tags")
        assert isinstance(tags, dict)
        assert tags.get("project") == "alpha"


