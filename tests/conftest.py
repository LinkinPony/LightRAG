import asyncio
import sys
import types
import json as _json
import os
import random
from typing import AsyncIterator, Callable

import numpy as np
import pytest
import pytest_asyncio

# Ensure local project root is on sys.path so `pytest` imports local package
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Stub json_repair BEFORE importing any lightrag modules
if "json_repair" not in sys.modules:
    _jr = types.ModuleType("json_repair")
    def _loads(s):
        return _json.loads(s)
    _jr.loads = _loads
    sys.modules["json_repair"] = _jr

# Stub nano_vectordb to avoid external dependency
if "nano_vectordb" not in sys.modules:
    _nv = types.ModuleType("nano_vectordb")

    class NanoVectorDB:
        def __init__(self, dim: int, storage_file: str | None = None):
            self.dim = dim
            # Mimic private storage attr used by LightRAG
            self._NanoVectorDB__storage = {"data": []}

        def upsert(self, datas: list[dict]):
            # Insert or replace by __id__
            id_to_index = {d.get("__id__"): i for i, d in enumerate(self._NanoVectorDB__storage["data"])}
            for d in datas:
                cid = d.get("__id__") or d.get("id")
                if cid in id_to_index:
                    self._NanoVectorDB__storage["data"][id_to_index[cid]] = d.copy()
                else:
                    self._NanoVectorDB__storage["data"].append(d.copy())
            return datas

        def query(self, query, top_k: int, better_than_threshold: float = 0.0):
            import numpy as _np
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
            # sort by score desc
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
            self._NanoVectorDB__storage["data"] = [
                d for d in self._NanoVectorDB__storage["data"] if d.get("__id__") not in ids
            ]

        def save(self):
            # no-op for tests
            return True

    _nv.NanoVectorDB = NanoVectorDB
    sys.modules["nano_vectordb"] = _nv

# Import after stubbing
from lightrag.utils import EmbeddingFunc, Tokenizer


# Default-ignore legacy test files; set LIGHTRAG_RUN_LEGACY_TESTS=1 to include them
LEGACY_IGNORED_TESTS = {"test_graph_storage.py", "test_lightrag_ollama_chat.py"}


def pytest_ignore_collect(collection_path, config):
    if os.environ.get("LIGHTRAG_RUN_LEGACY_TESTS", "").lower() in ("1", "true", "yes"):
        return False
    try:
        filename = os.path.basename(str(collection_path))
    except Exception:
        return False
    return filename in LEGACY_IGNORED_TESTS


@pytest.fixture(autouse=True)
def seeded_rng():
    random.seed(1337)
    np.random.seed(1337)


class DummyTokenizer:
    def encode(self, content: str):
        return [ord(c) % 251 for c in content]

    def decode(self, tokens):
        return "".join(chr(t) for t in tokens)


@pytest.fixture
def fake_embedding_func() -> EmbeddingFunc:
    async def _embed(batch, *_args, **_kwargs):
        # Deterministic embedding based on ascii codes
        arrs = []
        for text in batch:
            vec = np.zeros(8, dtype=np.float32)
            for i, ch in enumerate(text.encode("utf-8")):
                vec[i % 8] += float(ch) / 255.0
            arrs.append(vec)
        return np.stack(arrs, axis=0)

    return EmbeddingFunc(embedding_dim=8, func=_embed)


@pytest.fixture
def tmp_workdir(tmp_path):
    d = tmp_path / "rag_storage"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


@pytest_asyncio.fixture
async def lightrag_instance(fake_embedding_func, tmp_workdir: str):
    from lightrag.lightrag import LightRAG

    async def dummy_llm(
        prompt: str,
        system_prompt: str | None = None,
        stream: bool = False,
        keyword_extraction: bool = False,
        history_messages=None,
        **kwargs,
    ):
        if keyword_extraction:
            return "{\"high_level_keywords\": [], \"low_level_keywords\": []}"
        return "OK"
    # Force local storages to JSON/Nano to avoid external deps
    os.environ.pop("QDRANT_URL", None)
    rag = LightRAG(
        working_dir=tmp_workdir,
        kv_storage="JsonKVStorage",
        vector_storage="NanoVectorDBStorage",
        graph_storage="NetworkXStorage",
        doc_status_storage="JsonDocStatusStorage",
        embedding_func=fake_embedding_func,
        tokenizer=Tokenizer("dummy", DummyTokenizer()),
        llm_model_func=dummy_llm,
    )
    # tokenizer already provided to avoid importing tiktoken in __post_init__

    await rag.initialize_storages()
    try:
        yield rag
    finally:
        # Gracefully shutdown async worker pools created by decorators to avoid
        # pending-task warnings when pytest closes the event loop
        try:
            embedding = getattr(rag, "embedding_func", None)
            if embedding is not None and hasattr(embedding, "shutdown"):
                await embedding.shutdown()
        except Exception:
            pass
        try:
            llm = getattr(rag, "llm_model_func", None)
            if llm is not None and hasattr(llm, "shutdown"):
                await llm.shutdown()
        except Exception:
            pass

        # Clean storages
        await rag.finalize_storages()


