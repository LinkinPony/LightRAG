import os
import sys
import types
import uuid
import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_qdrant_server_side_tag_filters_skip_when_unavailable(
    fake_embedding_func, monkeypatch
):
    """
    Phase 3: Verify Qdrant server-side tag filtering for text chunks.

    Auto-skips when Qdrant is not configured (no QDRANT_URL in env).
    """
    if not os.environ.get("QDRANT_URL"):
        pytest.skip("Qdrant not configured; skipping server-side tag filter test")

    # Ensure qdrant-client is available; otherwise skip
    try:
        from qdrant_client import QdrantClient  # noqa: F401
    except Exception:
        pytest.skip("qdrant-client not installed; skipping server-side tag filter test")

    # Stub pipmaster to avoid import-time dependency in qdrant_impl
    if "pipmaster" not in sys.modules:
        _pm = types.ModuleType("pipmaster")
        _pm.is_installed = lambda *_args, **_kwargs: True
        _pm.install = lambda *_args, **_kwargs: None
        sys.modules["pipmaster"] = _pm

    # Lazy import to avoid side effects before stubbing
    from lightrag.kg.qdrant_impl import QdrantVectorDBStorage
    from lightrag.kg.shared_storage import initialize_share_data, finalize_share_data

    # Quick connectivity probe; skip if unreachable
    try:
        _probe = QdrantClient(
            url=os.environ.get("QDRANT_URL"), api_key=os.environ.get("QDRANT_API_KEY")
        )
        _probe.get_collections()
    except Exception:
        pytest.skip("Qdrant not reachable; skipping server-side tag filter test")

    # Use a unique workspace and namespace to ensure isolation across runs
    ws = f"e2e_{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("QDRANT_WORKSPACE", ws)
    namespace = f"chunks_{uuid.uuid4().hex[:8]}"

    # Initialize shared storage locks (required by QdrantVectorDBStorage.initialize)
    initialize_share_data(workers=1)

    # Minimal global_config required by storage
    global_config = {
        "embedding_batch_num": 32,
        "vector_db_storage_cls_kwargs": {"cosine_better_than_threshold": 0.0},
    }

    storage = QdrantVectorDBStorage(
        namespace=namespace,
        workspace=None,  # overridden by QDRANT_WORKSPACE
        global_config=global_config,
        embedding_func=fake_embedding_func,
        meta_fields={"content", "tags"},
    )

    # Initialize collection
    await storage.initialize()

    try:
        # Insert three chunks with distinct tag combinations
        items = {
            "doc_a": {
                "content": "alpha us fruit",
                "tags": {"project": "alpha", "region": ["us"]},
            },
            "doc_b": {
                "content": "alpha eu fruit",
                "tags": {"project": "alpha", "region": ["eu"]},
            },
            "doc_c": {
                "content": "beta us fruit",
                "tags": {"project": "beta", "region": ["us"]},
            },
        }

        await storage.upsert(items)

        # Baseline query without tag filters
        baseline = await storage.query(query="fruit", top_k=3)
        baseline_count = len(baseline)
        assert baseline_count >= 2  # at least two similar items should be returned

        # tag_equals only
        eq_results = await storage.query(
            query="fruit", top_k=3, tag_equals={"project": "alpha"}
        )
        assert len(eq_results) == 2
        for r in eq_results:
            tags = r.get("tags") or {}
            assert tags.get("project") == "alpha"

        # tag_in only
        in_results = await storage.query(
            query="fruit", top_k=3, tag_in={"region": ["us"]}
        )
        assert len(in_results) == 2
        for r in in_results:
            tags = r.get("tags") or {}
            regions = tags.get("region") or []
            assert "us" in regions

        # both tag_equals and tag_in must be satisfied simultaneously
        eq_in_results = await storage.query(
            query="fruit",
            top_k=3,
            tag_equals={"project": "alpha"},
            tag_in={"region": ["us"]},
        )
        assert len(eq_in_results) == 1
        tags = eq_in_results[0].get("tags") or {}
        assert tags.get("project") == "alpha"
        assert "us" in (tags.get("region") or [])

        # Server-side filtering should reduce candidates compared to baseline
        assert len(eq_results) <= baseline_count
        assert len(eq_in_results) < len(eq_results)
    finally:
        # Clean up the test collection
        await storage.drop()
        finalize_share_data()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_qdrant_entity_relation_server_side_tag_filters(
    fake_embedding_func, monkeypatch
):
    """
    Phase 4: Verify Qdrant server-side tag filtering for entities and relationships.

    Auto-skips when Qdrant is not configured/available.
    """
    if not os.environ.get("QDRANT_URL"):
        pytest.skip("Qdrant not configured; skipping entity/relation tag filter test")

    # Ensure qdrant-client is available; otherwise skip
    try:
        from qdrant_client import QdrantClient  # noqa: F401
    except Exception:
        pytest.skip("qdrant-client not installed; skipping entity/relation tag filter test")

    # Stub pipmaster to avoid import-time dependency in qdrant_impl
    if "pipmaster" not in sys.modules:
        _pm = types.ModuleType("pipmaster")
        _pm.is_installed = lambda *_args, **_kwargs: True
        _pm.install = lambda *_args, **_kwargs: None
        sys.modules["pipmaster"] = _pm

    # Lazy import to avoid side effects before stubbing
    from lightrag.kg.qdrant_impl import QdrantVectorDBStorage
    from lightrag.kg.shared_storage import initialize_share_data, finalize_share_data

    # Quick connectivity probe; skip if unreachable
    try:
        _probe = QdrantClient(
            url=os.environ.get("QDRANT_URL"), api_key=os.environ.get("QDRANT_API_KEY")
        )
        _probe.get_collections()
    except Exception:
        pytest.skip("Qdrant not reachable; skipping entity/relation tag filter test")

    # Use a unique workspace and namespaces to ensure isolation across runs
    ws = f"e2e_{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("QDRANT_WORKSPACE", ws)
    ent_ns = f"entities_{uuid.uuid4().hex[:8]}"
    rel_ns = f"relationships_{uuid.uuid4().hex[:8]}"

    # Initialize shared storage locks (required by QdrantVectorDBStorage.initialize)
    initialize_share_data(workers=1)

    # Minimal global_config required by storage
    global_config = {
        "embedding_batch_num": 32,
        "vector_db_storage_cls_kwargs": {"cosine_better_than_threshold": 0.0},
    }

    entities = QdrantVectorDBStorage(
        namespace=ent_ns,
        workspace=None,
        global_config=global_config,
        embedding_func=fake_embedding_func,
        meta_fields={"entity_name", "content", "tags"},
    )

    relationships = QdrantVectorDBStorage(
        namespace=rel_ns,
        workspace=None,
        global_config=global_config,
        embedding_func=fake_embedding_func,
        meta_fields={"src_id", "tgt_id", "content", "tags"},
    )

    await entities.initialize()
    await relationships.initialize()

    try:
        # Insert entities with distinct tag combinations
        ent_items = {
            "alice": {
                "entity_name": "Alice",
                "content": "person entity",  # simple common token
                "tags": {"project": "alpha", "region": ["us"]},
            },
            "bob": {
                "entity_name": "Bob",
                "content": "person entity",
                "tags": {"project": "alpha", "region": ["eu"]},
            },
            "charlie": {
                "entity_name": "Charlie",
                "content": "person entity",
                "tags": {"project": "beta", "region": ["us"]},
            },
        }
        await entities.upsert(ent_items)

        # Insert relationships with distinct tag combinations
        rel_items = {
            "alice-bob": {
                "src_id": "Alice",
                "tgt_id": "Bob",
                "content": "works-with relation",
                "tags": {"project": "alpha", "region": ["us"]},
            },
            "alice-charlie": {
                "src_id": "Alice",
                "tgt_id": "Charlie",
                "content": "knows relation",
                "tags": {"project": "alpha", "region": ["eu"]},
            },
            "bob-charlie": {
                "src_id": "Bob",
                "tgt_id": "Charlie",
                "content": "relates relation",
                "tags": {"project": "beta", "region": ["us"]},
            },
        }
        await relationships.upsert(rel_items)

        # Baselines
        ent_baseline = await entities.query(query="entity", top_k=5)
        rel_baseline = await relationships.query(query="relation", top_k=5)
        assert len(ent_baseline) >= 2
        assert len(rel_baseline) >= 2

        # Entities: tag_equals only
        ent_eq = await entities.query(query="entity", top_k=5, tag_equals={"project": "alpha"})
        assert len(ent_eq) == 2
        for r in ent_eq:
            tags = r.get("tags") or {}
            assert tags.get("project") == "alpha"

        # Entities: tag_in only
        ent_in = await entities.query(query="entity", top_k=5, tag_in={"region": ["us"]})
        assert len(ent_in) == 2
        for r in ent_in:
            tags = r.get("tags") or {}
            assert "us" in (tags.get("region") or [])

        # Entities: both equals + in
        ent_eq_in = await entities.query(
            query="entity", top_k=5, tag_equals={"project": "alpha"}, tag_in={"region": ["us"]}
        )
        assert len(ent_eq_in) == 1
        etags = ent_eq_in[0].get("tags") or {}
        assert etags.get("project") == "alpha"
        assert "us" in (etags.get("region") or [])

        # Relationships: tag_equals only
        rel_eq = await relationships.query(query="relation", top_k=5, tag_equals={"project": "alpha"})
        assert len(rel_eq) == 2
        for r in rel_eq:
            tags = r.get("tags") or {}
            assert tags.get("project") == "alpha"

        # Relationships: tag_in only
        rel_in = await relationships.query(query="relation", top_k=5, tag_in={"region": ["us"]})
        assert len(rel_in) == 2
        for r in rel_in:
            tags = r.get("tags") or {}
            assert "us" in (tags.get("region") or [])

        # Relationships: both equals + in
        rel_eq_in = await relationships.query(
            query="relation", top_k=5, tag_equals={"project": "alpha"}, tag_in={"region": ["us"]}
        )
        assert len(rel_eq_in) == 1
        rtags = rel_eq_in[0].get("tags") or {}
        assert rtags.get("project") == "alpha"
        assert "us" in (rtags.get("region") or [])

        # Candidate reductions
        assert len(ent_eq) <= len(ent_baseline)
        assert len(ent_eq_in) < len(ent_eq)
        assert len(rel_eq) <= len(rel_baseline)
        assert len(rel_eq_in) < len(rel_eq)
    finally:
        # Clean up test collections and shared storage
        await entities.drop()
        await relationships.drop()
        finalize_share_data()


