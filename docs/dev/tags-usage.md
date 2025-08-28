## Tags Usage Guide (Tag Plan C)

This guide explains how to attach tags when inserting documents and how to use tag filters in queries across Core Python, REST API, and WebUI.

### What are tags?

- Tags are a key-value map: `Record<string, string | string[]>`.
- Values support exact match only (no fuzzy/prefix).
- Typical examples: `{"project":"alpha","owner":["alice","bob"],"lang":"zh"}`.

### Filter semantics

- Two optional filters can be provided in queries:
  - `tag_equals: Record<string, string>`
  - `tag_in: Record<string, string[]>`
- Both groups apply with logical AND across groups and across keys.
- If a key appears in both, the equals value must also be inside the corresponding in-list.

---

## 1) Using LightRAG Core (Python)

### Insert with tags

```python
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.utils import EmbeddingFunc
import asyncio

async def main():
    rag = LightRAG(
        working_dir="./rag_storage",
        llm_model_func=gpt_4o_mini_complete,
        embedding_func=openai_embed,
    )
    await rag.initialize_storages()
    from lightrag.kg.shared_storage import initialize_pipeline_status
    await initialize_pipeline_status()

    tags = {"project": "alpha", "owner": ["alice", "bob"], "lang": "zh"}
    await rag.ainsert(["Text A", "Text B"], file_paths=["a.txt", "b.txt"], tags=tags)

    resp = await rag.aquery(
        "Who owns project alpha?",
        param=QueryParam(
            mode="mix",
            tag_equals={"project": "alpha"},
            tag_in={"owner": ["alice", "charlie"], "lang": ["zh", "en"]},
        ),
    )
    print(resp)

    await rag.finalize_storages()

asyncio.run(main())
```

Notes:
- `LightRAG.ainsert(..., tags=TagMap | None)` propagates tags to document status and all produced chunks.
- `QueryParam` exposes `tag_equals` and `tag_in` for filtering returned contexts.

---

## 2) Using REST API

Base route prefixes (from server):
- Documents: `/documents`
- Query: `/query` and `/query/stream`

### Upload a file with tags

Endpoint: `POST /documents/upload` (multipart/form-data)

- Form fields:
  - `file`: the file
  - `tags` (optional): JSON string of TagMap

```bash
curl -X POST "$HOST/documents/upload" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@/path/to/doc.pdf" \
  -F 'tags={"project":"alpha","owner":["alice","bob"],"lang":"zh"}'
```

Validation rules on server:
- `tags` must be a JSON object.
- Keys are trimmed; empty keys are dropped.
- Values must be string or string[]; elements are trimmed and deduplicated; empty values dropped.

### Insert raw text (no files)

Endpoints:
- `POST /documents/text` body: `{ "text": string, "file_source"?: string }`
- `POST /documents/texts` body: `{ "texts": string[], "file_sources"?: string[] }`

Note: These endpoints do not accept `tags` directly. Use upload route for file-based ingress, or use Core API to pass tags alongside text ingestion.

### Query with tag filters (non-stream)

Endpoint: `POST /query`

Body fields include `query`, `mode`, and optional tag filters:

```bash
curl -X POST "$HOST/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "query": "Summarize project alpha",
    "mode": "mix",
    "tag_equals": {"project": "alpha"},
    "tag_in": {"owner": ["alice","charlie"], "lang": ["zh","en"]}
  }'
```

### Query with tag filters (stream)

Endpoint: `POST /query/stream`

Body is the same shape as non-stream. Response is NDJSON.

---

## 3) Using WebUI

- Insert: In the Upload dialog, toggle “Insert Tags” to open the Tags editor; on submit, tags are sent as `tags` form field (JSON) to `/documents/upload` only when non-empty.
- Retrieval: In Query Settings, configure `Tag Equals` and `Tag In`. Only non-empty filters are sent to `/query`/`/query/stream`.
- Graph: In Graph Settings, optional `tag_equals`/`tag_in` are applied to graph queries in the UI; details panels display `tags` or `tags_json` when present.

---

## 4) Behavior and Compatibility

- If you do not provide tags or filters, behavior remains unchanged.
- Filters exclude items that lack required keys by design.
- With Qdrant backend, server-side filtering is applied where supported; client-side checks remain as a safety net.


