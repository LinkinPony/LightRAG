## Tags Development Guide (Tag Plan C)

This document explains the implementation details and integration points for Tag Plan C in LightRAG, covering data model, insert pipeline, query surfaces, storage specifics, and UI integration.

### Scope and constraints

- TagMap type: `dict[str, str | list[str]]` (frontend: `Record<string, string | string[]>`).
- Exact match only, no fuzzy/prefix.
- Backward compatible when fields are absent.

---

## 1) Data model and propagation

Where tags are stored:
- Document status (KV/DocStatus): `metadata.tags`.
- Text chunks (KV): `tags`.
- Qdrant payloads (vector): `tags` object.
- Graph (Neo4j): `tags_json` string on nodes/edges (for inspection/debug).

Propagation path (Core):
- `LightRAG.ainsert(..., tags)` → `apipeline_enqueue_documents(..., tags)` → document status is created with `metadata.tags` and produced chunks inherit the same `tags`.

Key code:
- `lightrag/lightrag.py`: `ainsert`, `apipeline_enqueue_documents` (accepts `tags`).
- `lightrag/operate.py`: tag-aware filtering during retrieval.
- `lightrag/kg/qdrant_impl.py`: server-side tag filters.
- Graph aggregation and storage stages add `tags`/`tags_json` for entities/relations.

---

## 2) Query filter semantics

Types:
- `tag_equals: dict[str, str]`
- `tag_in: dict[str, list[str]]`

Rules:
- Both groups are ANDed together. Each key is ANDed within a group.
- If a key appears in both, the `tag_equals[key]` must also be present in `tag_in[key]`.

Utility:
- `lightrag/utils.py: matches_tag_filters(tags, tag_equals, tag_in) -> bool` enforces the above semantics for client-side safety checks and non-VDB paths.

---

## 3) REST API surfaces

Query routes (`lightrag/api/routers/query_routes.py`):
- `POST /query` and `POST /query/stream` accept optional `tag_equals`, `tag_in` in `QueryRequest` and convert to `QueryParam`.

Documents routes (`lightrag/api/routers/document_routes.py`):
- `POST /documents/upload` accepts multipart form with `file` and optional `tags` (JSON string). The server validates and normalizes TagMap. Parsed tags are passed to the enqueue pipeline.
- `POST /documents/text` and `POST /documents/texts` do not take `tags` directly; tags can be set via Core ingestion or the upload route.

---

## 4) Vector DB: Qdrant filtering

File: `lightrag/kg/qdrant_impl.py`

- `query(..., tag_equals: dict[str,str] | None, tag_in: dict[str, list[str]] | None)` builds `models.Filter(must=[...])` where keys are addressed as `tags.<key>`.
  - For equals: `MatchValue(value=v)`.
  - For in-list: `MatchAny(any=vs)`.
- Client-side `matches_tag_filters` remains active as a safety net for legacy payloads or other backends.

---

## 5) Retrieval paths (operate)

File: `lightrag/operate.py`

- Vector chunk retrieval passes `tag_equals`/`tag_in` to VDB when supported, and then filters results with `matches_tag_filters`.
- Graph-related retrieval pre-filters candidates and always enforces chunk-level tag filters when assembling the final context sent to LLM.

---

## 6) WebUI integration

Types and utilities:
- `lightrag_webui/src/contexts/types.ts`: `TagMap`, `TagEquals`, `TagIn`, `InsertPayload`, `QueryParam`.
- `lightrag_webui/src/lib/utils.ts`: `cleanTagMap`, `cleanTagEquals`, `cleanTagIn`, `buildInsertPayload`, `buildQueryParams`.

API layer:
- `lightrag_webui/src/api/lightrag.ts`: adds `tag_equals`/`tag_in` to query requests; adds optional `tags` to upload form as JSON only when non-empty.

UI components:
- `lightrag_webui/src/components/ui/TagsEditor.tsx`: TagMap editor.
- `lightrag_webui/src/components/ui/TagFilterEditor.tsx`: filter editor for `tag_equals` and `tag_in`.

Integration points:
- Upload dialog (`components/documents/UploadDocumentsDialog.tsx`): integrates `TagsEditor` and sends `tags`.
- Retrieval settings (`components/retrieval/QuerySettings.tsx`): integrates `TagFilterEditor` and contributes to query params.
- Graph settings (`components/graph/Settings.tsx` + `hooks/useLightragGraph.tsx`): reads filters from store and applies during graph queries; properties view displays `tags`/`tags_json`.

I18n:
- `src/locales/*.json` includes `tags.*` keys (en, zh, zh_TW, fr, ar).

---

## 7) Validation and cleaning

Server (upload route):
- Validates JSON object, trims keys/values, drops empties, deduplicates arrays, enforces string or string[] only.

Client (WebUI):
- Utilities perform the same cleaning and only send non-empty `tags`/filters.

---

## 8) Testing

Core/unit:
- `tests/unit/lightrag/lightrag/test_tags_phase1_pipeline.py`: enqueue with tags.
- `tests/unit/lightrag/operate/...`: tag aggregation and filtering tests.

E2E (API):
- See `tests/e2e/lightrag/api/` for end-to-end flows that include tags and filters (naive/modes, graph flows, regressions).

WebUI:
- Bun tests for utilities: `lightrag_webui/src/lib/tags-utils.test.ts` (run in `lightrag_webui/` with `bun test`).

---

## 9) Backward compatibility

- If `tags`, `tag_equals`, `tag_in` are absent or empty, no changes in behavior.
- Items missing required keys are excluded when filters are provided.

---

## 10) Examples

Insert (Core):
```python
await rag.ainsert("Text", file_paths="a.txt", tags={"project":"alpha","owner":["alice","bob"]})
```

Query (REST):
```json
{
  "query": "What is LightRAG?",
  "mode": "naive",
  "tag_equals": {"project": "alpha"},
  "tag_in": {"owner": ["alice", "charlie"], "lang": ["zh", "en"]}
}
```


