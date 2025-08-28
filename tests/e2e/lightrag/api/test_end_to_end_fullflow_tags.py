import sys
import types
import json
import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.e2e
def test_e2e_insert_query_graph_with_tag_filters(tmp_path):
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

    # Stub json_repair
    if "json_repair" not in sys.modules:
        _jr = types.ModuleType("json_repair")
        _jr.loads = lambda s: json.loads(s)
        sys.modules["json_repair"] = _jr

    # Stub nano_vectordb for NanoVectorDBStorage
    if "nano_vectordb" not in sys.modules:
        import numpy as _np
        _nv = types.ModuleType("nano_vectordb")
        class NanoVectorDB:
            def __init__(self, dim: int, storage_file: str | None = None):
                self.dim = dim
                self._NanoVectorDB__storage = {"data": []}
            def upsert(self, datas: list[dict]):
                id_to_index = {d.get("__id__"): i for i, d in enumerate(self._NanoVectorDB__storage["data"])}
                for d in datas:
                    cid = d.get("__id__") or d.get("id")
                    if cid in id_to_index:
                        self._NanoVectorDB__storage["data"][id_to_index[cid]] = d.copy()
                    else:
                        self._NanoVectorDB__storage["data"].append(d.copy())
                return datas
            def query(self, query, top_k: int, better_than_threshold: float = 0.0):
                qv = query
                if isinstance(qv, list):
                    qv = _np.array(qv)
                if hasattr(qv, "ndim") and qv.ndim == 2:
                    qv = qv[0]
                qn = _np.linalg.norm(qv) + 1e-8
                results = []
                for d in self._NanoVectorDB__storage["data"]:
                    dv = d.get("__vector__")
                    if dv is None:
                        continue
                    dv = _np.array(dv, dtype=_np.float32)
                    dn = _np.linalg.norm(dv) + 1e-8
                    score = float(_np.dot(qv, dv) / (qn * dn))
                    if score >= better_than_threshold:
                        item = d.copy()
                        item["__metrics__"] = score
                        results.append(item)
                results.sort(key=lambda x: x.get("__metrics__", 0.0), reverse=True)
                return results[: top_k]
            def get(self, ids: list[str]):
                out = []
                for cid in ids:
                    for d in self._NanoVectorDB__storage["data"]:
                        if d.get("__id__") == cid:
                            out.append(d.copy())
                            break
                return out
            def delete(self, ids: list[str]):
                self._NanoVectorDB__storage["data"] = [d for d in self._NanoVectorDB__storage["data"] if d.get("__id__") not in ids]
            def save(self):
                return True
        _nv.NanoVectorDB = NanoVectorDB
        sys.modules["nano_vectordb"] = _nv

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
        # Pre-populate graph nodes/edges with tag properties to ensure /graphs reflects them
        await rag.chunk_entity_relation_graph.upsert_node(
            "Alice",
            {
                "name": "Alice",
                "tags_json": json.dumps({"project": "alpha", "region": ["us"]}),
            },
        )
        await rag.chunk_entity_relation_graph.upsert_node(
            "Bob",
            {
                "name": "Bob",
                "tags": {"project": "beta", "region": ["eu"]},
            },
        )
        await rag.chunk_entity_relation_graph.upsert_edge(
            "Alice",
            "Bob",
            {
                "type": "knows",
                "weight": 1.0,
                "tags_json": json.dumps({"project": "alpha", "region": ["us"]}),
            },
        )
        # Persist graph to disk and notify other processes
        await rag.chunk_entity_relation_graph.index_done_callback()
        try:
            yield
        finally:
            await rag.finalize_storages()
            finalize_share_data()

    app = FastAPI(lifespan=lifespan)

    from lightrag.api.routers.document_routes import DocumentManager, create_document_routes
    from lightrag.api.routers.query_routes import create_query_routes
    from lightrag.api.routers.graph_routes import create_graph_routes

    api_key = "test-key"
    doc_manager = DocumentManager(input_dir=str(tmp_path / "inputs"), workspace="e2e_fullflow")
    app.include_router(create_document_routes(rag, doc_manager, api_key))
    app.include_router(create_query_routes(rag, api_key, top_k=60))
    app.include_router(create_graph_routes(rag, api_key))

    with TestClient(app) as client:
        # Upload two texts with tags
        def upload_text(filename: str, content: str, tags: dict | None):
            files = {"file": (filename, content.encode("utf-8"), "text/plain")}
            data = {}
            if tags is not None:
                data["tags"] = json.dumps(tags)
            return client.post("/documents/upload", files=files, data=data, headers={"X-API-Key": api_key})

        r1 = upload_text("alpha.txt", "Alice Alpha US", {"project": "alpha", "region": ["us"]})
        assert r1.status_code == 200, r1.text
        r2 = upload_text("beta.txt", "Bob Beta EU", {"project": "beta", "region": ["eu"]})
        assert r2.status_code == 200, r2.text

        # Wait briefly for background processing
        time.sleep(0.5)

        # Query with filters: ensure non-matching content is not present
        def query(payload: dict):
            resp = client.post("/query", json=payload, headers={"X-API-Key": api_key})
            assert resp.status_code == 200, resp.text
            return resp.json()["response"]

        base_payload = {"query": "Alpha", "mode": "naive", "only_need_context": True, "chunk_top_k": 5}
        resp_filtered = query({**base_payload, "tag_equals": {"project": "alpha"}, "tag_in": {"region": ["us"]}})
        assert "Bob Beta EU" not in resp_filtered

        # Query graphs to verify tags properties appear
        gr = client.get(
            "/graphs",
            params={
                "label": "Alice",
                "max_depth": 2,
                "max_nodes": 10,
                "tag_equals": json.dumps({"project": "alpha"}),
                "tag_in": json.dumps({"region": ["us"]}),
            },
            headers={"X-API-Key": api_key},
        )
        assert gr.status_code == 200, gr.text
        data = gr.json()
        assert isinstance(data.get("nodes"), list)
        assert isinstance(data.get("edges"), list)
        node_props = [n.get("properties", {}) for n in data["nodes"]]
        edge_props = [e.get("properties", {}) for e in data["edges"]]
        has_tags = any(("tags" in p) or ("tags_json" in p) for p in node_props + edge_props)
        assert has_tags

