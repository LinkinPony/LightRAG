import sys
import types
import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _Capture:
    last = None


class FakeRag:
    async def aquery(self, query: str, param, **_kwargs):  # noqa: ANN001
        # capture the QueryParam for assertions
        _Capture.last = (query, param)
        return "OK"


@pytest.mark.integration
def test_query_route_accepts_and_passes_tag_filters():
    # Stub pipmaster and ascii_colors to avoid side effects from routers __init__ imports
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

    # Ensure shared storage initialized to satisfy utils_api imports using get_namespace_data
    from lightrag.kg.shared_storage import (
        initialize_share_data,
        initialize_pipeline_status,
        get_namespace_data,
    )
    initialize_share_data(1)
    import asyncio
    asyncio.get_event_loop().run_until_complete(initialize_pipeline_status())

    # Also ensure llm cache namespace exists to avoid missing update flags error
    try:
        asyncio.get_event_loop().run_until_complete(get_namespace_data("tags_llm_response_cache"))
    except Exception:
        # get_namespace_data will create the namespace after initialize_share_data; ignore
        pass

    # Disable rerank warnings
    os.environ["RERANK_BY_DEFAULT"] = "false"

    from lightrag.api.routers.query_routes import create_query_routes

    app = FastAPI()
    api_key = "test-key"
    rag = FakeRag()
    app.include_router(create_query_routes(rag, api_key=api_key, top_k=60))

    client = TestClient(app)

    payload = {
        "query": "hello",
        "mode": "naive",
        "tag_equals": {"project": "alpha"},
        "tag_in": {"region": ["us", "eu"]},
    }
    resp = client.post("/query", json=payload, headers={"X-API-Key": api_key})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("response") == "OK"

    # Verify pass-through into QueryParam
    assert _Capture.last is not None
    q, param = _Capture.last
    assert q == "hello"
    assert getattr(param, "tag_equals", None) == {"project": "alpha"}
    assert getattr(param, "tag_in", None) == {"region": ["us", "eu"]}


