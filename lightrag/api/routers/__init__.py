"""
This module contains router exports for the LightRAG API.

Note:
- We avoid importing a module-level `router` from `query_routes` to prevent hard coupling.
- Use `create_query_routes` from `query_routes` to construct a router instance.
"""

from .document_routes import router as document_router
from .graph_routes import router as graph_router
from .ollama_api import OllamaAPI

# Re-export factory for query routes for convenience
try:
    from .query_routes import create_query_routes  # type: ignore
except Exception:
    # Safe fallback in contexts where dependencies may be stubbed in tests
    create_query_routes = None  # type: ignore

__all__ = [
    "document_router",
    "graph_router",
    "OllamaAPI",
    "create_query_routes",
]
