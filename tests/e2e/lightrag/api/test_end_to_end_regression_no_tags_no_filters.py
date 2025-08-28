import sys
import types
import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.e2e
def test_e2e_regression_no_tags_no_filters(tmp_path):
    # Stub pipmaster and ascii_colors to avoid side effects
    if "pipmaster" not in sys.modules:
        _pm = types.ModuleType("pipmaster")
        _pm.is_installed = lambda *_args, **_kwargs: True
        _pm.install = lambda *_args, **_kwargs: None
        sys.modules["pipmaster"] = _pm
    if "ascii_colors" not in sys.modules:
        _ac = types.ModuleType("ascii_colors")
        class _Dummy:
            def __getattr__(self, _):
                return lambda *a, **k: None
        _ac.ASCIIColors = _Dummy()
        def trace_exception(e):
            return None
        _ac.trace_exception = trace_exception
        sys.modules["ascii_colors"] = _ac

    # Build app with lightweight storages and stubs (same pattern as other E2Es)
    from lightrag.lightrag import LightRAG
    from lightrag.utils import EmbeddingFunc, Tokenizer

    class DummyTokenizer:
        def encode(self, content: str):
            return [ord(c) % 251 for c in content]
        def decode(self, tokens):
            return "".join(chr(t) for t in tokens)

    async def fake_embed(batch, *_args, **_kwargs):
        import numpy as np
        arrs = []
        for text in batch:
            vec = np.zeros(8, dtype=np.float32)
            for i, ch in enumerate(text.encode("utf-8")):
                vec[i % 8] += float(ch) / 255.0
            arrs.append(vec)
        return np.stack(arrs, axis=0)

    async def dummy_llm(prompt: str, system_prompt: str | None = None, stream: bool = False, keyword_extraction: bool = False, history_messages=None, **kwargs):
        if keyword_extraction:
            return "{\"high_level_keywords\": [], \"low_level_keywords\": []}"
        return "OK"

    rag = LightRAG(
        working_dir=str(tmp_path / "rag_storage"),
        kv_storage="JsonKVStorage",
        vector_storage="NanoVectorDBStorage",
        graph_storage="NetworkXStorage",
        doc_status_storage="JsonDocStatusStorage",
        embedding_func=EmbeddingFunc(embedding_dim=8, func=fake_embed),
        tokenizer=Tokenizer("dummy", DummyTokenizer()),
        llm_model_func=dummy_llm,
    )

    from contextlib import asynccontextmanager
    from lightrag.kg.shared_storage import initialize_pipeline_status, finalize_share_data

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await rag.initialize_storages()
        await initialize_pipeline_status()
        try:
            yield
        finally:
            await rag.finalize_storages()
            finalize_share_data()

    app = FastAPI(lifespan=lifespan)

    from lightrag.api.routers.document_routes import DocumentManager, create_document_routes
    from lightrag.api.routers.query_routes import create_query_routes

    api_key = "test-key"
    doc_manager = DocumentManager(input_dir=str(tmp_path / "inputs"), workspace="e2e_regression")
    app.include_router(create_document_routes(rag, doc_manager, api_key))
    app.include_router(create_query_routes(rag, api_key, top_k=60))

    with TestClient(app) as client:
        # Upload two texts without any tags
        def upload_text(filename: str, content: str):
            files = {"file": (filename, content.encode("utf-8"), "text/plain")}
            return client.post("/documents/upload", files=files, headers={"X-API-Key": api_key})

        r1 = upload_text("d1.txt", "Alice works in US")
        assert r1.status_code == 200, r1.text
        r2 = upload_text("d2.txt", "Bob travels to EU")
        assert r2.status_code == 200, r2.text

        # Wait briefly for background processing
        time.sleep(0.5)

        # Query without any tag filters to assert baseline behavior is fine
        def query(payload: dict):
            resp = client.post("/query", json=payload, headers={"X-API-Key": api_key})
            assert resp.status_code == 200, resp.text
            return resp.json()["response"]

        base_payload = {"query": "Alice", "mode": "naive", "only_need_context": True, "chunk_top_k": 5}
        resp = query(base_payload)
        # Only assert invariant: it returns a string response
        assert isinstance(resp, str)

