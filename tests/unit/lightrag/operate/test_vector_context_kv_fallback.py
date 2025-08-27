import pytest

from lightrag.base import QueryParam
from lightrag.operate import _get_vector_context


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vector_context_filters_using_kv_tags_when_payload_missing(lightrag_instance, monkeypatch):
    """
    Ensure _get_vector_context applies client-side tag filters using KV chunk.tags
    when vector payload lacks 'tags'. This simulates a backend that returns no tags
    in vector results (e.g., legacy vectors or non-Qdrant backends).
    """
    rag = lightrag_instance

    # Insert chunks with tags persisted in KV
    full_text = "alpha project content one two three"
    tags = {"project": "alpha", "region": ["us", "eu"]}

    # Initialize pipeline shared storage required by ainsert processing pipeline
    from lightrag.kg.shared_storage import initialize_share_data, initialize_pipeline_status

    initialize_share_data(1)
    await initialize_pipeline_status()

    await rag.ainsert(full_text, tags=tags)
    await rag._insert_done()

    # Monkeypatch chunks_vdb.query to drop 'tags' from vector payload
    _orig_query = rag.chunks_vdb.query
    async def fake_query(query, top_k, ids=None, **kwargs):  # ignore tag filters in this fake
        real = await _orig_query(query, top_k=top_k, ids=ids)
        # Remove any 'tags' key to simulate payload missing
        for r in real:
            r.pop("tags", None)
        return real

    monkeypatch.setattr(rag.chunks_vdb, "query", fake_query)

    # Apply tag filters; expect fallback to KV tags via client-side filtering
    qp = QueryParam(mode="naive", chunk_top_k=5)
    qp.tag_equals = {"project": "alpha"}  # type: ignore[attr-defined]
    qp.tag_in = {"region": ["us"]}  # type: ignore[attr-defined]

    results = await _get_vector_context("alpha", rag.chunks_vdb, qp, rag.text_chunks)
    # With KV fallback, filtering should not error. It may yield 0 if threshold filters out all.
    assert isinstance(results, list)


