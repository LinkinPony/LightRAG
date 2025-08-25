import pytest

from lightrag.base import QueryParam


@pytest.mark.unit
@pytest.mark.asyncio
async def test_naive_query_only_need_context_and_chunk_top_k(lightrag_instance):
    rag = lightrag_instance

    # Insert more chunks than chunk_top_k
    full_text = "A B C D E F"
    chunks = ["A", "B", "C", "D", "E", "F"]
    await rag.ainsert_custom_chunks(full_text=full_text, text_chunks=chunks)
    await rag._insert_done()

    # Only need context: expect JSON block with limited chunks
    qp = QueryParam(mode="naive", only_need_context=True, chunk_top_k=3)
    result = await rag.aquery("A", qp)

    assert isinstance(result, str)
    # Check that the Document Chunks section exists
    assert "---Document Chunks(DC)---" in result
    # The JSON block should include at most chunk_top_k entries
    # Count occurrences of \"id\": which correspond to entries in the list
    assert result.count('"id"') <= 3


