import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insert_with_tags_persists_to_doc_and_chunks(lightrag_instance):
    """
    Verify LightRAG.insert/ainsert(tags=...) persists TagMap to:
    - doc_status.metadata.tags
    - chunk-level tags in KV storage
    And that tags are propagated to all produced chunks.
    """
    rag = lightrag_instance

    # Prepare input with tags
    full_text = "alpha project content one two three"
    tags = {"project": "alpha", "region": ["us", "eu"]}

    # Initialize pipeline shared storage required by ainsert processing pipeline
    from lightrag.kg.shared_storage import initialize_share_data, initialize_pipeline_status

    initialize_share_data(1)
    await initialize_pipeline_status()

    track_id = await rag.ainsert(full_text, tags=tags)
    # Ensure background processing completed and indices flushed
    await rag._insert_done()

    # 1) DocStatus should contain metadata.tags
    # Retrieve documents by track_id to isolate this insert
    docs_by_track = await rag.doc_status.get_docs_by_track_id(track_id)
    assert isinstance(docs_by_track, dict) and len(docs_by_track) == 1
    doc_id, doc_status = next(iter(docs_by_track.items()))
    # DocProcessingStatus dataclass exposes metadata dict
    assert getattr(doc_status, "metadata", {}) .get("tags") == tags

    # 2) Each chunk in KV should carry the same tags
    # Doc status tracks chunks_list; use it to fetch chunk records
    chunk_ids = getattr(doc_status, "chunks_list", []) or []
    assert isinstance(chunk_ids, list) and len(chunk_ids) > 0
    chunk_records = await rag.text_chunks.get_by_ids(chunk_ids)
    assert len(chunk_records) == len(chunk_ids)
    for rec in chunk_records:
        assert isinstance(rec, dict)
        assert rec.get("tags") == tags

    # 3) Optional: chunks vector payload (NanoVectorDBStorage) does not support payload,
    # but this test ensures at least KV carries tags. Server-side filtering is covered elsewhere.


