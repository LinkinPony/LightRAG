import os
import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_qdrant_server_side_tag_filters_skip_when_unavailable():
    """
    Phase 3: When Qdrant available, verify server-side filtering with tags.
    This test intentionally auto-skips when Qdrant is not configured.
    """
    if not os.environ.get("QDRANT_URL"):
        pytest.skip("Qdrant not configured; skipping server-side tag filter test")

    # Placeholder content:
    # - Initialize LightRAG with QdrantVectorDBStorage
    # - Insert chunks with tags
    # - Query with tag_equals/tag_in and assert results filtered server-side
    # Implementation will be added when Phase 3 lands.


