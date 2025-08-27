import pytest

from lightrag.base import QueryParam
from lightrag.operate import _get_vector_context


@pytest.mark.unit
@pytest.mark.asyncio
async def test__get_vector_context_applies_tag_filters(lightrag_instance):
    """
    Phase 2 expectation:
    - QueryParam has tag_equals/tag_in
    - _get_vector_context filters returned vector chunks by tags client-side
    """
    rag = lightrag_instance

    # prepare chunks without tags (pre-implementation baseline)
    await rag.ainsert_custom_chunks("foo bar baz", ["foo", "bar", "baz"])
    await rag._insert_done()

    # Expectation after implementation: filter will reduce results to those matching tags
    qp = QueryParam(mode="naive", chunk_top_k=5)
    # Expect QueryParam to include tag filters fields
    qp.tag_equals = {"project": "alpha"}  # type: ignore[attr-defined]
    qp.tag_in = {"region": ["us"]}  # type: ignore[attr-defined]

    results = await _get_vector_context("foo", rag.chunks_vdb, qp)
    assert isinstance(results, list)
    # All results should satisfy the tag filters once implemented
    for r in results:
        tags = r.get("tags")
        assert tags is not None
        assert tags.get("project") == "alpha"
        assert isinstance(tags.get("region"), list) and "us" in tags.get("region")


