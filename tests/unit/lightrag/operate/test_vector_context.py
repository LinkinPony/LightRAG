import pytest

from lightrag.base import QueryParam
from lightrag.operate import _get_vector_context


@pytest.mark.unit
@pytest.mark.asyncio
async def test__get_vector_context_result_shape(lightrag_instance):
    rag = lightrag_instance

    # Prepare a few chunks
    full_text = "The quick brown fox jumps over the lazy dog"
    chunks = ["quick brown fox", "lazy dog", "over the moon"]
    await rag.ainsert_custom_chunks(full_text=full_text, text_chunks=chunks)
    await rag._insert_done()

    qp = QueryParam(mode="naive", chunk_top_k=2)
    results = await _get_vector_context("quick", rag.chunks_vdb, qp)

    # Should return a list of dicts with required keys
    assert isinstance(results, list)
    assert len(results) > 0
    sample = results[0]
    assert set(["content", "file_path", "source_type", "chunk_id"]).issubset(sample.keys())


