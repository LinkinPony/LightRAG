## Tag Plan C 测试补全清单（Backend + WebUI + E2E）

目的：依据 `docs/todo/tag-plan-c.md` 与 `docs/todo/tag-plan-c-webui.md`，补齐单元、集成与端到端测试，确保标签(Tag Plan C)在插入与查询全链路行为符合预期并保持向后兼容。

进度标记约定：
- [ ] 未开始  - [~] 进行中  - [x] 已完成  - [s] 跳过/不适用

关联参考：
- 测试准则：`tests/TESTING.md`
- 已有相关单测：
  - `tests/unit/test_matches_tag_filters.py`
  - `tests/unit/test_tags_phase1_pipeline.py`
  - `tests/unit/test_vector_context_tags.py`
  - `tests/unit/test_queryparam_tags_defaults.py`
  - WebUI：`lightrag_webui/src/lib/tags-utils.test.ts`

环境与隔离策略（适用于 Integration/E2E）：
- 可选加载仓库根部 `.env` 作为默认配置，但在测试会话内务必覆盖下列工作空间相关 env 为唯一随机值（如 `e2e_<uuid8>`）：
  - `WORKSPACE`，以及存储专用：`REDIS_WORKSPACE`、`MILVUS_WORKSPACE`、`QDRANT_WORKSPACE`、`MONGODB_WORKSPACE`、`POSTGRES_WORKSPACE`、`NEO4J_WORKSPACE`
- 为测试运行创建临时 `working_dir`（如 `tmp_path_factory.mktemp("lightrag")`）。
- 不可用的后端通过环境检测自动 `skip`，避免失败污染。
- 参考 Fixture：见 `tests/TESTING.md` 中的 `test_isolated_env` 示例。

测试代码组织形式：
- 顶层按分类划分目录：`tests/unit/`、`tests/integration/`、`tests/e2e/`。
- 在每个分类目录内，测试用例路径结构与源代码目录结构完全一致（mirror）：
  - `lightrag/utils.py` → `tests/unit/lightrag/utils/test_utils.py`
  - `lightrag/operate.py` → `tests/unit/lightrag/operate/test_operate_tags.py`（Tag Plan C 相关）
  - `lightrag/kg/qdrant_impl.py` → `tests/integration/lightrag/kg/test_qdrant_impl_tags.py`
  - `lightrag/api/routers/query_routes.py` → `tests/integration/lightrag/api/routers/test_query_routes_tags.py`
  - 端到端 → `tests/e2e/lightrag/api/test_end_to_end_tags.py`

---

### 后端 — 单元测试（Unit）
- [ ] test_insert_with_tags_persists_to_doc_and_chunks
  - 覆盖 `LightRAG.insert/ainsert(tags=...)` 将 `tags` 写入 `doc_status.metadata.tags`，并在 KV 与向量 payload 中保留。
- [ ] test_vector_context_filters_using_kv_tags_when_payload_missing
  - `_get_vector_context`：当向量 payload 缺少 `tags` 时，回退使用 KV `chunk.tags` 做客户端过滤。
- [ ] test_find_related_text_unit_from_entities_applies_tag_filters
  - `_find_related_text_unit_from_entities`：实体关联的 chunk 列表在返回前应用 `tag_equals`/`tag_in` 过滤。
- [ ] test_get_node_data_passes_tag_filters_to_vdb_query
  - `_get_node_data`：将 `tag_equals`/`tag_in` 透传到实体向量库 `entities_vdb.query(...)`（可用伪 vdb 捕获调用参数）。
- [ ] test_get_edge_data_passes_tag_filters_to_vdb_query
  - `_get_edge_data`：将 `tag_equals`/`tag_in` 透传到关系向量库 `relationships_vdb.query(...)`。
- [ ] test_entity_relation_tag_aggregation_and_storage_to_vdb_and_graph
  - 实体/关系标签聚合（字符串值并集、数组元素并集），写入 `entities_vdb/relationships_vdb` 的 payload `tags` 与图 `tags_json`。
- [ ] test_tag_filter_uses_graph_tags_json_when_vector_tags_absent
  - 当向量结果无 `tags` 时，从图的 `tags_json` 回退并应用过滤（operate 中已有逻辑需覆盖）。
- [ ] test_no_tags_no_filters_unchanged_behavior
  - 未提供标签插入 + 无过滤查询，行为与现状一致。
- [ ] test_untagged_items_excluded_when_filters_present
  - 提供过滤时，未打标签的条目被排除（缺 key 视为不匹配）。
- [ ] test_non_qdrant_vdb_ignores_tag_filters_without_error
  - 非 Qdrant 后端（不支持服务端过滤）不报错，客户端过滤仍生效（TypeError 分支）。

已覆盖（标记进度，回溯验证）：
- [x] tests/unit/test_matches_tag_filters.py — 过滤语义单测
- [x] tests/unit/test_tags_phase1_pipeline.py — Phase 1：插入管道标签传播
- [x] tests/unit/test_vector_context_tags.py — Phase 2：客户端过滤应用
- [x] tests/unit/test_queryparam_tags_defaults.py — `QueryParam` 字段默认值

---

### 后端 — 集成测试（Integration）
- [ ] test_qdrant_chunk_server_side_tag_filters
  - 替换 `tests/integration/test_qdrant_tag_filters.py` 中的占位：插入带标签的 chunks，使用 `tag_equals`/`tag_in` 检索，断言 Qdrant 服务端过滤生效（候选减少）且客户端复核通过。
- [ ] test_qdrant_entity_relation_server_side_tag_filters
  - 针对 `entities_vdb`、`relationships_vdb` 的服务端过滤用例；同 key 同时存在 equals+in 必须同时满足。
- [ ] test_query_route_accepts_and_passes_tag_filters
  - `/query` API 路由接收并透传 `tag_equals`/`tag_in`（使用 TestClient）。
- [ ] test_graph_query_route_accepts_and_passes_tag_filters
  - 图谱查询路由接收并透传 `tag_equals`/`tag_in`；并在节点/边结果中看到 `tags`/`tags_json`（若存在）。

环境与跳过策略：
- Qdrant：通过 `QDRANT_URL` 检测可用性，不可用时 `pytest.skip(...)`（参考占位测试写法）。
- 其余后端（MongoDB/Neo4j）按 `tests/TESTING.md` 中的约定通过环境变量检测并自动跳过。

---

### 查询模式覆盖（Unit/Integration 皆可分层实现）
- [ ] test_modes_apply_tag_filters_strictly_parametrized
  - 对 `mode ∈ {naive, local, global, hybrid, mix}` 参数化：
    - 仅 `tag_equals`
    - 仅 `tag_in`
    - 同 key 同时存在 `equals + in`（需同时满足）
  - 断言：所有返回上下文严格满足过滤；清空过滤后恢复无过滤行为。

---

### WebUI — 单测（Bun）
- [ ] api.lightrag.spec.ts — queryGraphs 仅在非空时拼接 `tag_equals`/`tag_in`（JSON）到 QueryString。
- [ ] api.lightrag.spec.ts — uploadDocument/batchUploadDocuments 仅在非空时向 FormData 附加 `tags`（JSON 字符串）。
- [ ] TagsEditor.spec.tsx — 键/值增删、单值/多值切换、清空后 `onChange` 输出为 `undefined`（不发送字段）。
- [ ] TagFilterEditor.spec.tsx — 等值/包含两区编辑、清空后输出 `undefined`；受控属性变更时同步。
- [ ] QuerySettings.spec.tsx — 与 `useSettingsStore().querySettings` 双向绑定；清空过滤后不发送字段。
- [ ] useLightragGraph.spec.tsx — 从 store 读取 `graphTagEquals/graphTagIn` 并透传给 `queryGraphs`。
- [ ] i18n-tags-keys.spec.ts — `en/zh/zh_TW/fr/ar` 各语言包存在 `tags.*` 键。
- [x] lightrag_webui/src/lib/tags-utils.test.ts — 已覆盖清洗与构造工具

---

### 端到端（E2E）
- [ ] e2e_insert_and_naive_query_with_tag_filters
  - 插入含 `TagMap`，naive 模式设置 `tag_equals/tag_in` 检索；断言仅返回满足过滤的上下文。
- [ ] e2e_modes_with_tag_filters
  - local/global/hybrid/mix 模式在设置过滤下返回上下文均满足过滤；清空过滤恢复无过滤。
- [ ] e2e_graph_filter_and_properties_display
  - 图谱页透传 `tag_equals/tag_in`；节点/边详情展示 `tags` 或 `tags_json`（若存在）；无字段时不展示。
- [ ] e2e_regression_no_tags_no_filters
  - 未提供标签 + 未设置过滤，行为与现状一致。

运行建议（参见 tests/TESTING.md）：
- 仅单元：`pytest -m unit -q`
- 单元 + 可用集成：`pytest -m "unit or integration" -q`
- 端到端（可选）：新增 `@pytest.mark.e2e` 并在 CI 中按需运行

---

### 验收标准（关键）
- 插入：提供 `tags` 时成功持久化到 `doc_status` 与 chunk（KV/向量 payload）；未提供时与现状一致。
- 检索：设置 `tag_equals`/`tag_in` 后，所有返回上下文严格满足过滤；同 key 同时存在两约束需同时满足。
- 过滤执行：优先向量 payload `tags`；缺失时回退到 KV `chunk.tags` 或图 `tags_json`（客户端复核永远保守）。
- Qdrant：服务端过滤生效，候选集减少；客户端安全兜底。
- WebUI：仅在非空时发送新字段；i18n 键完整；组件行为与 API 透传正确。


