import pytest

from lightrag.base import QueryParam
from lightrag.operate import _find_related_text_unit_from_entities


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_related_text_unit_from_entities_applies_tag_filters_direct(lightrag_instance, monkeypatch):
    rag = lightrag_instance

    # Build node_datas with source_id referencing chunk IDs
    # Prepare two chunks: one matching tags, one not
    await rag.ainsert_custom_chunks(
        full_text="doc1", text_chunks=["c1", "c2"], doc_id="doc-1"
    )
    await rag._insert_done()

    # Inject tags into KV for specific chunks
    # Retrieve created chunk ids deterministically by recomputing md5 ids like ainsert_custom_chunks does
    from lightrag.utils import compute_mdhash_id

    chunk1_id = compute_mdhash_id("c1", prefix="chunk-")
    chunk2_id = compute_mdhash_id("c2", prefix="chunk-")

    # Update KV entries to include tags
    await rag.text_chunks.upsert(
        {
            chunk1_id: {"tags": {"project": "alpha", "region": ["us"]}},
            chunk2_id: {"tags": {"project": "beta", "region": ["eu"]}},
        }
    )

    node_datas = [
        {
            "entity_name": "Alice",
            "source_id": f"{chunk1_id}",
        },
        {
            "entity_name": "Bob",
            "source_id": f"{chunk2_id}",
        },
    ]

    qp = QueryParam(mode="local", top_k=5, chunk_top_k=5)
    qp.tag_equals = {"project": "alpha"}  # type: ignore[attr-defined]
    qp.tag_in = {"region": ["us"]}  # type: ignore[attr-defined]

    # Invoke function under test
    chunks = await _find_related_text_unit_from_entities(
        node_datas=node_datas,
        query_param=qp,
        text_chunks_db=rag.text_chunks,
        knowledge_graph_inst=rag.chunk_entity_relation_graph,
        query="alpha",
        chunks_vdb=rag.chunks_vdb,
    )

    # Expect only chunk1 passes tag filters
    assert isinstance(chunks, list)
    assert all(c.get("chunk_id") == chunk1_id for c in chunks)


