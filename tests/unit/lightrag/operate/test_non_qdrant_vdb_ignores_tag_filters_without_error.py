import pytest

from lightrag.base import QueryParam
from lightrag.operate import _get_vector_context


@pytest.mark.unit
@pytest.mark.asyncio
async def test_non_qdrant_vdb_ignores_tag_filters_without_error(lightrag_instance, monkeypatch):
    rag = lightrag_instance

    # Insert chunks with tags via pipeline
    from lightrag.kg.shared_storage import initialize_share_data, initialize_pipeline_status
    initialize_share_data(1)
    await initialize_pipeline_status()
    await rag.ainsert("alpha beta", tags={"project": "alpha", "region": ["us"]})
    await rag._insert_done()

    # Monkeypatch chunks_vdb.query to simulate a backend that does not accept tag filters
    orig_query = rag.chunks_vdb.query

    async def fake_query(query, top_k, ids=None):  # signature without **kwargs
        return await orig_query(query, top_k=top_k, ids=ids)

    monkeypatch.setattr(rag.chunks_vdb, "query", fake_query)

    qp = QueryParam(mode="naive", chunk_top_k=5)
    qp.tag_equals = {"project": "alpha"}  # type: ignore[attr-defined]
    qp.tag_in = {"region": ["us"]}  # type: ignore[attr-defined]

    # Should not raise even if backend doesn't accept tag filters; client-side filtering applies
    results = await _get_vector_context("alpha", rag.chunks_vdb, qp, rag.text_chunks)
    assert isinstance(results, list)
    for r in results:
        tags = r.get("tags")
        assert tags is not None
        assert tags.get("project") == "alpha"
        assert "us" in (tags.get("region") or [])


