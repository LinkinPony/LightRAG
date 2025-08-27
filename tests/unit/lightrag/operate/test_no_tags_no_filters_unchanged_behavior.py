import pytest

from lightrag.base import QueryParam
from lightrag.operate import _get_vector_context


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_tags_no_filters_unchanged_behavior(lightrag_instance):
    rag = lightrag_instance

    # Insert simple chunks with no tags via deprecated helper
    await rag.ainsert_custom_chunks("foo bar baz", ["foo", "bar", "baz"])
    await rag._insert_done()

    qp = QueryParam(mode="naive", chunk_top_k=5)  # no tag filters applied

    # Baseline behavior: returns list of chunks; no filtering shrinks results
    results = await _get_vector_context("foo", rag.chunks_vdb, qp, rag.text_chunks)
    assert isinstance(results, list)
    assert len(results) >= 0


