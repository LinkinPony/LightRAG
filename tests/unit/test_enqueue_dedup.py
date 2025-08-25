import pytest

from lightrag.base import DocStatus


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enqueue_generates_ids_and_stores_status(lightrag_instance):
    rag = lightrag_instance
    texts = ["Hello", "Hello", "World"]

    track_id = await rag.apipeline_enqueue_documents(texts)
    assert isinstance(track_id, str)

    pending = await rag.doc_status.get_docs_by_status(DocStatus.PENDING)
    # Current behavior: all inputs enqueued (no content dedup in status)
    assert len(pending) == 3

    # Each pending doc has file_path and track_id set
    for status in pending.values():
        assert status.status == DocStatus.PENDING
        assert isinstance(status.file_path, str)
        assert isinstance(status.track_id, str)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enqueue_validation_error_on_mismatched_file_paths(lightrag_instance):
    rag = lightrag_instance
    with pytest.raises(ValueError):
        await rag.apipeline_enqueue_documents(["A", "B"], file_paths=["only_one"])


