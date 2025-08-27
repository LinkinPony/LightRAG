import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vector_query_returns_expected_fields(lightrag_instance):
    rag = lightrag_instance

    full_text = "one two three"
    chunks = ["one", "two", "three"]
    await rag.ainsert_custom_chunks(full_text=full_text, text_chunks=chunks)
    await rag._insert_done()

    results = await rag.chunks_vdb.query("one", top_k=5)
    assert isinstance(results, list)
    if results:
        sample = results[0]
        # id, distance, created_at are added by vector layer
        assert "id" in sample
        assert "distance" in sample
        assert "created_at" in sample
        # meta_fields propagated
        assert "content" in sample
        assert "file_path" in sample
        assert "full_doc_id" in sample


