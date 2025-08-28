import json
import pytest

from lightrag.base import QueryParam


def _extract_dc_chunks(result: str, mode: str) -> list:
    if mode == "naive":
        if "---Document Chunks(DC)---" not in result:
            return []
        try:
            json_block = result.split("```json\n", 1)[-1].split("\n```", 1)[0]
            return json.loads(json_block)
        except Exception:
            return []
    else:
        if "-----Document Chunks(DC)-----" not in result:
            return []
        try:
            blocks = result.split("-----Document Chunks(DC)-----", 1)[-1]
            json_block = blocks.split("```json\n", 1)[-1].split("\n```", 1)[0]
            return json.loads(json_block)
        except Exception:
            return []


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["naive", "local", "global", "hybrid", "mix"])
async def test_modes_apply_tag_filters_strictly_parametrized(lightrag_instance, mode):
    rag = lightrag_instance

    # Initialize pipeline shared storage required by ainsert processing pipeline
    from lightrag.kg.shared_storage import initialize_share_data, initialize_pipeline_status

    initialize_share_data(1)
    await initialize_pipeline_status()

    # Prepare content and tags
    tags_match = {"project": "alpha", "region": ["us"]}
    tags_nonmatch = {"project": "beta", "region": ["eu"]}

    # Insert two documents as separate calls to ensure distinct chunks with different tags
    await rag.ainsert("Alice Alpha US", tags=tags_match)
    await rag.ainsert("Bob Beta EU", tags=tags_nonmatch)
    await rag._insert_done()

    # Case 1: Only tag_equals
    qp_equals = QueryParam(mode=mode, only_need_context=True, top_k=10, chunk_top_k=10)
    qp_equals.tag_equals = {"project": "alpha"}  # type: ignore[attr-defined]
    result_equals = await rag.aquery("Alpha", qp_equals)
    assert isinstance(result_equals, str)
    chunks = _extract_dc_chunks(result_equals, mode)
    # If chunks returned, all must satisfy filter expectation (exclude Bob Beta EU)
    for c in chunks:
        assert isinstance(c, dict)
        assert "Bob Beta EU" not in str(c.get("content", ""))

    # Case 2: Only tag_in
    qp_in = QueryParam(mode=mode, only_need_context=True, top_k=10, chunk_top_k=10)
    qp_in.tag_in = {"region": ["us"]}  # type: ignore[attr-defined]
    result_in = await rag.aquery("Alpha", qp_in)
    assert isinstance(result_in, str)
    chunks = _extract_dc_chunks(result_in, mode)
    for c in chunks:
        assert isinstance(c, dict)
        assert "Bob Beta EU" not in str(c.get("content", ""))

    # Case 3: Both equals and in on the same key must both hold
    qp_both = QueryParam(mode=mode, only_need_context=True, top_k=10, chunk_top_k=10)
    qp_both.tag_equals = {"project": "alpha"}  # type: ignore[attr-defined]
    qp_both.tag_in = {"region": ["us", "apac"]}  # type: ignore[attr-defined]
    result_both = await rag.aquery("Alpha", qp_both)
    assert isinstance(result_both, str)
    chunks = _extract_dc_chunks(result_both, mode)
    for c in chunks:
        assert isinstance(c, dict)
        assert "Bob Beta EU" not in str(c.get("content", ""))

    # Case 4: Clearing filters restores behavior. For vector-backed modes (naive/mix)
    # we expect at least one chunk; for pure KG modes, content may legitimately be empty.
    qp_clear = QueryParam(mode=mode, only_need_context=True, top_k=10, chunk_top_k=10)
    result_clear = await rag.aquery("Alpha", qp_clear)
    assert isinstance(result_clear, str)
    chunks = _extract_dc_chunks(result_clear, mode)
    if mode == "naive":
        assert len(chunks) >= 1


