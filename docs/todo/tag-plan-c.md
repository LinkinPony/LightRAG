## Tag Plan C (Key-Value Tags, Exact Match)

Goal: Add tags to inserts and enable tag-based filtering in queries under the storage combo:
- LIGHTRAG_VECTOR_STORAGE=QdrantVectorDBStorage
- LIGHTRAG_GRAPH_STORAGE=Neo4JStorage
- LIGHTRAG_KV_STORAGE=MongoKVStorage
- LIGHTRAG_DOC_STATUS_STORAGE=MongoDocStatusStorage

Constraints and scope:
- Tag values support only exact match on types: string, or list of strings. No fuzzy/prefix.
- Keep design minimal and incremental. Backward compatible for existing data.

### Data model
- Tag map type: `dict[str, str | list[str]]` (denoted as TagMap)
- Store at:
  - Document status (Mongo): `metadata.tags: TagMap`
  - Text chunks (Mongo KV): `tags: TagMap`
  - Text chunks (Qdrant payload): `tags` object. Nested keys addressed as `tags.<key>` in Qdrant filters.
  - Entities/Relations (Phase 4):
    - Vector payload: `tags` (aggregated union from associated chunks)
    - Graph (Neo4j): store `tags_json` (JSON string) to avoid nested map property limitations

Notes:
- If an item lacks a key required by filters, it does not match.
- For legacy rows without `tags`, behavior remains unchanged when no tag filters are provided.

### Query filter semantics (precise)
- Extend QueryParam with two optional fields:
  - `tag_equals: dict[str, str]` (AND across keys; each key must equal the specified value)
  - `tag_in: dict[str, list[str]]` (AND across keys; each key must be any-of listed values)
- Combination rules:
  - Both groups apply with logical AND.
  - If a key appears in both, both constraints must hold (i.e., equals value must also be contained in the in-list).

### API surface changes (user code)
- Insert:
  - `LightRAG.insert(..., tags: dict[str, str | list[str]] | None = None, ...)`
  - `LightRAG.ainsert(..., tags: dict[str, str | list[str]] | None = None, ...)`
  - Behavior: when provided, persist tags at document level (doc_status.metadata.tags) and propagate same tags to all produced chunks (chunk.tags). No partial per-chunk override in Phase 1.
- Query:
  - `QueryParam` gains `tag_equals`, `tag_in` (both optional). Default empty = no tag filtering.

### Storage specifics
- Qdrant (vector):
  - Phase 1: store chunk `tags` in payload by adding `"tags"` to chunks meta_fields.
  - Phase 3: server-side filtering for chunks using `models.Filter`:
    - For each `(k,v)` in `tag_equals` use `FieldCondition(key=f"tags.{k}", match=MatchValue(value=v))`
    - For each `(k, vs)` in `tag_in` use `FieldCondition(key=f"tags.{k}", match=MatchAny(any=vs))`
  - Entities/Relations (Phase 4): also add `"tags"` to their meta_fields and apply same filter logic.
- Mongo (KV + DocStatus):
  - Store TagMap as-is (`str` or `list[str]`). Indexing optional initially.
- Neo4j (graph):
  - Phase 4: write `tags_json` string onto nodes/edges (for inspection/debug). Filtering remains result-side in operate.py, not via Cypher.

### Execution flow (apply filters)
- Naive/mix vector chunk retrieval:
  - Phase 2: client-side filter in operate after retrieval based on `result.payload.tags` (or fallback to KV chunk.tags when payload missing).
  - Phase 3: Qdrant server-side filter first, then client-side as safety net.
- KG (local/global/hybrid/mix):
  - Phase 2: when projecting entities/relations to text chunks, filter chunk list by tag constraints before assembling context for LLM.
  - Phase 4: optionally pre-filter entity/relation candidates by their aggregated `tags` (vector) before chunk projection; still enforce chunk-level filter.

### Phased implementation plan (step-by-step, unambiguous)

Phase 1 — Schema & insert pipeline (chunks only) — DONE
1. Add `tags` parameter to `LightRAG.insert/ainsert` (default None). — DONE
2. In `apipeline_enqueue_documents`, persist `metadata.tags` on doc_status records when `tags` provided. — DONE
3. During chunk creation (in `apipeline_process_enqueue_documents` where `all_chunks_data` is prepared), set `chunk.tags = tags`. — DONE
4. Update `lightrag.py` meta_fields for Qdrant chunks to include "tags":
   - `self.chunks_vdb` meta_fields: {"full_doc_id", "content", "file_path", "tags"} — DONE
5. Acceptance:
   - Insert with tags succeeds; doc_status shows metadata.tags; chunks in KV carry tags; Qdrant payload for chunks includes tags. — DONE

Phase 2 — Query surfaces & client-side filtering (all modes) — DONE
1. Extend `QueryParam` with `tag_equals: dict[str,str] = {}`, `tag_in: dict[str, list[str]] = {}`. — DONE
2. Implement `matches_tag_filters(tags: dict[str, Any], tag_equals, tag_in) -> bool` in a shared utility. — DONE
3. `_get_vector_context` (naive/mix): after retrieval, keep only results where payload.tags (or KV chunk.tags fallback) satisfy filters. — DONE
4. `_find_related_text_unit_from_entities`: when assembling chunks for entities, filter the chunk list by tags before returning. — DONE
5. Acceptance:
  - With filters provided, returned chunks all satisfy constraints across naive/local/global/hybrid/mix. — DONE

Phase 3 — Qdrant server-side filtering for chunks — DONE
1. Extend `QdrantVectorDBStorage.query` to accept optional `tag_equals` and `tag_in`. — DONE
2. Build `models.Filter(must=[...])` using `tags.<key>` path and `MatchValue/MatchAny`. — DONE
3. Keep client-side filter as safety (in case of legacy payloads missing tags). — DONE
   - `_get_vector_context` now passes `tag_equals/tag_in` to vector DB when supported, with fallback for other backends.
4. Acceptance:
   - When filters are provided, Qdrant limits candidates by payload; fewer items scanned; results still pass client check. — DONE

Phase 4 — Entities/Relations tagging & pre-filter — DONE
1. On entity/relation upsert (existing creation/edit paths), compute aggregated TagMap from associated chunk ids (union of string values; for list values use union of elements); store:
   - Vector payload: `tags` — DONE
   - Graph: `tags_json` string — DONE
2. Add "tags" to `entities_vdb` and `relationships_vdb` meta_fields. — DONE
3. In `_get_node_data` / `_get_edge_data`, pass tag filters to vector query when supported (e.g., Qdrant); otherwise filter candidates post-retrieval by their `tags`/`tags_json`. — DONE
4. Acceptance:
   - Entity/Relation vector results respect filters; final chunk context remains strictly filtered. — DONE

Phase 5 — Tests & docs — PARTIAL
1. Unit tests for `matches_tag_filters`. — DONE
2. Unit tests for Phase 1 propagation and client-side vector filtering. — DONE
3. Integration tests with Qdrant verifying server-side filter for chunks/entities/relations. — TODO
4. Mode coverage tests: naive/local/global/hybrid/mix with tag filters. — DONE (client-side)
5. Update README with insert/query examples including tags. — TODO

### Backward compatibility & migration
- No migration required. Rows without tags remain queryable when no filters are provided.
- When filters are provided, items lacking required keys are excluded (by design).

### Optional indices (can defer)
- Mongo: create selective indexes based on actual keys used in filters, e.g. `text_chunks.tags.project`, `doc_status.metadata.tags.project`.

### Risks & mitigations
- Entity/Relation tag “union expansion”: an entity spanning many documents may accumulate many tags. Mitigate by enforcing chunk-level tag filter (always) and using entity/relation tags only as pre-filter.
- Qdrant payload size: keep TagMap small and string-only. Large or deeply nested structures are out of scope.

### Acceptance summary (end-to-end)
- Insert: user supplies TagMap once; tags visible in doc_status and chunk records; Qdrant chunk payload contains tags.
- Query: user supplies `tag_equals/tag_in`; all returned contexts (chunks sent to LLM) satisfy filters; vector search leverages server-side filtering when available.


