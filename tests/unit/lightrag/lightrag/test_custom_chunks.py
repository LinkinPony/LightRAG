import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insert_custom_chunks_and_vector_query(lightrag_instance):
    rag = lightrag_instance

    full_text = "Alpha Beta Gamma"
    chunks = ["Alpha", "Beta", "Gamma"]

    await rag.ainsert_custom_chunks(full_text=full_text, text_chunks=chunks)

    # Persist storages
    await rag._insert_done()

    # Query chunks_vdb directly to ensure meta_fields propagated
    # Using a term from one chunk should retrieve payloads that include content and file_path
    results = await rag.chunks_vdb.query("Alpha", top_k=5)
    assert isinstance(results, list)
    assert any("content" in r for r in results)
    # Ensure only expected fields exist from meta_fields and created_at
    sample = results[0]
    assert "content" in sample
    assert "file_path" in sample
    assert "full_doc_id" in sample


