import pytest

from lightrag.base import DocStatus


@pytest.mark.unit
@pytest.mark.xfail(reason="Tag Plan C Phase 1 not implemented yet", strict=False)
@pytest.mark.asyncio
async def test_pipeline_enqueue_and_process_propagates_tags(lightrag_instance):
    """
    Phase 1 expectation:
    - apipeline_enqueue_documents accepts tags (dict[str, str | list[str]])
    - doc_status.metadata.tags == tags
    - after processing, all produced chunks in KV carry tags
      and chunks vector payload includes tags via meta_fields
    """
    rag = lightrag_instance

    texts = ["A quick brown fox."]
    tags = {"project": "alpha", "region": ["us", "eu"]}

    # The following should be supported after Phase 1 implementation
    track_id = await rag.apipeline_enqueue_documents(texts, file_paths=["a.txt"], track_id=None)  # noqa: E501
    assert isinstance(track_id, str)

    # Process
    from lightrag.kg.shared_storage import initialize_pipeline_status
    await initialize_pipeline_status()
    await rag.apipeline_process_enqueue_documents()

    # Find processed doc
    processed = await rag.doc_status.get_docs_by_status(DocStatus.PROCESSED)
    assert len(processed) >= 1
    doc_id, status = next(iter(processed.items()))

    # tags must be persisted on doc_status metadata
    # EXPECTED AFTER PHASE 1: status.metadata["tags"] == tags
    assert hasattr(status, "metadata")
    assert isinstance(status.metadata, dict)
    assert status.metadata.get("tags") == tags

    # For each chunk in KV and vector, tags must exist
    chunk_ids = status.chunks_list or []
    kv_chunks = await rag.text_chunks.get_by_ids(chunk_ids)
    for kv in kv_chunks:
        assert kv is not None and kv.get("tags") == tags

    # vdb payload should include "tags" due to meta_fields
    vdb_chunks = await rag.chunks_vdb.get_by_ids(chunk_ids)
    for c in vdb_chunks:
        assert c is not None and c.get("tags") == tags


