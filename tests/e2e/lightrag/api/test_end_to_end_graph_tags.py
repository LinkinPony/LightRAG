import sys
import types
import json
import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.e2e
def test_e2e_graph_filter_and_properties_display(tmp_path):
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

    app = FastAPI()
    from lightrag.kg.shared_storage import initialize_pipeline_status, finalize_share_data

    @app.on_event("startup")
    async def _startup():
        await rag.initialize_storages()
        await initialize_pipeline_status()

        # Pre-populate graph with nodes/edges containing tags or tags_json
        # Nodes
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
                "tags": {"project": "alpha", "region": ["eu"]},
            },
        )
        # Node without tags
        await rag.chunk_entity_relation_graph.upsert_node(
            "Carol",
            {
                "name": "Carol",
                "role": "tester",
            },
        )
        # Edge
        await rag.chunk_entity_relation_graph.upsert_edge(
            "Alice",
            "Bob",
            {
                "type": "knows",
                "weight": 1.0,
                "tags_json": json.dumps({"project": "alpha", "region": ["us"]}),
            },
        )
        # Edge without tags
        await rag.chunk_entity_relation_graph.upsert_edge(
            "Bob",
            "Carol",
            {
                "type": "works_with",
                "weight": 0.5,
            },
        )

        # Persist graph to disk and notify other processes to avoid reload race
        await rag.chunk_entity_relation_graph.index_done_callback()

    @app.on_event("shutdown")
    async def _shutdown():
        await rag.finalize_storages()
        finalize_share_data()

    from lightrag.api.routers.graph_routes import create_graph_routes

    api_key = "test-key"
    app.include_router(create_graph_routes(rag, api_key))

    with TestClient(app) as client:
        # Allow startup to complete
        time.sleep(0.2)

        # Query graphs with tolerated tag filter params (ignored by backend but sent by WebUI)
        resp = client.get(
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
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data.get("nodes"), list)
        assert isinstance(data.get("edges"), list)

        # nodes/edges should include tags or tags_json properties
        node_props = [n.get("properties", {}) for n in data["nodes"]]
        edge_props = [e.get("properties", {}) for e in data["edges"]]
        has_tags = any(("tags" in p) or ("tags_json" in p) for p in node_props + edge_props)
        assert has_tags

        # Carol node should not have tags fields (locate by stable id instead of name)
        carol_node = next((n for n in data["nodes"] if n.get("id") == "Carol"), None)
        if carol_node is not None:
            carol_props = carol_node.get("properties", {})
            assert "tags" not in carol_props and "tags_json" not in carol_props

        # The works_with edge Bob-Carol should not have tags fields
        works_with_props = None
        for e in data["edges"]:
            if {e.get("source"), e.get("target")} == {"Bob", "Carol"}:
                works_with_props = e.get("properties", {})
                break
        if works_with_props is not None:
            assert "tags" not in works_with_props and "tags_json" not in works_with_props


