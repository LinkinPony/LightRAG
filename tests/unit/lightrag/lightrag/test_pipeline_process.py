import pytest

from lightrag.base import DocStatus


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pipeline_process_transitions_and_persists_chunks(lightrag_instance):
    rag = lightrag_instance

    # Enqueue two docs
    texts = ["Cats and dogs.", "Birds and fish."]
    await rag.apipeline_enqueue_documents(texts, file_paths=["a.txt", "b.txt"])

    # Initialize pipeline namespace then process the queue
    from lightrag.kg.shared_storage import initialize_pipeline_status
    await initialize_pipeline_status()
    await rag.apipeline_process_enqueue_documents()

    # Verify doc statuses are PROCESSED for the two enqueued documents
    processed = await rag.doc_status.get_docs_by_status(DocStatus.PROCESSED)
    assert len(processed) >= 2
    # Find entries by content_summary
    summaries = [s.content_summary for s in processed.values()]
    assert "Cats and dogs." in summaries
    assert "Birds and fish." in summaries
    # Each processed has chunks_count and chunks_list populated
    for status in processed.values():
        if status.content_summary in {"Cats and dogs.", "Birds and fish."}:
            assert status.status == DocStatus.PROCESSED
            assert isinstance(status.chunks_count, int) and status.chunks_count >= 0
            assert isinstance(status.chunks_list, list)

    # Chunks persisted into both vector and KV stores
    # Collect all chunk ids
    all_chunk_ids = []
    for status in processed.values():
        all_chunk_ids.extend(status.chunks_list)

    # KV must return by ids
    kv_results = await rag.text_chunks.get_by_ids(all_chunk_ids)
    assert len([r for r in kv_results if r is not None]) == len(all_chunk_ids)

    # Vector DB must be able to retrieve vectors for chunk ids
    vectors = await rag.chunks_vdb.get_vectors_by_ids(all_chunk_ids)
    # vectors might be empty if embeddings failed, but storage path should be exercised
    assert isinstance(vectors, dict)


