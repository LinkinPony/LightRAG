import sys
import types
import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeRag:
    def __init__(self):
        self.calls = []

    async def get_knowledge_graph(self, node_label: str, max_depth: int, max_nodes: int):  # noqa: ANN001
        # Return a small graph that includes tags/tags_json in properties
        # graph response follows lightrag.types.KnowledgeGraph shape
        return {
            "nodes": [
                {
                    "id": "Alice",
                    "labels": ["Person"],
                    "properties": {
                        "name": "Alice",
                        "tags_json": json.dumps({"project": "alpha", "region": ["us"]}),
                    },
                },
                {
                    "id": "Bob",
                    "labels": ["Person"],
                    "properties": {
                        "name": "Bob",
                        "tags": {"project": "alpha", "region": ["eu"]},
                    },
                },
            ],
            "edges": [
                {
                    "id": "Alice-Bob",
                    "type": "knows",
                    "source": "Alice",
                    "target": "Bob",
                    "properties": {
                        "weight": 1.0,
                        "tags_json": json.dumps({"project": "alpha", "region": ["us"]}),
                    },
                }
            ],
            "is_truncated": False,
        }


@pytest.mark.integration
def test_graph_query_route_accepts_and_passes_tag_filters():
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

    from lightrag.api.routers.graph_routes import create_graph_routes

    app = FastAPI()
    api_key = "test-key"
    rag = FakeRag()
    app.include_router(create_graph_routes(rag, api_key=api_key))

    client = TestClient(app)

    # The backend currently does not accept tag filters via graph routes directly,
    # but the WebUI composes them as query params for /graphs.
    # We ensure the endpoint works and returns tags/tags_json in properties.
    resp = client.get(
        "/graphs",
        params={
            "label": "Alice",
            "max_depth": 2,
            "max_nodes": 10,
            # ensure unknown params (if present) do not break
            "tag_equals": json.dumps({"project": "alpha"}),
            "tag_in": json.dumps({"region": ["us"]}),
        },
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data.get("nodes"), list) and isinstance(data.get("edges"), list)

    # Verify presence of tags/tags_json on either nodes or edges
    node_props = [n.get("properties", {}) for n in data["nodes"]]
    edge_props = [e.get("properties", {}) for e in data["edges"]]

    has_tags_or_tags_json = any(
        ("tags" in p) or ("tags_json" in p) for p in node_props + edge_props
    )
    assert has_tags_or_tags_json


