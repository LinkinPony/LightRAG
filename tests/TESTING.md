## Testing Guidelines for LightRAG

This document defines how we write, organize, and run tests for LightRAG. It aims to ensure refactors and new features do not break existing behavior.

These rules are intentionally practical and minimal; follow them unless a strong reason exists to deviate. When deviating, document the reason in the PR description.

### Test Runner and Scope
- We use `pytest` as the single test runner.
- All test files must live under `tests/` and be discoverable by pytest (`test_*.py` or `*_test.py`).
- Prefer unit tests first; complement with integration tests for storage backends and API surfaces.

### Test Structure
- Organize tests by domain capability rather than file parity with sources, for example:
  - `tests/unit/` for pure logic and utilities
  - `tests/integration/` for storage backends (Qdrant, MongoDB, Neo4j, etc.) and API routes
  - `tests/e2e/` for end-to-end user flows (optional, kept lightweight)
- Within each module, group tests by feature area using `pytest` classes or modules.

### Naming Conventions
- Test files: `test_<area>.py`
- Test functions: `test_<behavior>_when_<condition>[_then_<result>]`
- Fixtures: `<resource>_fixture` or just `<resource>` when unambiguous.

### Determinism and Isolation
- Tests must be deterministic. Seed randomness (e.g., `random`, `numpy`) at the beginning of tests using a shared fixture.
- Avoid relying on the system clock; pass times explicitly or freeze time when necessary.
- Each test must clean up any resources it creates (collections, temp files, env vars). Prefer `tmp_path`/`tmp_path_factory` for filesystem work.
- Do not depend on other tests’ side effects.

### Performance and Timeouts
- Keep individual unit tests under ~1s and integration tests under ~10s each.
- Use timeouts for long-running async tasks when applicable.
- Skip expensive integration tests by default unless the required services are available (see Markers section).

### External Services and Backends
LightRAG supports multiple storage backends. Tests must run even when external services are not present by default.

- Provide two layers of coverage:
  1) Mocked/Local mode (default): Use mocks/fakes to validate logic without external services.
  2) Real backend mode (opt-in): If services are available, run integration tests against them.

- For backends supported in this repo:
  - Qdrant: prefer using an ephemeral container or a locally running instance. Integration tests should detect availability via env (e.g., `QDRANT_URL`).
  - MongoDB: similar pattern; detect via `MONGO_URI`/`MONGO_DATABASE`.
  - Neo4j: detect via `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`.

- Tests must skip (not fail) when a backend is not reachable. Use `pytest.skip` or markers (see below).

### Markers
Define and use markers to control test selection:
- `@pytest.mark.unit` for pure unit tests (default target on CI).
- `@pytest.mark.integration` for tests requiring external services.
- `@pytest.mark.slow` for tests exceeding typical time bounds.
- `@pytest.mark.e2e` for end-to-end flows (optional).

In `pytest.ini` (or pyproject’s tool.pytest.ini_options) define markers to avoid warnings. Example:
```
[pytest]
markers =
    unit: fast unit tests
    integration: tests requiring external services
    slow: long-running tests
    e2e: end-to-end tests
```

### Async Code
- Use `pytest.mark.asyncio` for async tests.
- Keep event loop usage straightforward; avoid nested loop management.
- Prefer async fixtures for storage clients.
- When your code uses background async workers (e.g., functions decorated with `priority_limit_async_func_call`), ensure tests gracefully shut them down in fixture teardowns to prevent warnings like "Task was destroyed but it is pending!" and "Event loop is closed" during pytest loop cleanup. Example:

```python
# In tests/conftest.py fixture teardown
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
```

### Fixtures
- Centralize shared fixtures in `tests/conftest.py`:
  - `seeded_rng` to seed randomness
  - `temp_working_dir` to isolate filesystem side effects
  - Optional backends: `qdrant_client`, `mongo_db`, `neo4j_driver` that auto-skip when env/config missing
- Keep fixtures small and composable; avoid doing significant work in session-scoped fixtures unless necessary.

### Assertions and Style
- Prefer precise assertions on types, shapes, and key fields.
- For text outputs (LLM content), assert on structural invariants and key substrings rather than entire free-form text.
- When asserting floating similarities or thresholds, use tolerances (e.g., `pytest.approx`).

### Test Data
- Keep small, focused input samples in code or `tests/data/`.
- For Tag Plan C, include representative TagMap examples:
  - string values: `{"project": "alpha"}`
  - list of strings: `{"region": ["us", "eu"]}`
- Avoid large corpus or network downloads in tests.

### Logging and Debugging
- Tests should not depend on logs, but may assert that certain warnings/errors are raised.
- Reduce noise by configuring lower log levels in test runs; elevate selectively for debugging.

### Coverage Goals
- Unit coverage for core logic (token control, selection strategies, matching predicates) ≥ 85% lines/branches where practical.
- Integration tests focus on critical paths (insert/query lifecycles, storage CRUD, Tag Plan C filters).
- Do not sacrifice readability for marginal coverage gains.

### Failure Policy
- A failing test must provide a clear reason; use descriptive assertion messages.
- If a backend is unavailable, integration tests must `skip` rather than `fail`.

### Default-ignored legacy tests
- By default, pytest will ignore the following legacy/integration helpers to keep the default test run fast and backend-agnostic:
  - `tests/test_graph_storage.py`
  - `tests/test_lightrag_ollama_chat.py`
- To include them explicitly, set the environment variable and run pytest:
```
LIGHTRAG_RUN_LEGACY_TESTS=1 pytest -q
```

### CI Recommendations
- Default CI job: run `pytest -m unit -q` and type checks/linters.
- Optional CI job (nightly or on-demand): run `pytest -m "unit or integration"` when backends are provisioned.

### How to Run Tests
Unit tests only:
```
pytest -m unit -q
```

Unit + available integrations (auto-skip unavailable):
```
pytest -m "unit or integration" -q
```

Run a single test file or test:
```
pytest tests/unit/test_tags.py::test_matches_tag_filters -q
```

### Adding New Tests
- Place under appropriate folder (`unit`, `integration`, or `e2e`).
- Use markers and fixtures as above.
- Keep assertions tight and inputs minimal.

---
By adhering to this guide, we ensure LightRAG remains stable during refactors while keeping tests fast, readable, and reliable.


